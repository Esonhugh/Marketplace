# Gatekeeper, AMFI, MACF & Launch Constraints Reference

## Gatekeeper

Gatekeeper validates downloaded software: developer signature, Apple notarization, quarantine attribute. Enforced by `syspolicyd` (database `/var/db/SystemPolicy`). Only checks files with `com.apple.quarantine` xattr -- no quarantine = no Gatekeeper.

### Verification Flow

1. Download -> browser/mail sets `com.apple.quarantine` xattr
2. User opens -> Gatekeeper checks quarantine flag
3. Signature verified (developer cert + notarization ticket)
4. XProtect scans (`/Library/Apple/System/Library/CoreServices/XProtect.bundle`)
5. Pass -> execute; fail -> block

### Key Commands

```bash
spctl --status                         # Gatekeeper status
spctl --assess -v /Applications/App.app # Assess app
xattr -l /path/to/file | grep com.apple.quarantine  # Check quarantine
# Quarantine format: flags;timestamp;app;UUID  (0x0040 = USER_APPROVED)
xattr -d com.apple.quarantine /path/to/file          # Remove quarantine
find . -print0 | xargs -0 xattr -d com.apple.quarantine  # Bulk remove

sqlite3 /var/db/SystemPolicy \
  "SELECT requirement,allow,disabled,label FROM authority WHERE label != 'GKE' AND disabled=0;"
system_profiler SPInstallHistoryDataType 2>/dev/null | grep -A 4 "XProtectPlistConfigData" | tail -n 5
xattr -p com.apple.provenance /Applications/Some.app | hexdump -C  # Ventura+
```

**Sequoia (15+):** `spctl --master-disable` no longer works. Policy via System Settings or MDM (`com.apple.systempolicy.control`). Ctrl+Open bypass removed.

### Quarantine Internals

- `libquarantine.dylib`: `qtn_file_*` / `qtn_proc_*` -> `mac_syscall("Quarantine", ...)` -> `Quarantine.kext`
- `Quarantine.kext`: MACF hooks on file create/open/rename/hardlink/setxattr
- MIBs: `security.mac.qtn.sandbox_enforce`, `security.mac.qtn.user_approved_exec`
- Event DB: `~/Library/Preferences/com.apple.LaunchServices.QuarantineEventsV2`

### Gatekeeper Bypass CVEs

| CVE | Technique |
|-----|-----------|
| CVE-2021-1810 | Archive Utility paths >886 chars skip quarantine |
| CVE-2021-30990 | Automator stub symlink bypasses quarantine on executable |
| CVE-2022-22616 | ZIP from `app/Contents` -- `.app` itself lacks quarantine |
| CVE-2022-32910 | Apple Archive from `app/Contents` -- same with `.aar` |
| CVE-2022-42821 | ACL `writeextattr deny` via AppleDouble blocks quarantine |
| CVE-2023-27951 | AppleDouble `._` files skip quarantine; DMG symlink trick |
| CVE-2024-44128 | Automator Quick Action workflows bypass assessment path |

**uchg trick:** `uchg` flag on app -> tar.gz -> Gatekeeper skips immutable files.

---

## Code Signing

`LC_CODE_SIGNATURE` points to signature blob. Magic: `0xFADE0CC0` (embedded) / `0xFADE0CC1` (detached).

### SuperBlob & Code Directory

```c
typedef struct __SC_SuperBlob {
    uint32_t magic;       // 0xFADE0CC0
    uint32_t length;
    uint32_t count;       // blob index count
    CS_BlobIndex index[]; // type + offset pairs
} CS_SuperBlob;  // Contains: CodeDirectory, Requirements, Entitlements, CMS. Big Endian.
```

Per-page SHA256 hashes. Special slots: -1 Info.plist, -2 Requirements, -3 Resources, -5 Entitlements, -7 DER Entitlements.

```bash
codesign -d -vvvvvv /bin/ls               # Full signature dump
codesign -d --entitlements :- /path/to/bin # Extract entitlements
codesign -d -r- /path/to/bin              # Show requirements
codesign --verify --verbose /path/to/app   # Verify signature
codesign -s - /path/to/binary              # Ad-hoc sign
csreq -b /tmp/out.csreq -r='identifier "com.apple.ls" and anchor apple'
```

### Key CS Flags (cs_blobs.h)

| Flag | Value | Meaning |
|------|-------|---------|
| `CS_ADHOC` | 0x0002 | Ad-hoc signed (no certificate) |
| `CS_GET_TASK_ALLOW` | 0x0004 | Debuggable |
| `CS_HARD` | 0x0100 | Kill on invalid page load |
| `CS_KILL` | 0x0200 | Kill if signature invalid |
| `CS_RESTRICT` | 0x0800 | Restricted (dyld) |
| `CS_RUNTIME` | 0x10000 | Hardened runtime |
| `CS_PLATFORM_BINARY` | 0x4000000 | Platform binary |

### Weaknesses

**Ad-hoc binaries** (`CS_ADHOC`): no cert chain. On Apple Silicon, minimum signing requirement. Attack: replace in writable location + `codesign -s -` -> inherit TCC grants keyed by path.

```bash
# Find ad-hoc binaries in privileged locations
find /usr/local /opt /Applications -type f -perm +111 -exec sh -c '
  codesign -dvv "{}" 2>&1 | grep -q "Signature=adhoc" && echo "AD-HOC: {}"
' \; 2>/dev/null
```

**Deadly combo** -- `disable-library-validation` + `allow-dyld-environment-variables`:
```bash
DYLD_INSERT_LIBRARIES=/tmp/evil.dylib /path/to/vulnerable-binary
# Constructor runs with target's entitlements + TCC grants
```

---

## MACF - Mandatory Access Control Framework

Intercepts kernel operations, delegates to policy kexts: `AMFI.kext`, `Sandbox.kext`, `Quarantine.kext`, `AppleSystemPolicy.kext`, `ALF.kext`, `CoreTrust.kext`.

### Architecture

```
Syscall/Mach trap -> kernel function -> MACF -> iterate policy modules -> allow/deny
```

- **Static policies**: boot-installed, never removed. **Dynamic**: kext-loaded, unloadable (macOS only)
- Kexts declare `AppleSecurityExtension` in Info.plist, depend on `com.apple.kpi.dsep`
- Init: `mac_policy_init()` -> `mac_policy_initmach()` loads security kexts

### MAC_CHECK Macro (Simplified)

```c
#define MAC_CHECK(check, args...) do {
    error = 0;
    MAC_POLICY_ITERATE({
        if (mpc->mpc_ops->mpo_ ## check != NULL) {
            int __step_err = mpc->mpc_ops->mpo_ ## check (args);
            error = mac_error_select(__step_err, error);  // prefers errors
        }
    });
} while (0)
// Iterates static [0..staticmax], then dynamic [staticmax..maxindex]
// MAC_GRANT: opposite -- any 0 return grants privilege
```

Callout format: `mac_<object>_<opType>_opName` (object: `proc|vnode|file|socket|mount|cred|...`).

```c
int __mac_syscall(const char *_policyname, int _call, void *_arg); // syscall #381
```

```bash
find /System/Library/Extensions -name Info.plist | xargs grep -l AppleSecurityExtension 2>/dev/null
```

---

## AMFI - AppleMobileFileIntegrity

`AMFI.kext` (kernel) + `/usr/libexec/amfid` (userspace). Code signature verification, entitlement enforcement, debug policy. IPC via `HOST_AMFID_PORT` (special port 18, MIG messages). `amfid` uses `libmis.dyld` (`MobileDevice.framework`) -- historically abused in jailbreaks.

### Boot Arguments

| Argument | Effect |
|----------|--------|
| `amfi_get_out_of_my_way=1` | Disables AMFI completely |
| `amfi_allow_any_signature=1` | Accept any code signature |
| `cs_enforcement_disable=1` | System-wide CS enforcement off |
| `amfi_unrestricted_task_for_pid=1` | task_for_pid without entitlements |

### Key MACF Hooks

| Hook | Purpose |
|------|---------|
| `cred_check_label_update_execve` | Label modification permission at exec |
| `vnode_check_exec` | Set `cs_hard|cs_kill` on executable load |
| `vnode_check_signature` | Signature check via trust cache + amfid |
| `proc_check_get_task` | Enforce `get-task-allow` / `task_for_pid-allow` |
| `proc_check_run_cs_invalid` | Intercept `ptrace()` PT_ATTACH/PT_TRACE_ME |
| `proc_check_map_anon` | `dynamic-codesigning` check for MAP_JIT |
| `file_check_mmap` | Library validation on executable mmap |
| `file_check_library_validation` | TeamID / platform binary dylib checks |
| `proc_check_inherit_ipc_ports` | SEND right inheritance across exec |
| `policy_syscall` | DYLD policy (unrestricted segments, env vars) |

**Trust Cache:** Known cdhashes in kext `__TEXT.__const`. Apple Silicon: binaries not in trust cache refused.

```bash
kextstat | grep "com.apple.driver.AppleMobileFileIntegrity"
security cms -D -i /path/to/profile.mobileprovision  # Dump provisioning profile
```

---

## Launch Constraints (Ventura+)

Each system binary gets a constraint category in the trust cache. Checked at `execve()` / `posix_spawn()`.

### 4 Constraint Types

| Type | Validates |
|------|-----------|
| **Self** | Binary itself (volume, launch-type, validation-category) |
| **Parent** | Parent process (e.g., must be `launchd`) |
| **Responsible** | XPC caller process |
| **Library Load** | Allowed dylibs/frameworks |

### Constraint Facts

`is-init-proc`, `is-sip-protected`, `on-authorized-authapfs-volume`, `on-system-volume`, `launch-type`, `validation-category`

Example Category 1: `Self: (on-authorized-authapfs-volume || on-system-volume) && launch-type == 1 && validation-category == 1` / `Parent: is-init-proc`

### Trust Cache Enumeration

```bash
pyimg4 img4 extract -i /tmp/BaseSystemTrustCache.img4 -p /tmp/BaseSystemTrustCache.im4p
pyimg4 im4p extract -i /tmp/BaseSystemTrustCache.im4p -o /tmp/BaseSystemTrustCache.data
pyimg4 im4p extract -i /System/Library/Security/OSLaunchPolicyData -o /tmp/OSLaunchPolicyData.data
trustcache info /tmp/OSLaunchPolicyData.data | head  # constraintCategory 0 = unconstrained
codesign -d -vvvv app.app  # Environment constraints on third-party apps
```

```c
struct trust_cache_entry2 {
    uint8_t cdhash[CS_CDHASH_LEN];
    uint8_t hash_type;
    uint8_t flags;
    uint8_t constraintCategory;  // 0 = unconstrained
    uint8_t reserved0;
} __attribute__((__packed__));
```

**Environment Constraints (Sonoma+):** Third-party devs define in launchd plists or code-signing dicts. Reverse via `kConstraintCategory*` symbols in AMFI kext (DER/ASN.1 encoded).

**LCs do NOT mitigate:** XPC abuse (self-referential responsible constraint), Electron injection (`open` / LaunchServices API), dylib injection without library validation.

---

## Dangerous Entitlements Catalog

| Entitlement | Allows | Exploitation |
|-------------|--------|-------------|
| `com.apple.rootless.install[.heritable]` | Bypass SIP | Write system files |
| `com.apple.system-task-ports` | Task port for any process | Full process control |
| `com.apple.security.get-task-allow` | Debugger attach | `task_for_pid()` -> injection |
| `com.apple.security.cs.debugger` | `task_for_pid()` on GTA targets | Inject dev builds |
| `com.apple.security.cs.disable-library-validation` | Load any dylib | dylib injection |
| `com.apple.security.cs.allow-dyld-environment-variables` | DYLD_INSERT_LIBRARIES | Code injection |
| `com.apple.private.tcc.manager` | TCC database R/W | Silent permission grant |
| `com.apple.rootless.storage.TCC` | Write TCC database | Same |
| `com.apple.private.apfs.revert-to-snapshot` | Revert SSV snapshot | Undo security updates |
| `com.apple.private.apfs.create-sealed-snapshot` | Create sealed snapshot | Persist system mods |
| `kTCCServiceSystemPolicyAllFiles` | Full Disk Access | Read any file |
| `kTCCServiceEndpointSecurityClient` | Write user TCC DB | Grant permissions |
| `com.apple.security.cs.allow-jit` | MAP_JIT W+X memory | JIT / shellcode |
| `com.apple.security.cs.allow-unsigned-executable-memory` | Patch code in memory | Memory corruption |
| `kTCCServiceAppleEvents` | AppleEvents to other apps | Abuse target TCC |
| `kTCCServiceListenEvent` | Intercept all input | Keylogger |
| `temporary-exception.mach-lookup.global-name` | XPC from sandbox | Sandbox escape |

---

## Sealed System Volume (SSV)

Since Big Sur: system volume is APFS snapshot with cryptographic hash tree. Read-only mount. Modification breaks seal verified at boot.

```bash
csrutil authenticated-root status    # SSV status
diskutil apfs listSnapshots disk3s1  # List snapshots
mount | grep " / "                   # Verify read-only
```

### SSV Writer Entitlements

`com.apple.private.apfs.revert-to-snapshot` (revert), `com.apple.private.apfs.create-sealed-snapshot` (create), `com.apple.rootless.install[.heritable]` (write SIP paths)

| CVE | Description |
|-----|-------------|
| CVE-2021-30892 | Shrootless -- SIP bypass via `system_installd` |
| CVE-2022-22583 | SSV bypass through PackageKit snapshot handling |
| CVE-2022-46689 | Race condition writing SIP-protected files |

### DataVault

Root cannot access DataVault files. Protected: TCC DB (`/Library/Application Support/com.apple.TCC/TCC.db`), Keychain. Required entitlements: `com.apple.private.tcc.manager`, `com.apple.private.tcc.allow`, `com.apple.rootless.storage.TCC`.

```bash
ls -le@ "/Library/Application Support/com.apple.TCC/TCC.db"
```

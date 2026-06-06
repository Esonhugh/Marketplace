# macOS Control Bypasser

[![Version](https://img.shields.io/badge/version-2.0.0-blue)](https://github.com/Esonhugh/Marketplace/tree/Skyworship/skills/macos-control-bypasses)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A Claude Code / Ducc skill plugin for macOS offensive security research, covering the full attack surface from system internals and hardware coprocessors to complete penetration testing attack chains.

When your AI coding agent encounters macOS security research tasks — shellcode crafting, dylib injection, sandbox escapes, TCC bypasses, persistence, Gatekeeper bypass, app injection, MDM exploitation, or CVE analysis — this skill automatically activates and provides expert-level guidance with code examples.

## Capabilities

| Topic | Coverage |
|---|---|
| macOS Internals | XNU kernel (Mach/BSD/IOKit), APFS, SIP, AMFI, MACF, Mach-O format, Objective-C runtime |
| Binary Analysis | codesign, objdump, jtool2, Hopper Disassembler, LLDB, DTrace |
| Shellcode | x64/ARM64 shellcode, BSD syscall interface, bind/reverse shells, MAP_JIT loader |
| Dylib Injection | DYLD_INSERT_LIBRARIES, binary restriction analysis, dylib hijacking, dlopen hijacking |
| App-Runtime Injection | Electron fuses, Chromium CDP, Dirty NIB, Java/Python/Perl/Ruby/.NET env var injection |
| Mach IPC | Mach ports, task ports, MIG, remote memory write, thread injection |
| Function Hooking | DYLD_INTERPOSE, Objective-C method swizzling, function interposing |
| XPC Attacks | XPC service vulnerabilities, Mach service abuse, authorization bypass, PID reuse |
| Gatekeeper / XProtect | Quarantine attributes, notarization, XProtect, Gatekeeper bypass CVEs |
| AMFI / MACF | AMFI.kext internals, MACF policy modules, boot-args weakening |
| Launch Constraints | Trust cache, constraint categories, Environment Constraints (Ventura+) |
| Sandbox | Sandbox internals, SBPL profiles, sandbox escape techniques, Office sandbox bypasses |
| TCC Bypass | TCC internals, consent databases, credential/data theft, privacy circumvention |
| Persistence | LaunchAgents/Daemons, Login Items, shell RC files, Folder Actions, cron, BTM bypass |
| Privilege Escalation | Installer abuse, authorization database, symlink/hardlink races, dangerous entitlements |
| Kernel & Hardware | KEXT loading, IOKit/DriverKit, System Extensions, ESF bypass, NVRAM, coprocessors |
| Red Teaming | MDM/DEP exploitation, JAMF attack chains, keychain attacks, AD integration |
| Network Services | VNC, SSH, ARD, Remote Apple Events, firewall bypass |
| Pentesting | Full attack chain: initial access, sandbox escape, persistence, privesc, TCC bypass, kernel exec |

## Installation

### Method 1: Via Marketplace (Recommended)

First, add this repository as a marketplace source:

```bash
/plugin marketplace add Esonhugh/Marketplace
```

Then install the plugin:

```bash
/plugin install macos-control-bypasser
```

Or with the `claude` CLI:

```bash
claude plugin marketplace add Esonhugh/Marketplace
claude plugin install macos-control-bypasser
```

### Method 2: Clone from GitHub

Clone the marketplace repo and install through the marketplace entry. This is a pure skills plugin: the marketplace entry uses `source: "./"` and lists `./skills/macos-control-bypasses` in its `skills` array.

```bash
git clone https://github.com/Esonhugh/Marketplace.git
cd Marketplace
/plugin marketplace add .
/plugin install macos-control-bypasser
```

Once installed, the skill activates automatically when:
- You ask about macOS security research, privilege escalation, or bypass techniques
- You mention SIP, TCC, Sandbox, AMFI, Gatekeeper, MACF, or launch constraints
- You mention DYLD_INSERT_LIBRARIES, Mach ports, Electron injection, or Dirty NIB
- You request CVE analysis related to macOS
- You need help with shellcode (x64 or ARM64), dylib injection, or KEXT exploitation
- You discuss MDM/DEP attacks, keychain exploitation, or macOS red teaming

## Usage

Ask your agent about any macOS offensive security topic:

```
> Explain how DYLD_INSERT_LIBRARIES injection works and why it fails on Safari

> Write ARM64 null-byte-free reverse shell shellcode for Apple Silicon with a MAP_JIT loader

> Analyze CVE-2020-9934 TCC bypass via HOME environment variable relocation

> How can I inject code into an Electron app to abuse its TCC camera permissions?

> What macOS persistence mechanisms bypass BTM detection?

> Explain how MACF dispatches security checks to AMFI, Sandbox, and Quarantine

> How do I exploit a JAMF MDM server for device takeover?

> Show me how to attack IOKit drivers and what DriverKit changed
```

The skill supports both English and Chinese.

## Reference Files

The skill provides 17 balanced reference files covering the full macOS attack surface:

| # | Topic | Key Content |
|---|---|---|
| 01 | macOS Internals | XNU, APFS, SIP, Mach-O, ObjC |
| 02 | Binary Analysis | codesign, Hopper, LLDB, DTrace |
| 03 | Shellcode | x64/ARM64, syscalls, bind/reverse shells, MAP_JIT loader |
| 04 | Dylib Injection | DYLD, restriction analysis, hijacking, dlopen |
| 05 | Mach IPC | Mach ports, task ports, thread injection |
| 06 | Function Hooking | DYLD_INTERPOSE, method swizzling |
| 07 | XPC Attacks | Services, authorization, CVEs |
| 08 | Sandbox | SBPL, internals, escape techniques |
| 09 | TCC Bypass | Internals, consent databases, privacy bypass |
| 10 | Symlink/Hardlink | Filesystem attacks, privilege escalation CVEs |
| 11 | Kernel Execution | KEXT loading, unsigned KEXT exploits |
| 12 | Pentesting | Full attack chain walkthrough |
| 13 | Persistence | LaunchAgents/Daemons, shell RC, Login Items, BTM bypass |
| 14 | Gatekeeper/AMFI/MACF | Quarantine, code signing, MACF, launch constraints, entitlements, SSV |
| 15 | App-Runtime Injection | Electron, Chromium CDP, Dirty NIB, Java/Python/Perl/Ruby/.NET |
| 16 | Red Teaming | MDM/DEP, JAMF, keychain, AD, lateral movement, firewall bypass |
| 17 | IOKit/Kernel/Enumeration | IOKit/DriverKit, ESF, NVRAM, coprocessors, forensics, TCC theft |

## CVE Case Studies

The reference materials include detailed analysis of real-world vulnerabilities:

- **CVE-2020-9934** — TCC bypass via HOME environment variable relocation
- **CVE-2020-9939** — Unsigned KEXT loading via race condition
- **CVE-2021-1779** — KEXT code signing bypass with hardlinks
- **CVE-2020-29621** — Full TCC bypass via coreaudiod audio driver plugin
- **CVE-2024-44243** — SIP bypass through kexts ("Sigma")
- **CVE-2024-23225 / CVE-2024-23296** — In-the-wild kernel 0-days (2024)
- **CVE-2023-41075** — MIG type-confusion kernel vulnerability
- **CVE-2019-8805** — EndpointSecurity client verification bypass
- **CVE-2020-0984** — Microsoft Auto Update hardened runtime bypass
- **CVE-2020-9714** — Adobe Reader PID reuse + TOCTOU
- **CVE-2020-3855** — DiagnosticMessages file overwrite via hardlinks
- **CVE-2020-3762** — Adobe Reader installer privilege escalation
- **CVE-2019-8802** — manpages privilege escalation via symlink
- **CVE-2021-30965** — Endpoint Security Framework bypass
- **CVE-2020-9839 / CVE-2022-22583** — NVRAM-based attacks

## Project Structure

```
skills/macos-control-bypasses/
├── SKILL.md                                  # Skill definition
├── README.md                                 # English overview
├── README-zh.md                              # Chinese overview
├── evals/
│   └── evals.json                            # 7 evaluation test cases
└── references/
    ├── 01-macos-internals.md                 # 17 balanced reference files
    ├── 02-binary-analysis.md                 # covering the full macOS
    ├── 03-shellcode.md                       # attack surface
    ├── 04-dylib-injection.md
    ├── 05-mach-ipc.md
    ├── 06-function-hooking.md
    ├── 07-xpc-attacks.md
    ├── 08-sandbox.md
    ├── 09-tcc-bypass.md
    ├── 10-symlink-hardlink.md
    ├── 11-kernel-execution.md
    ├── 12-pentesting.md
    ├── 13-persistence.md
    ├── 14-gatekeeper-amfi-macf.md
    ├── 15-app-runtime-injection.md
    ├── 16-red-teaming.md
    └── 17-iokit-kernel-enumeration.md
```

## License

MIT

## Author

[Esonhugh](https://github.com/Esonhugh) — [Skill Homepage](https://github.com/Esonhugh/Marketplace/tree/Skyworship/skills/macos-control-bypasses)

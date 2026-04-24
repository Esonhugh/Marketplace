# macOS Control Bypasser

A Claude Code / Ducc skill plugin for macOS offensive security research, covering the full attack surface from system internals to complete penetration testing attack chains.

When your AI coding agent encounters macOS security research tasks — shellcode crafting, dylib injection, sandbox escapes, TCC bypasses, or CVE analysis — this skill automatically activates and provides expert-level guidance with code examples.

## Capabilities

| Topic | Coverage |
|---|---|
| macOS Internals | XNU kernel (Mach/BSD/IOKit), APFS, SIP, AMFI, Mach-O format, Objective-C runtime |
| Binary Analysis | codesign, objdump, jtool2, Hopper Disassembler, LLDB, DTrace |
| Shellcode | x64 ASM/C shellcode, BSD syscall interface, bind shells, NULL byte elimination |
| Dylib Injection | DYLD_INSERT_LIBRARIES, binary restriction analysis, dylib hijacking, dlopen hijacking |
| Mach IPC | Mach ports, task ports, remote memory write, thread injection |
| Function Hooking | DYLD_INTERPOSE, Objective-C method swizzling, function interposing |
| XPC Attacks | XPC service vulnerabilities, authorization bypass, client verification flaws |
| Sandbox | Sandbox internals, SBPL profiles, sandbox escape techniques |
| TCC Bypass | TCC internals, consent databases, privacy protection circumvention |
| Filesystem Attacks | Symlink/hardlink attacks, race conditions, privilege escalation |
| Kernel Execution | KEXT loading, unsigned KEXT exploits, SIP disable techniques |
| Pentesting | Full attack chain: initial access, persistence, privesc, TCC bypass, kernel execution |

## Installation

### Method 1: Via Marketplace (Recommended)

First, add this repository as a marketplace source:

```bash
claude plugin marketplace add Esonhugh/Marketplace
```

Then install the plugin:

```bash
claude plugin install macos-control-bypasser
```

### Method 2: Clone from GitHub

Clone the entire marketplace repo and point Claude Code to the plugin directory:

```bash
git clone https://github.com/Esonhugh/Marketplace.git
claude --plugin-dir ./Marketplace/plugins/macos-control-bypasser
```

Or clone just the plugin into your plugins directory:

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/Esonhugh/Marketplace.git /tmp/marketplace
cd /tmp/marketplace && git sparse-checkout set plugins/macos-control-bypasser
cp -r plugins/macos-control-bypasser ~/.claude/plugins/macos-control-bypasser
```

Once installed, the skill activates automatically when:
- You ask about macOS security research, privilege escalation, or bypass techniques
- You mention SIP, TCC, Sandbox, AMFI, DYLD_INSERT_LIBRARIES, or Mach ports
- You request CVE analysis related to macOS local privilege escalation
- You need help with shellcode, dylib injection, or KEXT exploitation

## Usage

Ask your agent about any macOS offensive security topic:

```
> Explain how DYLD_INSERT_LIBRARIES injection works and why it fails on Safari

> Walk me through writing x64 bind shell shellcode for macOS on port 4444

> Analyze CVE-2020-9934 TCC bypass via HOME environment variable relocation

> How can I escape the macOS sandbox using QuickLook plugins?

> Show me how Objective-C method swizzling can be used for function hooking
```

The skill supports both English and Chinese — respond in whichever language you prefer, and the agent will follow.

## Key Topics

### macOS Security Layers

The skill covers the full macOS security stack, from outermost to innermost:

1. **Gatekeeper** — Controls what apps can be launched
2. **Code Signing / Notarization** — Validates app integrity and origin
3. **SIP (System Integrity Protection)** — Protects system files even from root
4. **Sandbox (App Sandbox)** — Restricts app capabilities via SBPL profiles
5. **TCC (Transparency, Consent, Control)** — Privacy protections for user data
6. **AMFI** — Validates code signing and enforces entitlements
7. **Hardened Runtime** — Prevents code injection and DYLD env variable use

### CVE Case Studies

The reference materials include detailed analysis of real-world vulnerabilities:

- **CVE-2020-9934** — TCC bypass via HOME environment variable relocation
- **CVE-2020-9939** — Unsigned KEXT loading via race condition
- **CVE-2021-1779** — KEXT code signing bypass with hardlinks
- **CVE-2020-29621** — Full TCC bypass via coreaudiod audio driver plugin
- **CVE-2019-8805** — EndpointSecurity client verification bypass
- **CVE-2020-0984** — Microsoft Auto Update hardened runtime bypass
- **CVE-2020-3855** — DiagnosticMessages file overwrite via hardlinks
- **CVE-2020-3762** — Adobe Reader installer privilege escalation
- **CVE-2019-8802** — manpages privilege escalation via symlink

### Full Penetration Testing Workflow

The skill includes a complete macOS attack chain walkthrough:

Initial Access (Word macro) → Sandbox Escape (iTerm2 AutoLaunch) → Persistence (LaunchAgent) → Privilege Escalation (XPC + PAM) → TCC Bypass (HOME relocation) → Kernel Execution (KEXT race)

## Project Structure

```
macos-control-bypasser/
├── .claude-plugin/
│   └── plugin.json                        # Plugin metadata
├── skills/
│   └── macos-control-bypasses/
│       ├── SKILL.md                       # Skill definition (loaded by the agent)
│       ├── evals/
│       │   └── evals.json                 # 3 evaluation test cases
│       └── references/
│           ├── 01-macos-internals.md      # XNU, APFS, SIP, Mach-O, ObjC
│           ├── 02-binary-analysis.md      # codesign, Hopper, LLDB, DTrace
│           ├── 03-shellcode.md            # x64 ASM/C, syscalls, bind shells
│           ├── 04-dylib-injection.md      # DYLD injection, hijacking, dlopen
│           ├── 05-mach-ipc.md             # Mach ports, thread injection
│           ├── 06-function-hooking.md     # Interposing, method swizzling
│           ├── 07-xpc-attacks.md          # XPC vulns, authorization bypass
│           ├── 08-sandbox.md              # SBPL, sandbox escapes
│           ├── 09-tcc-bypass.md           # TCC internals, privacy bypass
│           ├── 10-symlink-hardlink.md     # Filesystem attacks, privesc
│           ├── 11-kernel-execution.md     # KEXT loading, unsigned KEXT
│           └── 12-pentesting.md           # Full attack chain walkthrough
├── README.md
└── README-zh.md
```

## License

MIT

## Author

[Esonhugh](https://github.com/Esonhugh)

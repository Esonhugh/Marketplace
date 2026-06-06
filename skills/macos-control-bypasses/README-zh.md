# macOS Control Bypasser

[![版本](https://img.shields.io/badge/版本-2.0.0-blue)](https://github.com/Esonhugh/Marketplace/tree/Skyworship/skills/macos-control-bypasses)
[![许可证](https://img.shields.io/badge/许可证-MIT-green)](LICENSE)

一个用于 macOS 攻击性安全研究的 Claude Code / Ducc 技能插件，覆盖从系统内部机制、硬件协处理器到完整渗透测试攻击链的全部攻击面。

当你的 AI 编程助手遇到 macOS 安全研究任务 — shellcode 编写、dylib 注入、沙箱逃逸、TCC 绕过、持久化、Gatekeeper 绕过、应用注入、MDM 利用或 CVE 分析 — 本技能会自动激活，提供专家级的指导和代码示例。

## 功能覆盖

| 主题 | 内容 |
|---|---|
| macOS 内部机制 | XNU 内核（Mach/BSD/IOKit）、APFS、SIP、AMFI、MACF、Mach-O 格式、Objective-C 运行时 |
| 二进制分析 | codesign、objdump、jtool2、Hopper Disassembler、LLDB、DTrace |
| Shellcode | x64/ARM64 shellcode、BSD 系统调用接口、bind/reverse shell、MAP_JIT 加载器 |
| Dylib 注入 | DYLD_INSERT_LIBRARIES、二进制限制分析、dylib 劫持、dlopen 劫持 |
| 应用运行时注入 | Electron fuses、Chromium CDP、Dirty NIB、Java/Python/Perl/Ruby/.NET 环境变量注入 |
| Mach IPC | Mach 端口、task 端口、MIG、远程内存写入、线程注入 |
| 函数 Hook | DYLD_INTERPOSE、Objective-C method swizzling、函数拦截 |
| XPC 攻击 | XPC 服务漏洞、Mach 服务滥用、授权绕过、PID 重用 |
| Gatekeeper / XProtect | 隔离属性、公证、XProtect、Gatekeeper 绕过 CVE |
| AMFI / MACF | AMFI.kext 内部机制、MACF 策略模块、boot-args 弱化 |
| 启动约束 | Trust cache、约束类别、Environment Constraints（Ventura+）|
| 沙箱 | 沙箱内部机制、SBPL 配置文件、沙箱逃逸、Office 沙箱绕过 |
| TCC 绕过 | TCC 内部机制、consent 数据库、凭证/数据窃取、隐私绕过 |
| 持久化 | LaunchAgents/Daemons、Login Items、shell RC 文件、Folder Actions、cron、BTM 绕过 |
| 权限提升 | 安装程序滥用、授权数据库、符号链接/硬链接竞争、危险 entitlements |
| 内核与硬件 | KEXT 加载、IOKit/DriverKit、System Extensions、ESF 绕过、NVRAM、协处理器 |
| 红队 | MDM/DEP 利用、JAMF 攻击链、Keychain 攻击、AD 集成 |
| 网络服务 | VNC、SSH、ARD、Remote Apple Events、防火墙绕过 |
| 渗透测试 | 完整攻击链：初始访问、沙箱逃逸、持久化、提权、TCC 绕过、内核执行 |

## 安装

### 方式一：通过 Marketplace 安装（推荐）

首先，将本仓库添加为 marketplace 源：

```bash
/plugin marketplace add Esonhugh/Marketplace
```

然后安装插件：

```bash
/plugin install macos-control-bypasser
```

或使用 `claude` CLI：

```bash
claude plugin marketplace add Esonhugh/Marketplace
claude plugin install macos-control-bypasser
```

### 方式二：从 GitHub 克隆

克隆 marketplace 仓库并通过 marketplace entry 安装。这是纯 skills 插件：marketplace entry 使用 `source: "./"`，并在 `skills` 数组中列出 `./skills/macos-control-bypasses`。

```bash
git clone https://github.com/Esonhugh/Marketplace.git
cd Marketplace
/plugin marketplace add .
/plugin install macos-control-bypasser
```

安装后，本技能会在以下情况自动激活：
- 你询问 macOS 安全研究、权限提升或绕过技术
- 你提到 SIP、TCC、Sandbox、AMFI、Gatekeeper、MACF 或启动约束
- 你提到 DYLD_INSERT_LIBRARIES、Mach 端口、Electron 注入或 Dirty NIB
- 你请求分析与 macOS 相关的 CVE
- 你需要 shellcode（x64 或 ARM64）、dylib 注入或 KEXT 利用的帮助
- 你讨论 MDM/DEP 攻击、Keychain 利用或 macOS 红队

## 使用方式

向你的 agent 询问任何 macOS 攻击性安全主题：

```
> 解释 DYLD_INSERT_LIBRARIES 注入的工作原理，以及为什么对 Safari 无效

> 编写 ARM64 无 NULL 字节的 Apple Silicon reverse shell shellcode，附带 MAP_JIT 加载器

> 分析 CVE-2020-9934 通过 HOME 环境变量重定位的 TCC 绕过

> 如何注入代码到 Electron 应用以滥用其 TCC 摄像头权限？

> macOS 有哪些持久化机制可以绕过 BTM 检测？

> 解释 MACF 如何将安全检查分派给 AMFI、Sandbox 和 Quarantine

> 如何利用 JAMF MDM 服务器进行设备接管？

> 展示如何攻击 IOKit 驱动以及 DriverKit 带来的变化
```

本技能支持中英双语。

## 参考文件

本技能提供 17 个均衡的参考文件，覆盖完整的 macOS 攻击面：

| # | 主题 | 核心内容 |
|---|---|---|
| 01 | macOS 内部机制 | XNU、APFS、SIP、Mach-O、ObjC |
| 02 | 二进制分析 | codesign、Hopper、LLDB、DTrace |
| 03 | Shellcode | x64/ARM64、系统调用、bind/reverse shell、MAP_JIT 加载器 |
| 04 | Dylib 注入 | DYLD、限制分析、劫持、dlopen |
| 05 | Mach IPC | Mach 端口、task 端口、线程注入 |
| 06 | 函数 Hook | DYLD_INTERPOSE、method swizzling |
| 07 | XPC 攻击 | 服务、授权、CVE |
| 08 | 沙箱 | SBPL、内部机制、逃逸技术 |
| 09 | TCC 绕过 | 内部机制、consent 数据库、隐私绕过 |
| 10 | 符号链接/硬链接 | 文件系统攻击、提权 CVE |
| 11 | 内核执行 | KEXT 加载、未签名 KEXT 利用 |
| 12 | 渗透测试 | 完整攻击链演练 |
| 13 | 持久化 | LaunchAgents/Daemons、shell RC、Login Items、BTM 绕过 |
| 14 | Gatekeeper/AMFI/MACF | 隔离属性、代码签名、MACF、启动约束、entitlements、SSV |
| 15 | 应用运行时注入 | Electron、Chromium CDP、Dirty NIB、Java/Python/Perl/Ruby/.NET |
| 16 | 红队 | MDM/DEP、JAMF、Keychain、AD、横向移动、防火墙绕过 |
| 17 | IOKit/内核/枚举 | IOKit/DriverKit、ESF、NVRAM、协处理器、取证、TCC 窃取 |

## CVE 案例分析

参考材料包含真实漏洞的详细分析：

- **CVE-2020-9934** — 通过 HOME 环境变量重定位绕过 TCC
- **CVE-2020-9939** — 利用竞争条件加载未签名 KEXT
- **CVE-2021-1779** — 利用硬链接绕过 KEXT 代码签名
- **CVE-2020-29621** — 通过 coreaudiod 音频驱动插件完全绕过 TCC
- **CVE-2024-44243** — 通过 kext 绕过 SIP（"Sigma"）
- **CVE-2024-23225 / CVE-2024-23296** — 2024 年在野内核 0-day
- **CVE-2023-41075** — MIG 类型混淆内核漏洞
- **CVE-2019-8805** — EndpointSecurity 客户端验证绕过
- **CVE-2020-0984** — Microsoft Auto Update hardened runtime 绕过
- **CVE-2020-9714** — Adobe Reader PID 重用 + TOCTOU
- **CVE-2020-3855** — 通过硬链接覆盖 DiagnosticMessages 文件
- **CVE-2020-3762** — Adobe Reader 安装程序权限提升
- **CVE-2019-8802** — 通过符号链接的 manpages 权限提升
- **CVE-2021-30965** — Endpoint Security Framework 绕过
- **CVE-2020-9839 / CVE-2022-22583** — 基于 NVRAM 的攻击

## 项目结构

```
skills/macos-control-bypasses/
├── SKILL.md                                  # 技能定义
├── README.md                                 # 英文说明
├── README-zh.md                              # 中文说明
├── evals/
│   └── evals.json                            # 7 个评估测试用例
└── references/
    ├── 01-macos-internals.md                 # 17 个均衡的参考文件
    ├── 02-binary-analysis.md                 # 覆盖完整的 macOS
    ├── 03-shellcode.md                       # 攻击面
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

## 许可证

MIT

## 作者

[Esonhugh](https://github.com/Esonhugh) — [Skill 主页](https://github.com/Esonhugh/Marketplace/tree/Skyworship/skills/macos-control-bypasses)

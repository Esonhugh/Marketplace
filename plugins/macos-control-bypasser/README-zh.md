# macOS Control Bypasser

一个用于 macOS 攻击性安全研究的 Claude Code / Ducc 技能插件，覆盖从系统内部机制到完整渗透测试攻击链的全部攻击面。

当你的 AI 编程助手遇到 macOS 安全研究任务 — shellcode 编写、dylib 注入、沙箱逃逸、TCC 绕过或 CVE 分析 — 本技能会自动激活，提供专家级的指导和代码示例。

## 功能覆盖

| 主题 | 内容 |
|---|---|
| macOS 内部机制 | XNU 内核（Mach/BSD/IOKit）、APFS、SIP、AMFI、Mach-O 格式、Objective-C 运行时 |
| 二进制分析 | codesign、objdump、jtool2、Hopper Disassembler、LLDB、DTrace |
| Shellcode | x64 ASM/C shellcode、BSD 系统调用接口、bind shell、NULL 字节消除 |
| Dylib 注入 | DYLD_INSERT_LIBRARIES、二进制限制分析、dylib 劫持、dlopen 劫持 |
| Mach IPC | Mach 端口、task 端口、远程内存写入、线程注入 |
| 函数 Hook | DYLD_INTERPOSE、Objective-C method swizzling、函数拦截 |
| XPC 攻击 | XPC 服务漏洞、授权绕过、客户端验证缺陷 |
| 沙箱 | 沙箱内部机制、SBPL 配置文件、沙箱逃逸技术 |
| TCC 绕过 | TCC 内部机制、consent 数据库、隐私保护绕过 |
| 文件系统攻击 | 符号链接/硬链接攻击、竞争条件、权限提升 |
| 内核执行 | KEXT 加载、未签名 KEXT 利用、SIP 禁用技术 |
| 渗透测试 | 完整攻击链：初始访问、持久化、提权、TCC 绕过、内核执行 |

## 安装

### 方式一：通过 Marketplace 安装（推荐）

首先，将本仓库添加为 marketplace 源：

```bash
claude plugin marketplace add Esonhugh/Marketplace
```

然后安装插件：

```bash
claude plugin install macos-control-bypasser
```

### 方式二：从 GitHub 克隆

克隆整个 marketplace 仓库，并指定插件目录：

```bash
git clone https://github.com/Esonhugh/Marketplace.git
claude --plugin-dir ./Marketplace/plugins/macos-control-bypasser
```

或仅克隆插件到插件目录：

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/Esonhugh/Marketplace.git /tmp/marketplace
cd /tmp/marketplace && git sparse-checkout set plugins/macos-control-bypasser
cp -r plugins/macos-control-bypasser ~/.claude/plugins/macos-control-bypasser
```

安装后，本技能会在以下情况自动激活：
- 你询问 macOS 安全研究、权限提升或绕过技术
- 你提到 SIP、TCC、Sandbox、AMFI、DYLD_INSERT_LIBRARIES 或 Mach 端口
- 你请求分析与 macOS 本地权限提升相关的 CVE
- 你需要 shellcode、dylib 注入或 KEXT 利用的帮助

## 使用方式

向你的 agent 询问任何 macOS 攻击性安全主题：

```
> 解释 DYLD_INSERT_LIBRARIES 注入的工作原理，以及为什么对 Safari 无效

> 带我编写 macOS 上端口 4444 的 x64 bind shell shellcode

> 分析 CVE-2020-9934 通过 HOME 环境变量重定位的 TCC 绕过

> 如何利用 QuickLook 插件逃逸 macOS 沙箱？

> 展示如何使用 Objective-C method swizzling 进行函数 hook
```

本技能支持中英双语 — 使用你偏好的语言提问，agent 会相应回复。

## 核心主题

### macOS 安全层级

本技能覆盖完整的 macOS 安全栈，从最外层到最内层：

1. **Gatekeeper** — 控制哪些应用可以启动
2. **Code Signing / Notarization** — 验证应用完整性和来源
3. **SIP（系统完整性保护）** — 即使 root 也无法修改系统文件
4. **Sandbox（应用沙箱）** — 通过 SBPL 配置文件限制应用能力
5. **TCC（透明度、同意与控制）** — 用户数据的隐私保护
6. **AMFI** — 验证代码签名并执行 entitlements
7. **Hardened Runtime** — 阻止代码注入和 DYLD 环境变量

### CVE 案例分析

参考材料包含真实漏洞的详细分析：

- **CVE-2020-9934** — 通过 HOME 环境变量重定位绕过 TCC
- **CVE-2020-9939** — 利用竞争条件加载未签名 KEXT
- **CVE-2021-1779** — 利用硬链接绕过 KEXT 代码签名
- **CVE-2020-29621** — 通过 coreaudiod 音频驱动插件完全绕过 TCC
- **CVE-2019-8805** — EndpointSecurity 客户端验证绕过
- **CVE-2020-0984** — Microsoft Auto Update hardened runtime 绕过
- **CVE-2020-3855** — 通过硬链接覆盖 DiagnosticMessages 文件
- **CVE-2020-3762** — Adobe Reader 安装程序权限提升
- **CVE-2019-8802** — 通过符号链接的 manpages 权限提升

### 完整渗透测试流程

本技能包含完整的 macOS 攻击链演练：

初始访问（Word 宏）→ 沙箱逃逸（iTerm2 AutoLaunch）→ 持久化（LaunchAgent）→ 权限提升（XPC + PAM）→ TCC 绕过（HOME 重定位）→ 内核执行（KEXT 竞争条件）

## 项目结构

```
macos-control-bypasser/
├── .claude-plugin/
│   └── plugin.json                        # 插件元数据
├── skills/
│   └── macos-control-bypasses/
│       ├── SKILL.md                       # 技能定义（由 agent 加载）
│       ├── evals/
│       │   └── evals.json                 # 3 个评估测试用例
│       └── references/
│           ├── 01-macos-internals.md      # XNU、APFS、SIP、Mach-O、ObjC
│           ├── 02-binary-analysis.md      # codesign、Hopper、LLDB、DTrace
│           ├── 03-shellcode.md            # x64 ASM/C、系统调用、bind shell
│           ├── 04-dylib-injection.md      # DYLD 注入、劫持、dlopen
│           ├── 05-mach-ipc.md             # Mach 端口、线程注入
│           ├── 06-function-hooking.md     # 拦截、method swizzling
│           ├── 07-xpc-attacks.md          # XPC 漏洞、授权绕过
│           ├── 08-sandbox.md              # SBPL、沙箱逃逸
│           ├── 09-tcc-bypass.md           # TCC 内部机制、隐私绕过
│           ├── 10-symlink-hardlink.md     # 文件系统攻击、提权
│           ├── 11-kernel-execution.md     # KEXT 加载、未签名 KEXT
│           └── 12-pentesting.md           # 完整攻击链演练
├── README.md
└── README-zh.md
```

## 许可证

MIT

## 作者

[Esonhugh](https://github.com/Esonhugh)

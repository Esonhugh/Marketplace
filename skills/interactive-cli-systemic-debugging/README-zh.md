# Interactive CLI Systemic Debugging

一个纯 skills Claude Code 插件，用于通过 tmux 系统化调试交互式 CLI、REPL、TUI、shell wizard、watch mode 和长时间运行的终端程序。

该 skill 会指导 Claude 保留真实运行中的终端进程、观察屏幕状态、按步骤发送输入、捕获证据，并且一次只改变一个调试变量。

## 安装

首先添加本仓库作为 marketplace 源：

```bash
/plugin marketplace add Esonhugh/Marketplace
```

然后安装插件：

```bash
/plugin install interactive-cli-systemic-debugging@Esonhugh-Marketplace
```

## 触发场景

当任务涉及以下情况时应触发该 skill：

- 交互式 CLI、REPL、TUI、prompt loop、shell wizard 或 installer
- 命令 hang、freeze、等待输入，或需要多轮输入
- watch mode、dev server、长运行测试 runner 或实时进度工具
- 终端渲染、按键处理、`$TERM`、窗口尺寸、颜色、alternate screen 问题
- 需要 tmux panes、`capture-pane`、`send-keys` 或保留屏幕状态的调试

示例提示：

```text
这个 CLI 打印 Continue? 之后卡住了，先别改代码，帮我调试。
我的 curses TUI 在小终端尺寸下显示异常，复现并诊断它。
watch mode 只有在我回答 prompt 后才失败，帮我保持进程运行并调查。
```

## 包含的 Skill

| Skill | 路径 | 用途 |
|---|---|---|
| `interactive-cli-systemic-debugging` | `skills/interactive-cli-systemic-debugging/SKILL.md` | 基于 tmux 的交互式终端调试观察流程 |

## 仓库布局

```text
skills/interactive-cli-systemic-debugging/
├── SKILL.md      # Skill 定义
├── README.md     # 英文说明
├── README-zh.md  # 中文说明
└── evals.json    # 示例评估 prompts
```

## 说明

- 这是纯 skills 插件：marketplace entry 使用 `source: "./"`，并在 `skills` 数组中列出 `./skills/interactive-cli-systemic-debugging`。
- 不包含 scripts 或 MCP servers。该 workflow 依赖用户环境中的标准 `tmux` 命令。

## 许可证

MIT — 作者：Esonhugh

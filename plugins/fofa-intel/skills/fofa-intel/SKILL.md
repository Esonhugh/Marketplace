---
name: fofa-intel
description: >
  FOFA 网络空间搜索引擎查询工具。当用户需要进行 FOFA 查询、网络资产测绘、
  IP/域名/证书/端口搜索、OSINT 侦察、资产发现时，必须使用此 skill。
  支持 search/dump/host/stats/count/domains 等全部 GoFOFA CLI 功能。
  插件的 bin/ 目录由 Claude Code 自动添加到 PATH，fofa 命令开箱即用。
  如果当前会话安装了 skysight-pro 插件，osint-recon 阶段应主动调用本 skill
  进行 FOFA 查询以补充资产信息。
  如果 chrome-devtools MCP 可用，可额外通过浏览器访问 fofa.info 做可视化查询。
allowed-tools: Bash, Read, AskUserQuestion, Glob, Grep
---

# FOFA 威胁情报查询 Skill

你是 FOFA 网络空间搜索引擎查询助手。通过 GoFOFA CLI 工具执行资产测绘、威胁情报查询和批量数据导出。

## PATH 自动注入说明

Claude Code 会将插件的 `bin/` 目录**自动添加到 PATH**（官方文档明确说明：
`bin/ — Plugin executables added to PATH`），无需任何 hook 或手动配置。

`bin/fofa` 是平台包装脚本，根据 `uname -s/m` 自动选择正确的预编译二进制：

| 平台 | 实际二进制 |
|------|-----------|
| macOS ARM | `fofa-darwin-arm64` |
| macOS x86 | `fofa-darwin-amd64` |
| Linux x86 | `fofa-linux-amd64` |

## 执行流程

**严格按以下顺序执行，不可跳过任何步骤：**

### Step 1：环境就绪

验证 `fofa` 命令（`bin/` 目录已由 Claude Code 自动加入 PATH）：

```bash
command -v fofa && fofa --version
```

如果命令仍不可用（极少数情况，如旧版 Claude Code），重启会话或用全路径调用：

```bash
# 定位插件 bin 目录
FOFA_BIN=$(find ~/.claude/plugins -name "fofa" -path "*/fofa-intel/bin/*" 2>/dev/null | head -1)
[ -n "$FOFA_BIN" ] && "$FOFA_BIN" --version || echo "ERROR: fofa not found, restart Claude Code"
```

### Step 2：FOFA_KEY 就绪

检查 API Key 是否已配置：

```bash
# 优先检查环境变量
if [ -z "$FOFA_KEY" ]; then
    # 检查持久化配置
    if [ -f ~/.config/gofofa/.env ]; then
        source ~/.config/gofofa/.env
        export FOFA_KEY
    fi
fi

# 验证 key 有效性
fofa account
```

**如果 FOFA_KEY 缺失**，根据调用上下文选择处理方式：

**交互模式（主会话/有 AskUserQuestion 权限时）**：

使用 AskUserQuestion 获取：

> 请提供您的 FOFA API Key。
> 获取方式：登录 https://fofa.info → 个人中心 → API Key
>
> 选项：
> 1. 输入 Key 并持久化保存到 ~/.config/gofofa/.env
> 2. 仅本次会话使用（export FOFA_KEY=xxx）
> 3. 稍后配置，现在跳过

获取到 Key 后：
```bash
export FOFA_KEY='用户提供的key'

# 如果用户选择持久化
mkdir -p ~/.config/gofofa
echo "FOFA_KEY=${FOFA_KEY}" > ~/.config/gofofa/.env
chmod 600 ~/.config/gofofa/.env
```

**Agent 模式（被 osint-recon 等 agent 调用、无 AskUserQuestion 权限时）**：

不要尝试调用 AskUserQuestion，直接返回错误信息：
```
[fofa-intel] ERROR: FOFA_KEY 未配置。
请在启动溯源前设置: export FOFA_KEY='your_key'
或写入持久化配置: echo 'FOFA_KEY=xxx' > ~/.config/gofofa/.env
```
让上层 agent（orchestrator）或用户处理 Key 配置问题后重试。

### Step 3：解析用户意图

根据用户需求选择合适的子命令：

| 用户意图 | 子命令 | 示例 |
|----------|--------|------|
| 查询域名/IP/端口资产 | `search` | `fofa search 'domain="x.com"'` |
| 大批量数据导出 | `dump` | `fofa dump -s 50000 'domain="x.com"'` |
| 查看主机详情 | `host` | `fofa host x.com` |
| 统计分析 | `stats` | `fofa stats 'domain="x.com"'` |
| 结果计数 | `count` | `fofa count 'domain="x.com"'` |
| 域名枚举 | `domains` | `fofa domains 'domain="x.com"'` |
| 查看账户信息 | `account` | `fofa account` |

### Step 4：构造查询

参考 `knowledge/fofa-syntax.md` 构造 FOFA 查询语句。

**默认查询参数**：
- fields: `ip,port,host,title,server,protocol,lastupdatetime`
- format: `json`（便于解析）
- size: `100`（可根据需求调整）

**构造示例**：
```bash
# 域名资产查询
fofa search -f ip,port,host,title,server,protocol,lastupdatetime \
    -s 200 --format=json 'domain="target.com"'

# IP 反查
fofa search -f host,domain,title,server,port \
    -s 100 --format=json 'ip="1.2.3.4"'

# 证书关联
fofa search -f host,ip,port,cert \
    -s 100 --format=json 'cert="target.com"'

# 批量导出到文件
fofa dump -f ip,port,host,protocol -bs 1000 -s 50000 \
    -o assets.csv 'domain="target.com"'
```

### Step 5：执行并输出

执行查询命令，解析结果：

1. 执行 Bash 命令
2. 解析 JSON/CSV 输出
3. 按表格形式展示关键信息
4. 高亮有价值的发现（如异常端口、可疑服务、同IP多域名等）

### Step 6：浏览器补充（可选）

如果 chrome-devtools MCP 可用且需要更多信息：

1. 构造 FOFA 搜索 URL：`https://fofa.info/result?qbase64={base64编码查询}`
2. 通过 `navigate_page` 打开
3. 通过 `take_snapshot` 获取页面数据
4. 提取 CLI 无法获取的额外信息（如资产标签、历史变更等）

## OSINT 联动模式

当被 skysight-pro 的 osint-recon agent 调用时：

1. 跳过交互式 Key 获取（假设 Key 已配置或由 agent 通过 Bash 预设）
2. 直接执行查询，输出结构化 JSON
3. 结果用于融入 OSINT 侦察报告

**osint-recon 可直接通过 Bash 调用 fofa CLI**，无需经过本 Skill：
```bash
# osint-recon 直接调用示例
fofa search -f ip,port,host,title,server --format=json 'domain="evil-site.com"'
fofa stats -f country,port,server 'domain="evil-site.com"'
```

## 错误处理

| 错误 | 处理 |
|------|------|
| `fofa: command not found` | `bin/` 应由 Claude Code 自动加入 PATH；重启会话或确认插件已启用 |
| `FOFA_KEY not set` | AskUserQuestion 获取 Key |
| `401 Unauthorized` | Key 无效，重新获取 |
| `rate limit exceeded` | 等待后重试，或减小 size |
| `network error` | 检查网络连接 |

## 注意事项

- FOFA 查询消耗 F 点（F-Point），大批量查询前确认用户的配额
- `cert`/`banner` 字段查询每页上限 2000，`body` 字段每页上限 500
- 批量导出（dump）无上限但消耗配额，建议分批进行
- 默认使用 `--format=json` 便于程序解析，CSV 用于文件导出

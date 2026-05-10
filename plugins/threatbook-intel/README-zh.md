# threatbook-intel

Claude Code 的微步在线（ThreatBook）威胁情报插件。支持 IP、域名、文件哈希威胁情报查询，X 语言资产测绘，以及 pydoll 浏览器自动化（含微信扫码登录）。

## 功能

- **IP 威胁情报** — 信誉评分、标签、关联恶意样本、地理位置
- **域名威胁情报** — WHOIS、DNS 历史、关联 IP、威胁标签
- **文件哈希查询** — 恶意软件分类、沙箱报告
- **漏洞情报** — CVE 详情及受影响资产
- **资产测绘** — X 语言全布尔运算符搜索
- **XGPT 对话** — AI 驱动的威胁分析会话
- **微信登录自动化** — pydoll 全自动扫码登录流程

## 前置条件

- Chrome 浏览器
- [uv](https://github.com/astral-sh/uv) — Python 包管理器（`pip install uv` 或 `brew install uv`）
- 微步在线账号（[x.threatbook.com](https://x.threatbook.com)）
- 微信账号（用于微信扫码登录）
- 推荐配置 `chrome-devtools` MCP 以支持浏览器自动化

## 安装

```bash
/plugin install threatbook-intel@Esonhugh/Marketplace
```

## 使用

用自然语言描述需求即可触发 Skill：

```
查询 IP 8.8.8.8 的威胁情报
在微步查询域名 evil-site.com
用微步搜索资产：ip="1.1.1.1" && port="80"
查询文件哈希 abc123... 的威胁情报
```

## CLI 脚本

`scripts/threatbook_query.py` 通过 pydoll 实现浏览器自动化，用 `uv` 直接运行（依赖自动安装）：

```bash
# IP 威胁情报
uv run scripts/threatbook_query.py -q 8.8.8.8

# 域名查询
uv run scripts/threatbook_query.py -q example.com

# 文件哈希
uv run scripts/threatbook_query.py -q abc123def456...

# X 语言资产测绘
uv run scripts/threatbook_query.py -q 'ip="1.1.1.1" && port="80"'

# 保存结果到 JSON
uv run scripts/threatbook_query.py -q 8.8.8.8 -o result.json
```

## X 语言速查

X 语言是微步在线的资产测绘和内容搜索语法。

### 运算符

| 运算符 | 含义 |
|--------|------|
| `=` | 包含匹配 |
| `==` | 精确匹配 |
| `!=` | 排除 |
| `&&` | 与 |
| `\|\|` | 或 |
| `()` | 分组（最高优先级）|

### 资产测绘示例

```
ip="1.1.1.1"                        # 单个 IP
ip="1.1.1.1/24"                     # C 段
ip="1.1.1.1" && port="80"           # IP + 端口
country="中国" && city="北京"        # 地理位置过滤
asn="15169"                         # 按 ASN
os="windows"                        # 按操作系统
```

### 内容搜索示例

```
intitle=报告 && intext=APT           # 标题 + 正文关键词
blog=溯源 && intext=威胁情报         # 博客搜索
x=溯源                              # 社区内容搜索
```

## 微信登录流程

未登录时，Skill 自动执行完整登录步骤：

1. 导航到登录页面
2. 点击微信登录图标
3. 点击同意隐私协议（必须先点才能显示清晰二维码）
4. 截图二维码并展示给你
5. 持续监测直到登录成功
6. 自动继续原始查询

登录状态保存在 `~/.claude/plugins/data/.chrome-profiles/threatbook`，通常只需登录一次。

## 注意事项

- 脚本使用非无头模式（`headless=False`）运行 Chrome，更好地规避反爬检测
- pydoll 内置 Cloudflare 验证码自动绕过
- 二维码有效期约 5 分钟，过期后重新发起查询获取新码
- 基于 Cookie 的会话跨查询持久保持，仅在 Cookie 失效时需重新登录

## 许可证

MIT — 作者：Esonhugh

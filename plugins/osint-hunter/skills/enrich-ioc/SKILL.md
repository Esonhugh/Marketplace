---
name: enrich-ioc
description: >
  统一 IOC 富化查询。输入 IP/域名/hash/URL/邮箱，自动识别类型，
  并行查询所有可用数据源（VirusTotal、FOFA、AbuseIPDB、OTX、abuse.ch、crt.sh、ThreatBook），
  聚合输出结构化威胁情报报告。支持批量输入（逗号或换行分隔）。
  当用户需要查询威胁情报、分析可疑 IOC、进行资产侦察时使用此 skill。
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

# IOC 富化查询 Skill

你是统一威胁情报查询助手。接收用户提供的 IOC（Indicator of Compromise），自动识别类型，并行查询多个数据源，输出聚合报告。

## 执行流程

**严格按以下顺序执行：**

### Step 1：识别 IOC 类型

参考 `knowledge/ioc-types.md` 中的规则，按优先级匹配用户输入：

- IPv4: `^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$`
- IPv6: 含 `:` 的标准格式
- MD5: `^[a-fA-F0-9]{32}$`
- SHA1: `^[a-fA-F0-9]{40}$`
- SHA256: `^[a-fA-F0-9]{64}$`
- Email: `^[^@\s]+@[^@\s]+\.[^@\s]+$`
- URL: `^https?://`
- Domain: 非 IP、含 `.`、有效 TLD

如果无法识别，使用 AskUserQuestion 请用户明确类型。

支持批量输入：逗号或换行分隔，逐个识别并查询。

### Step 2：检查可用数据源

根据 IOC 类型和已配置的 API Key，确定可查询的数据源：

| IOC 类型 | 数据源 |
|----------|--------|
| IP | FOFA(CLI), VirusTotal(MCP), AbuseIPDB(MCP), OTX(MCP), ThreatBook(Script) |
| Domain | FOFA(CLI), VirusTotal(MCP), OTX(MCP), crt.sh(Script), ThreatBook(Script) |
| Hash | VirusTotal(MCP), OTX(MCP), abuse.ch(Script), ThreatBook(Script) |
| URL | VirusTotal(MCP), OTX(MCP), abuse.ch(Script) |
| Email | OTX(MCP), (Sprint 3: HIBP) |

**可用性检查**：
- VirusTotal MCP: 始终可用（required key）
- FOFA CLI: 检查 `$CLAUDE_PLUGIN_OPTION_FOFA_KEY` 是否存在
- AbuseIPDB MCP: 检查 `$CLAUDE_PLUGIN_OPTION_ABUSEIPDB_KEY` 是否存在
- OTX MCP: 检查 `$CLAUDE_PLUGIN_OPTION_OTX_KEY` 是否存在
- abuse.ch Script: 始终可用（无需 Key）
- crt.sh Script: 始终可用（无需 Key）
- ThreatBook Script: 始终可用（微信登录，需用户交互）

### Step 3：并行查询

**VirusTotal（MCP tool call）**：

根据 IOC 类型调用对应 MCP tool：
- IP → `get_ip_report(ip)`
- Domain → `get_domain_report(domain)`
- Hash → `get_file_report(hash)`
- URL → `get_url_report(url)`

**FOFA（Bash CLI）**：

仅对 IP 和 Domain 类型调用：

```bash
# IP 查询
fofa search -f ip,port,host,title,server,protocol,lastupdatetime \
    -s 100 --format=json 'ip="<IOC_VALUE>"'

# Domain 查询
fofa search -f ip,port,host,title,server,protocol,lastupdatetime \
    -s 100 --format=json 'domain="<IOC_VALUE>"'
```

**AbuseIPDB（MCP tool call）**：

仅对 IP 类型调用：
- IP → `check_ip(ip, max_age_days=90)`

**OTX（MCP tool call）**：

根据 IOC 类型调用：
- IP → `get_indicator(indicator_type="ip", value=<IOC>)`
- Domain → `get_indicator(indicator_type="domain", value=<IOC>)`
- Hash → `get_indicator(indicator_type="hash", value=<IOC>)`
- URL → `get_indicator(indicator_type="url", value=<IOC>)`
- Email → `get_indicator(indicator_type="email", value=<IOC>)`

**abuse.ch（Bash Script）**：

根据 IOC 类型调用：

```bash
# Hash 查询 (MalwareBazaar)
uv run scripts/abusech_query.py --type hash --value "<IOC_VALUE>"

# URL 查询 (URLhaus)
uv run scripts/abusech_query.py --type url --value "<IOC_VALUE>"

# 通用 IOC 查询 (ThreatFox)
uv run scripts/abusech_query.py --type ioc --value "<IOC_VALUE>"
```

**crt.sh（Bash Script）**：

仅对 Domain 类型调用：

```bash
uv run scripts/crtsh_query.py --value "<IOC_VALUE>"
```

**ThreatBook（Bash Script）**：

对 IP、Domain、Hash 类型调用（需用户交互登录，仅在用户明确要求时调用）：

```bash
uv run scripts/threatbook_query.py -q "<IOC_VALUE>"
```

> 注意：ThreatBook 需要微信扫码登录，首次使用会弹出二维码截图。
> 仅在用户明确要求"查询微步"或其他源数据不足时调用。

### Step 4：聚合结果

将所有数据源的返回结果聚合为统一格式：

**Verdict 计算规则**：
- 每个源返回判定：malicious / suspicious / clean / unknown
- VirusTotal: malicious 检出数 / 总引擎数 > 0.1 → malicious，> 0.05 → suspicious
- AbuseIPDB: abuse_score >= 80 → malicious，>= 30 → suspicious
- OTX: pulse_count >= 5 → malicious，>= 1 → suspicious
- abuse.ch: 有匹配记录 → malicious
- confidence = 判定为 malicious 的源数 / 有效返回的源总数
- verdict 阈值：confidence >= 0.6 → malicious，>= 0.3 → suspicious，< 0.3 → clean
- 单源判定 malicious 时 confidence 上限 0.5

### Step 5：输出报告

以 Markdown 表格 + 结构化摘要输出：

```
## IOC 威胁情报报告: <IOC_VALUE>

**类型**: <type>
**综合判定**: <verdict> (置信度: <confidence>)
**查询时间**: <timestamp>

### 数据源结果

| 数据源 | 状态 | 判定 | 关键发现 |
|--------|------|------|----------|
| VirusTotal | ✓ | malicious | 12/90 引擎检出，标签: malware, c2 |
| FOFA | ✓ | - | 开放端口: 22,80,443; 服务: nginx |
| AbuseIPDB | ✓ | malicious | 恶意评分: 95, 举报 234 次, ISP: xxx |
| OTX | ✓ | suspicious | 3 个脉冲匹配, 标签: apt, botnet |
| abuse.ch | ✓ | malicious | ThreatFox: Cobalt Strike C2 |
| crt.sh | ✓ | - | 发现 15 个子域名 |
| ThreatBook | ✗ [未调用] | - | - |

### 详细信息

#### VirusTotal
- 检出率: 12/90
- 恶意标签: malware, c2, trojan
- 关联域名: evil.com, bad.org
- 最近分析: 2026-05-15

#### FOFA 资产信息
- 开放端口: 22, 80, 443, 8080
- 服务: nginx/1.18, OpenSSH 8.2
- 关联域名: evil.com
- 最后更新: 2026-05-10

#### AbuseIPDB
- 恶意评分: 95/100
- 总举报次数: 234
- 最近举报: 2026-05-16
- 主要类别: Port Scan, Web Attack, Brute Force
- ISP: Example Hosting
- 国家: RU

#### OTX
- 脉冲匹配: 3 个
- 标签: apt28, botnet, c2
- 恶意软件家族: Fancy Bear
- 关联 IOC: 5 个 IP, 3 个域名

#### abuse.ch
- ThreatFox: Cobalt Strike C2 beacon
- 置信度: 90%
- 首次发现: 2026-05-01
- 标签: cobalt-strike, c2

#### crt.sh 证书透明度
- 匹配证书: 8 张
- 发现子域名: 15 个
- 关键子域名: admin.evil.com, vpn.evil.com, mail.evil.com

### 关联 IOC
| 类型 | 值 | 关联方式 | 来源 |
|------|-----|----------|------|
| domain | evil.com | resolves_to | VT, FOFA |
| hash | abc123... | communicates_with | VT |
| ip | 2.3.4.5 | same_pulse | OTX |
| domain | admin.evil.com | subdomain | crt.sh |

### 数据完整度
<N>/<total> 源可用
├── ✓ VirusTotal (多引擎检测)
├── ✓ FOFA (资产测绘)
├── ✓ AbuseIPDB (IP 恶意评分)
├── ✓ OTX (威胁脉冲)
├── ✓ abuse.ch (恶意软件/URL)
├── ✓ crt.sh (证书透明度)
└── ○ ThreatBook [按需调用]
```

## 错误处理

| 错误 | 处理 |
|------|------|
| FOFA_KEY 未配置 | 跳过 FOFA 查询，报告标注 [未配置] |
| VT API Key 无效 | 跳过 VT，提示用户检查 Key |
| AbuseIPDB Key 未配置 | 跳过 AbuseIPDB，报告标注 [未配置] |
| OTX Key 未配置 | 跳过 OTX，报告标注 [未配置] |
| FOFA 命令不可用 | 提示重启会话或检查 plugin 安装 |
| Script 执行失败 | 标注 [错误]，继续其他源 |
| 网络超时 | 标注 [超时]，继续其他源 |
| 无法识别 IOC | AskUserQuestion 请用户明确 |

## 注意事项

- FOFA 查询消耗 F 点，大批量前确认配额（`fofa account`）
- VirusTotal 免费 Key 限 4 次/分钟，批量查询时注意间隔
- AbuseIPDB 免费 Key 限 1000 次/天
- OTX 无严格速率限制，但建议间隔 1 秒
- abuse.ch 和 crt.sh 无需 Key，但有速率限制，避免高频请求
- ThreatBook 需微信登录，仅在用户明确要求或其他源不足时调用
- 批量 IOC 查询时，逐个执行避免速率限制

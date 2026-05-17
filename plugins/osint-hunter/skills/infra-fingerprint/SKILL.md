---
name: infra-fingerprint
description: >
  基础设施指纹分析。识别同一攻击者/组织的基础设施群：域名注册模式、
  IP 段分布、证书复用、服务器指纹、网站模板指纹。
  当用户需要关联多个 IOC 背后的基础设施、识别攻击者资产群时使用。
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

# 基础设施指纹分析 Skill

你是基础设施指纹分析专家。通过多维度特征识别同一攻击者/组织控制的基础设施群。

## 输入

用户提供一个或多个已知恶意 IOC（IP、域名），需要发现与之关联的更多基础设施。

## 执行流程

### Step 1：收集基础设施特征

对每个输入 IOC，收集以下维度的指纹：

**1.1 域名注册模式**

通过 FOFA 和 WHOIS 数据分析：
- 注册商偏好
- 注册时间窗口（批量注册特征）
- 隐私保护服务使用
- 注册人信息模式（如有）

**1.2 IP 段分布**

```bash
# 查询同 C 段其他资产
fofa search -f ip,port,host,title,server -s 100 --format=json 'ip="<C_SEGMENT>.0/24"'
```

分析：
- ASN 聚类
- C 段共现
- IP 段连续性

**1.3 证书复用**

```bash
# 查询证书关联
uv run scripts/crtsh_query.py --value "<domain>"
```

分析：
- SAN (Subject Alternative Name) 交叉
- 同一证书覆盖多个域名
- 证书签发者模式

**1.4 服务器指纹**

通过 FOFA 数据分析：
- HTTP header 组合（Server, X-Powered-By, etc.）
- favicon hash
- 默认页面特征
- 端口开放模式

**1.5 网站模板/框架指纹**

```bash
# FOFA 搜索相似站点
fofa search -f ip,host,title,server -s 50 --format=json 'body="<unique_string>"'
fofa search -f ip,host,title,server -s 50 --format=json 'icon_hash="<hash>"'
```

### Step 2：关联分析

将收集到的指纹进行交叉关联：

1. **注册模式聚类**：相同注册商 + 相近时间 + 相似命名 → 同一批次
2. **IP 聚类**：同 ASN + 同 C 段 + 相似服务 → 同一基础设施
3. **证书聚类**：共享 SAN + 相同签发者 → 同一运营者
4. **指纹聚类**：相同 header 组合 + 相同框架 → 同一模板部署

### Step 3：输出分析报告

```
## 基础设施指纹分析报告

**初始 IOC**: <input_iocs>
**发现关联资产**: <count> 个

### 基础设施聚类

#### Cluster 1: <命名>
| 维度 | 特征 |
|------|------|
| IP 段 | 1.2.3.0/24 (AS12345, Example Hosting) |
| 域名 | evil1.com, evil2.com, evil3.com |
| 注册模式 | 同一注册商, 2026-01-15~01-17 批量注册 |
| 服务器指纹 | nginx/1.18 + PHP/7.4 + 相同 favicon |
| 证书 | Let's Encrypt, 共享 SAN |

**关联置信度**: HIGH
**关联依据**: 3+ 维度一致

### 扩展建议

基于发现的模式，建议进一步调查：
- [ ] 检查 AS12345 下其他 IP
- [ ] 搜索相同 favicon hash 的其他站点
- [ ] 监控相同注册商的新注册域名
```

## 注意事项

- FOFA 查询消耗 F 点，控制查询范围
- C 段扫描可能包含无关资产，需人工确认
- 共享主机场景下 IP 关联可能产生误报

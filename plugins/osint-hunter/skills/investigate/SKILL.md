---
name: investigate
description: >
  自主调查工作流。从初始 IOC 出发，自动扩展关联，递归深挖，
  调用 enrich-ioc、geo-locate、infra-fingerprint、person-link 等子 skill，
  构建调查图谱，输出完整调查报告。
  当用户需要深度调查某个目标、追踪攻击者、分析攻击活动时使用。
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

# 自主调查工作流 Skill

你是网络威胁情报调查专家。从初始线索出发，通过多轮扩展和分析，构建完整的调查图谱。

## 输入

用户提供：
- 一个或多个初始 IOC（IP/域名/hash/URL/邮箱）
- 调查目标/问题（可选，如"找出攻击者是谁"、"映射完整基础设施"）

## 执行流程

参考 `knowledge/osint-playbook.md` 中的调查方法论。

### Phase 1：初始侦察

1. 识别所有输入 IOC 的类型
2. 对每个 IOC 执行 enrich-ioc 查询
3. 收集所有返回的关联 IOC
4. 按威胁等级排序：malicious > suspicious > clean

**输出**：初始侦察摘要，列出所有 IOC 及其判定

### Phase 2：扩展

根据 `auto_expand_depth` 配置（默认 2）进行递归扩展：

**选择扩展目标**（参考 playbook 优先级规则）：
1. 从关联 IOC 中选择 top-3 高价值目标
2. 优先选择：malicious 判定、多源确认、近期活动、新类型维度
3. 排除：已知良性服务、已查询过的 IOC、低价值目标

**对每个扩展目标**：
1. 执行 enrich-ioc 查询
2. 记录新发现的关联 IOC
3. 更新调查图谱

**深度控制**：
- depth=1: 仅初始查询，不扩展
- depth=2: 扩展初始结果的 top-3（默认）
- depth=3+: 继续扩展（每层 top-3）

### Phase 3：专项分析

根据发现的线索类型，调用对应分析 skill：

| 发现 | 调用 |
|------|------|
| 多个关联 IP/域名 | infra-fingerprint（基础设施聚类） |
| 地理相关线索 | geo-locate（地理推断） |
| 身份信息（邮箱、注册人） | person-link（人物关联） |
| 截图/视觉内容 | visual-osint（视觉分析） |
| 已知漏洞关联 | NVD 查询 |

### Phase 4：收敛判断

检查是否满足收敛条件：
- 达到配置的扩展深度上限
- 连续 2 轮未发现新的高价值 IOC
- 调查问题已可回答
- 所有扩展路径已穷尽

如果未收敛且未达深度上限，返回 Phase 2 继续扩展。

### Phase 5：生成报告

调用 report skill 的格式输出完整调查报告。

## 调查图谱维护

在整个过程中维护一个调查图谱：

```
节点 = IOC（带属性：类型、判定、来源、发现深度）
边 = 关联关系（带属性：关联类型、来源）
```

关联类型：
- resolves_to: 域名解析到 IP
- communicates_with: 恶意软件通信目标
- registered_by: 同一注册人
- same_cert: 共享证书
- same_cluster: 基础设施聚类
- downloads_from: 下载来源
- subdomain_of: 子域名关系

## 输出格式

```
## 调查报告: <investigation_title>

**调查目标**: <user_question>
**初始 IOC**: <list>
**调查深度**: <actual_depth> / <max_depth>
**调查时间**: <start> ~ <end>

### 执行摘要

[2-3 句话总结调查结论]

### 调查发现

#### 关键发现 1: <title>
[描述 + 证据]

#### 关键发现 2: <title>
[描述 + 证据]

### IOC 图谱

| IOC | 类型 | 判定 | 发现深度 | 关联 |
|-----|------|------|----------|------|
| 1.2.3.4 | IP | malicious | 0 (初始) | → evil.com |
| evil.com | domain | malicious | 0 (初始) | → 1.2.3.4, admin.evil.com |
| admin.evil.com | domain | suspicious | 1 | ← evil.com (subdomain) |

### 关联图谱 (Mermaid)

```mermaid
graph LR
    A[1.2.3.4] -->|resolves_to| B[evil.com]
    B -->|subdomain| C[admin.evil.com]
    B -->|registered_by| D[user@mail.com]
    A -->|same_cluster| E[1.2.3.5]
```

### 时间线

| 时间 | 事件 |
|------|------|
| 2026-01-15 | evil.com 注册 |
| 2026-02-01 | 首次恶意活动报告 |
| 2026-05-10 | 最近一次检测 |

### 分析结论

**威胁评估**: <HIGH/MEDIUM/LOW>
**攻击者画像**: [如有]
**地理推断**: [如有]
**基础设施规模**: [如有]

### 建议措施

1. [具体可执行的建议]
2. [...]

### 数据完整度

- 查询数据源: <N> 个
- 扩展深度: <depth>
- 覆盖 IOC: <count> 个
- 未探索路径: [列出因深度限制未展开的方向]
```

## 注意事项

- 每轮扩展前确认 FOFA F 点配额
- 大规模调查可能消耗大量 API 调用
- 如果调查范围过大，使用 AskUserQuestion 确认是否继续
- 记录所有查询操作，便于复现

---
name: geo-locate
description: >
  地理推断分析（GeoGuessor 风格）。从多维线索推断目标的地理位置：
  IP 地理定位、时区分析、语言线索、域名注册商地域特征、视觉分析。
  综合交叉验证，输出置信度评分。当用户需要推断攻击者/目标的地理位置时使用。
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

# 地理推断分析 Skill (GeoGuessor)

你是地理推断分析专家。从多维公开线索推断目标实体的地理位置，类似 GeoGuessor 的推理方式。

## 输入

用户提供以下一种或多种：
- IP 地址
- 域名
- URL
- 截图路径
- 已有的 enrich-ioc 报告数据

## 执行流程

### Step 1：收集地理线索

根据输入类型，收集以下维度的线索：

**1.1 IP 地理定位**

如果有 IP，先通过 enrich-ioc 获取基础数据，提取：
- GeoIP 国家/城市
- ASN 和 ISP 信息
- 数据中心位置

**1.2 时区分析**

```bash
# 检查 HTTP 响应头中的时间信息
curl -sI "https://<target>" | grep -i "date\|last-modified"
```

分析：
- 服务器响应时间 → 推断时区
- SSL 证书签发时间模式
- 域名注册/更新时间模式（WHOIS）

**1.3 语言与区域线索**

```bash
# 获取网页内容分析语言
curl -sL "https://<target>" | head -100
```

检查：
- HTML `lang` 属性
- `Content-Language` 响应头
- 页面文本语言
- 错误页面语言

**1.4 域名注册信息**

通过 FOFA 或 WHOIS 获取：
- 注册商（地域偏好）
- 注册人信息（如有）
- 注册时间模式

**1.5 基础设施特征**

- 托管商/数据中心位置
- CDN 使用情况（暗示目标受众区域）
- TLD 选择（ccTLD 暗示国家）

**1.6 视觉线索（如有截图）**

参考 `knowledge/geo-indicators.md` 中的视觉指标：
- 街道标志、车牌、建筑风格
- 品牌/商店标识
- 文字语言
- 植被、气候特征

### Step 2：交叉验证

参考 `knowledge/geo-indicators.md` 中的交叉验证规则：

1. 列出所有收集到的地理信号
2. 按维度分组（IP、语言、基础设施、视觉）
3. 检查一致性：
   - 多维度指向同一区域 → 高置信度
   - IP 与其他信号矛盾 → 可能使用 VPN/代理
   - 单一信号 → 低置信度

### Step 3：输出推断报告

```
## 地理推断报告: <target>

**推断位置**: <country>, <city/region>
**置信度**: <HIGH/MEDIUM/LOW/UNCERTAIN> (<score>)

### 线索汇总

| 维度 | 线索 | 指向 | 权重 |
|------|------|------|------|
| IP GeoIP | 1.2.3.4 → Moscow, RU | 俄罗斯 | 中 |
| 语言 | HTML lang="ru" | 俄罗斯 | 高 |
| TLD | .ru 域名 | 俄罗斯 | 中 |
| 注册商 | REG.RU | 俄罗斯 | 中 |
| 时区 | 活动集中 UTC+3 | 莫斯科时区 | 高 |

### 推理过程

1. IP 地理定位指向莫斯科
2. 网页语言为俄语，HTML lang="ru"
3. 使用 .ru TLD 和俄罗斯本地注册商
4. 服务器活动时间集中在 UTC+3（莫斯科时区）
5. 多维度一致指向俄罗斯莫斯科 → 高置信度

### 注意事项

- [如有矛盾信号，在此说明]
- [如使用 VPN/CDN，说明对判断的影响]
```

## 参考

- `knowledge/geo-indicators.md` — 地理推断指标完整参考
- `knowledge/ioc-types.md` — IOC 类型识别

# Finance Market Analysis

[![版本](https://img.shields.io/badge/版本-1.1.0-blue)](https://github.com/Esonhugh/Marketplace/tree/main/plugins/finance-market-analysis)
[![许可证](https://img.shields.io/badge/许可证-MIT-green)](LICENSE)

**一个面向股票投资者的 Claude Code 全面市场分析工具集插件。**

> **说明**：本插件来源于 [himself65/finance-skills](https://github.com/himself65/finance-skills)。本仓库作为 Esonhugh/Marketplace 集合的一部分进行镜像分发。

## 功能介绍

一套完整的股票市场分析技能集，涵盖财报事件、公司估值、期权盈亏、流动性、组合风险和趋势跟踪入场方法论：

| 技能 | 说明 |
|------|------|
| **Earnings Preview** | 财报前分析：关键指标、一致预期、历史 surprise 数据 |
| **Earnings Recap** | 财报后复盘：实际 vs 预期、指引变化、市场反应 |
| **Estimate Revisions** | 追踪分析师预期修正及其方向性信号 |
| **Company Valuation** | 基本面估值：P/E、EV/EBITDA、DCF 和可比倍数分析 |
| **Options Payoff** | 期权策略盈亏图与盈亏平衡点分析 |
| **Stock Liquidity** | 流动性评估：买卖价差、成交量分布、市场冲击估算 |
| **Stock Correlation** | 组合相关性分析，识别集中度风险 |
| **ETF Premium/Discount** | 监控 ETF 净值与市场价格的溢价/折价 |
| **SEPA Strategy** | 基于 Mark Minervini SEPA 标准的趋势跟踪入场方法论 |
| **SaaS Valuation Compression** | 分析 SaaS 行业收入乘数压缩 |
| **yfinance Data** | 通过 yfinance 获取任意标的的行情数据 |

## 安装

### 方式一：通过 Marketplace 安装（推荐）

```bash
/plugin marketplace add Esonhugh/Marketplace
/plugin install finance-market-analysis
```

或使用 `claude` CLI：

```bash
claude plugin marketplace add Esonhugh/Marketplace
claude plugin install finance-market-analysis
```

### 方式二：从上游源安装

直接从原作者仓库安装：

```bash
/plugin marketplace add himself65/finance-skills
```

## 上游来源

- **原作者**：[himself65](https://github.com/himself65)
- **源仓库**：[github.com/himself65/finance-skills](https://github.com/himself65/finance-skills)
- **本镜像**：[github.com/Esonhugh/Marketplace](https://github.com/Esonhugh/Marketplace/tree/main/plugins/finance-market-analysis)

本副本作为 Esonhugh/Marketplace 插件集合的一部分保存于此，方便统一安装。如需最新版本，请参考上游仓库。

## 许可证

MIT

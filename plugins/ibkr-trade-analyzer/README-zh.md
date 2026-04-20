# IBKR Trade Analyzer

**一个用于分析 Interactive Brokers 交易历史的 Claude Code 插件 — 只读分析，零风险。**

## 功能介绍

本插件通过 IBKR 的只读 Flex Web Service API 连接你的账户，或读取本地导出的 CSV/XML 文件，生成全面的交易分析报告：

| 维度 | 详细内容 |
|------|---------|
| **交易行为模式** | 交易频率、持仓周期、时段分布、胜率、盈亏比 |
| **盈亏表现** | 已实现盈亏、权益曲线、夏普比率、最大回撤、月度收益 |
| **组合结构** | 资产配置、行业集中度、多空比例、仓位大小 |
| **费用与现金流** | 佣金、利息、股息、融资成本、费用/盈亏比 |
| **现金与外汇** | 多币种余额、外汇兑换历史、流动性比率 |
| **交易风格画像** | 自动生成的定性总结（日内/波段/趋势、方向偏好、风险偏好）|
| **风险评估** | 6 个维度的 0-100 评分，附具体风险预警 |
| **价格图表** | 叠加买卖标记的历史价格走势图 |

## 安装

### 方式一：通过 Marketplace 安装（推荐）

首先，将本仓库添加为 marketplace 源：

```bash
claude plugin marketplace add Esonhugh/Marketplace
```

然后安装插件：

```bash
claude plugin install ibkr-trade-analyzer
```

### 方式二：从 GitHub 克隆

克隆整个 marketplace 仓库，并指定插件目录：

```bash
git clone https://github.com/Esonhugh/Marketplace.git
claude --plugin-dir ./Marketplace/plugins/ibkr-trade-analyzer
```

或仅克隆插件到插件目录：

```bash
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/Esonhugh/Marketplace.git /tmp/marketplace
cd /tmp/marketplace && git sparse-checkout set plugins/ibkr-trade-analyzer
cp -r plugins/ibkr-trade-analyzer ~/.claude/plugins/ibkr-trade-analyzer
```

## 使用方法

安装后，直接对 Claude 说：

```
分析我的 IBKR 交易历史
```

Claude 会引导你完成：

1. **选择数据来源** — Flex Web Service（在线）或本地文件（离线）
2. **提供凭证** — Flex Token + Query ID，或文件路径
3. **运行分析** — 自动执行，生成 Markdown + 交互式 HTML 报告
4. **查看结果** — 与 Claude 交互讨论分析发现

## 数据来源

### 方式 A：Flex Web Service（推荐）

从 IBKR 的只读报告 API 直接拉取数据。

**设置步骤：**
1. 登录 [IBKR 账户管理](https://www.interactivebrokers.com/sso/Login)
2. 进入 **Performance & Reports > Flex Queries**
3. 创建新的 Activity Flex Query，勾选：**Trades、Cash Transactions、Open Positions、Account Information**
4. 输出格式设为 **XML**，保存后记录 **Query ID**
5. 在 **Manage Flex Web Service** 中获取 **Flex Token**

可设置环境变量跳过交互提示：
```bash
export IBKR_FLEX_TOKEN="your-token-here"
export IBKR_QUERY_ID="123456"
```

### 方式 B：本地文件

从 IBKR Client Portal 或 TWS 导出文件，提供文件路径即可。支持 CSV 和 XML 格式。

## 输出

报告保存在 `reports/` 目录下：
- `ibkr-analysis-YYYY-MM-DD.md` — 完整 Markdown 报告（含表格）
- `ibkr-analysis-YYYY-MM-DD.html` — 交互式 HTML 报告（含 Plotly 图表）

## 安全保证

本插件以**只读安全**为核心设计原则：

1. **API 层面** — Flex Web Service 不存在任何写入/下单接口
2. **代码层面** — 未导入任何交易执行库（无 `ibapi`、无 `ib_insync`）
3. **网络层面** — 仅向 IBKR Flex 报告端点发起出站 HTTPS 请求
4. **文件层面** — 仅写入 `reports/` 输出目录

## 环境要求

- Python >= 3.10
- 依赖通过 [PEP 723](https://peps.python.org/pep-0723/) 内联元数据由 `uv run` 自动安装

## 许可证

MIT

## 作者

[Esonhugh](https://github.com/Esonhugh)

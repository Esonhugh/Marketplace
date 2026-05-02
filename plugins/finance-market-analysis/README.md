# Finance Market Analysis

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/Esonhugh/Marketplace/tree/main/plugins/finance-market-analysis)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**A Claude Code plugin providing a comprehensive market analysis toolkit for stock investors.**

> **Note**: This plugin originates from [himself65/finance-skills](https://github.com/himself65/finance-skills). This repository mirrors and distributes it as part of the Esonhugh/Marketplace collection.

## What It Does

A complete set of skills for stock market analysis, covering earnings events, company valuation, options payoff, liquidity, portfolio risk, and trend-following entry methodology:

| Skill | Description |
|-------|-------------|
| **Earnings Preview** | Pre-earnings analysis with key metrics, consensus estimates, and historical surprise data |
| **Earnings Recap** | Post-earnings breakdown of results vs expectations, guidance changes, and market reaction |
| **Estimate Revisions** | Track analyst estimate revisions and their directional signals |
| **Company Valuation** | Fundamental valuation analysis: P/E, EV/EBITDA, DCF, and comparable multiples |
| **Options Payoff** | Options strategy payoff diagrams and break-even analysis |
| **Stock Liquidity** | Liquidity assessment: bid-ask spread, volume profile, market impact estimation |
| **Stock Correlation** | Portfolio correlation analysis to identify concentration risk |
| **ETF Premium/Discount** | Monitor ETF NAV vs market price for arbitrage and sentiment signals |
| **SEPA Strategy** | Trend-following entry methodology based on Mark Minervini's SEPA criteria |
| **SaaS Valuation Compression** | Analyze revenue multiple compression in SaaS sector |
| **yfinance Data** | Fetch and explore market data via yfinance for any ticker |

## Installation

### Method 1: Via Marketplace (Recommended)

```bash
/plugin marketplace add Esonhugh/Marketplace
/plugin install finance-market-analysis
```

Or with the `claude` CLI:

```bash
claude plugin marketplace add Esonhugh/Marketplace
claude plugin install finance-market-analysis
```

### Method 2: From Upstream Source

Install directly from the original author's repository:

```bash
/plugin marketplace add himself65/finance-skills
```

## Upstream

- **Original Author**: [himself65](https://github.com/himself65)
- **Source Repository**: [github.com/himself65/finance-skills](https://github.com/himself65/finance-skills)
- **This Mirror**: [github.com/Esonhugh/Marketplace](https://github.com/Esonhugh/Marketplace/tree/main/plugins/finance-market-analysis)

This copy is maintained here for convenience as part of the Esonhugh/Marketplace plugin collection. For the latest upstream version, refer to the source repository.

## License

MIT

# threatbook-intel

ThreatBook (微步在线) threat intelligence plugin for Claude Code. Query IP, domain, and file hash threat intelligence, perform asset mapping with X language, and automate the browser via pydoll — including WeChat QR login.

## Features

- **IP threat intelligence** — reputation, tags, associated malware, geolocation
- **Domain threat intelligence** — WHOIS, DNS history, associated IPs, threat tags
- **File hash lookup** — malware classification, sandbox reports
- **Vulnerability intelligence** — CVE details and affected assets
- **Asset mapping** — X language search with full boolean operators
- **XGPT conversation** — AI-powered threat analysis chat
- **WeChat login automation** — fully automated QR code login flow via pydoll

## Prerequisites

- Chrome browser installed
- [uv](https://github.com/astral-sh/uv) — Python package manager (`pip install uv` or `brew install uv`)
- ThreatBook account at [x.threatbook.com](https://x.threatbook.com)
- WeChat account (for WeChat login)
- `chrome-devtools` MCP configured (recommended for browser automation)

## Installation

```bash
/plugin install threatbook-intel@Esonhugh/Marketplace
```

## Usage

Trigger the skill with natural language:

```
Query threat intelligence for IP 8.8.8.8
Look up domain evil-site.com on ThreatBook
Search ThreatBook for assets: ip="1.1.1.1" && port="80"
Check file hash abc123... on ThreatBook
```

## CLI Script

`scripts/threatbook_query.py` provides headless automation via pydoll. Run it directly with `uv` (dependencies install automatically):

```bash
# IP threat intel
uv run scripts/threatbook_query.py -q 8.8.8.8

# Domain lookup
uv run scripts/threatbook_query.py -q example.com

# File hash
uv run scripts/threatbook_query.py -q abc123def456...

# X language asset mapping
uv run scripts/threatbook_query.py -q 'ip="1.1.1.1" && port="80"'

# Save result to JSON
uv run scripts/threatbook_query.py -q 8.8.8.8 -o result.json
```

## X Language Quick Reference

X language is ThreatBook's query syntax for asset mapping and content search.

### Operators

| Operator | Meaning |
|----------|---------|
| `=` | Contains match |
| `==` | Exact match |
| `!=` | Exclude |
| `&&` | AND |
| `\|\|` | OR |
| `()` | Grouping (highest precedence) |

### Asset Mapping Examples

```
ip="1.1.1.1"                        # Single IP
ip="1.1.1.1/24"                     # C-class subnet
ip="1.1.1.1" && port="80"           # IP + port
country="中国" && city="北京"        # Geo filter
asn="15169"                         # By ASN
os="windows"                        # By OS
```

### Content Search Examples

```
intitle=报告 && intext=APT           # Title + body keywords
blog=溯源 && intext=威胁情报         # Blog search
x=溯源                              # Community content
```

## WeChat Login Flow

When not logged in, the skill automates the full login sequence:

1. Navigate to the login page
2. Click the WeChat login icon
3. Accept the privacy agreement (required to reveal QR code)
4. Screenshot the QR code and present it to you
5. Poll until login is confirmed
6. Proceed with the original query

Login state is persisted in `~/.threatbook-chrome-profile` — you typically only need to log in once.

## Notes

- The script runs Chrome in non-headless mode (`headless=False`) to bypass anti-bot detection
- Cloudflare challenge bypass is handled automatically by pydoll
- If the QR code expires, re-run the query to get a fresh one
- Cookie-based session is maintained across queries; re-login only needed when session expires

## License

MIT — Author: Esonhugh

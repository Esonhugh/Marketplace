# fofa-intel

FOFA cyberspace search engine plugin for Claude Code. Provides asset discovery, threat intelligence queries, and bulk data export via the GoFOFA CLI — with pre-compiled multi-platform binaries bundled.

## Features

- **Asset mapping** — search by domain, IP, port, certificate, banner, protocol
- **Bulk export** — dump up to millions of records with `dump`
- **Host profiling** — full asset detail with `host`
- **Statistical analysis** — distribution breakdown with `stats`
- **Domain enumeration** — find subdomains with `domains`
- **Cross-platform** — pre-compiled binaries for macOS (ARM/x86), Linux, Windows; auto-selected at runtime

## Prerequisites

- FOFA account with API Key — get one at [fofa.info](https://fofa.info) → Profile → API Key
- Claude Code with this plugin installed

The `bin/` directory is automatically added to `PATH` by Claude Code — no manual setup required.

## Installation

```bash
/plugin install fofa-intel@Esonhugh/Marketplace
```

## Configuration

Set your FOFA API Key (persists across sessions):

```bash
mkdir -p ~/.config/gofofa
echo "FOFA_KEY=your_key_here" > ~/.config/gofofa/.env
chmod 600 ~/.config/gofofa/.env
```

Or set it temporarily for the current session:

```bash
export FOFA_KEY=your_key_here
```

## Usage

Trigger the skill by describing your intent naturally:

```
Search FOFA for assets on domain example.com
Find all open ports on IP 1.2.3.4 using FOFA
Export FOFA data for certificate cert.example.com
Run FOFA stats on country=CN and port=443
```

## CLI Quick Reference

The `fofa` command is available in all Bash tool calls once the plugin is installed:

```bash
# Domain asset search
fofa search -f ip,port,host,title,server -s 200 --format=json 'domain="target.com"'

# IP reverse lookup
fofa search -f host,domain,title,server,port -s 100 --format=json 'ip="1.2.3.4"'

# Certificate pivot
fofa search -f host,ip,port,cert -s 100 --format=json 'cert="target.com"'

# Bulk export to CSV
fofa dump -f ip,port,host,protocol -bs 1000 -s 50000 -o assets.csv 'domain="target.com"'

# Host detail
fofa host target.com

# Result count
fofa count 'domain="target.com"'

# Account info
fofa account
```

## Bundled Binaries

| Platform | Binary |
|----------|--------|
| macOS ARM64 | `bin/fofa-darwin-arm64` |
| macOS x86_64 | `bin/fofa-darwin-amd64` |
| Linux x86_64 | `bin/fofa-linux-amd64` |
| Windows x86_64 | `bin/fofa-windows-amd64.exe` |

`bin/fofa` is a shell wrapper that auto-selects the correct binary via `uname`.

## Notes

- Queries consume F-Points; confirm your quota before bulk exports
- `cert` / `banner` fields: max 2,000 results per page
- `body` field: max 500 results per page
- Use `--format=json` for programmatic parsing, CSV for file exports

## License

MIT — Author: Esonhugh

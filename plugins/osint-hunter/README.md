# OSINT Hunter

A unified network threat intelligence analysis plugin for Claude Code. Aggregates multiple intelligence sources (FOFA, VirusTotal, AbuseIPDB, OTX, and more) into a single investigation workflow.

## Features

- **IOC Enrichment**: Input any IOC (IP, domain, hash, URL, email) and get aggregated intelligence from all configured sources
- **Asset Mapping**: FOFA-powered internet asset discovery and reconnaissance
- **Multi-Engine Detection**: VirusTotal integration for file/URL/IP/domain analysis
- **Graceful Degradation**: Works with whatever API keys you have configured; skips unavailable sources

## Installation

```bash
claude plugin install osint-hunter
```

On first enable, you'll be prompted to configure API keys.

## Required API Keys

| Service | Required | Get it at |
|---------|----------|-----------|
| FOFA | Yes | https://fofa.info |
| VirusTotal | Yes | https://www.virustotal.com/gui/my-apikey |
| AbuseIPDB | No | https://www.abuseipdb.com/account/api |
| OTX | No | https://otx.alienvault.com/api |

## Usage

```
/osint-hunter:enrich-ioc 8.8.8.8
/osint-hunter:enrich-ioc evil-domain.com
/osint-hunter:enrich-ioc d41d8cd98f00b204e9800998ecf8427e
```

## Roadmap

- [x] AbuseIPDB MCP server
- [x] OTX MCP server
- [x] abuse.ch integration (ThreatFox, URLhaus, MalwareBazaar)
- [x] Certificate transparency (crt.sh)
- [x] Investigation workflow with auto-expansion
- [x] Geo-location inference (GeoGuessor)
- [x] Infrastructure fingerprinting
- [x] Person-link analysis
- [x] Visual OSINT
- [x] Autonomous investigation agent

## License

MIT

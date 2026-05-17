# IOC Type Identification Rules

## Auto-Detection Priority

When a user provides an IOC value, match against these patterns in order.
First match wins.

| Priority | Type | Pattern | Examples |
|----------|------|---------|----------|
| 1 | IPv4 | `^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$` | `8.8.8.8`, `192.168.1.0/24` |
| 2 | IPv6 | Standard IPv6 with `:` separators | `2001:db8::1` |
| 3 | MD5 | `^[a-fA-F0-9]{32}$` | `d41d8cd98f00b204e9800998ecf8427e` |
| 4 | SHA1 | `^[a-fA-F0-9]{40}$` | `da39a3ee5e6b4b0d3255bfef95601890afd80709` |
| 5 | SHA256 | `^[a-fA-F0-9]{64}$` | `e3b0c44298fc1c149afbf4c8996fb924...` |
| 6 | Email | `^[^@\s]+@[^@\s]+\.[^@\s]+$` | `admin@evil.com` |
| 7 | URL | `^https?://` | `https://evil.com/malware.exe` |
| 8 | Domain | Not IP, contains `.`, valid TLD | `evil.com`, `sub.evil.co.uk` |

## Data Source Routing

| IOC Type | Data Sources |
|----------|-------------|
| IPv4/IPv6 | FOFA, VirusTotal, AbuseIPDB, OTX, ThreatBook |
| Domain | FOFA, VirusTotal, OTX, crt.sh, ThreatBook |
| MD5/SHA1/SHA256 | VirusTotal, OTX, abuse.ch (MalwareBazaar) |
| URL | VirusTotal, OTX, abuse.ch (URLhaus) |
| Email | HIBP, OTX |

## Batch Input

Support comma-separated or newline-separated IOCs.
Split, trim whitespace, identify each independently.

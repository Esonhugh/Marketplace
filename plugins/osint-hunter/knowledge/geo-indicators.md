# Geographic Inference Indicators

## IP Geolocation

Primary source: GeoIP databases (MaxMind, IP2Location)
- Country, city, ASN, ISP
- Accuracy varies: country ~99%, city ~50-80%
- VPN/proxy/Tor exit nodes reduce reliability

## Time Zone Analysis

| Signal | Source | Reliability |
|--------|--------|-------------|
| Server response headers (Date) | HTTP headers | Medium |
| SSL certificate timestamps | crt.sh | Low |
| Domain registration time patterns | WHOIS | Medium |
| Activity time patterns | Log analysis | High |
| Cron job execution times | Server behavior | High |

## Language & Locale Signals

| Signal | Source | Inference |
|--------|--------|-----------|
| HTTP Accept-Language | Server config | Operator language |
| HTML lang attribute | Web content | Target audience |
| Content language | Page text | Operator/audience |
| Error messages language | Server errors | Developer locale |
| WHOIS registrant info | Domain records | Registrant location |
| Code comments language | Source code | Developer origin |

## Infrastructure Patterns

| Pattern | Geographic Signal |
|---------|-------------------|
| Domain registrar | Regional preference (e.g., Namecheap=US, GoDaddy=US, Alibaba Cloud=CN) |
| Hosting provider | Data center location |
| CDN usage | Target audience region |
| Payment processor | Operating jurisdiction |
| TLD choice | .cn=China, .ru=Russia, .de=Germany, etc. |

## Visual OSINT Indicators

| Indicator | What it reveals |
|-----------|----------------|
| Street signs | Country, city, language |
| License plates | Country, region |
| Architecture style | Region, era |
| Vegetation | Climate zone |
| Power line style | Country |
| Road markings | Country |
| Sun position/shadows | Hemisphere, latitude |
| Brand logos/stores | Country, city |
| Currency symbols | Country |
| Phone number format | Country |

## Cross-Validation Rules

1. Multiple independent signals pointing to same region → HIGH confidence
2. IP geo + language + TLD agree → HIGH confidence
3. IP geo contradicts other signals → likely VPN/proxy, use other signals
4. Single signal only → LOW confidence, note as "possible"
5. Conflicting signals → report all, note contradiction

## Confidence Scoring

| Level | Criteria |
|-------|----------|
| HIGH (0.8-1.0) | 3+ independent signals agree |
| MEDIUM (0.5-0.8) | 2 signals agree, no contradictions |
| LOW (0.2-0.5) | 1 signal only, or minor contradictions |
| UNCERTAIN (<0.2) | Conflicting signals, insufficient data |

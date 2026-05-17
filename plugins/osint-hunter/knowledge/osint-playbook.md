# OSINT Investigation Playbook

## Investigation Methodology

### Phase 1: Initial Reconnaissance

1. **IOC Identification**: Classify input indicators (IP, domain, hash, URL, email)
2. **Baseline Enrichment**: Run enrich-ioc on all initial IOCs
3. **Prioritize**: Rank IOCs by threat level (malicious > suspicious > clean)

### Phase 2: Expansion

For each high-priority IOC, expand in these directions:

| IOC Type | Expansion Vectors |
|----------|-------------------|
| IP | Reverse DNS, same C-segment, historical domains, certificates |
| Domain | Subdomains (crt.sh), sibling domains, DNS history, WHOIS |
| Hash | Related samples, C2 infrastructure, download URLs |
| URL | Hosting IP, redirect chain, payload hashes |
| Email | Registered domains, breach data, platform accounts |

### Phase 3: Analysis

Apply specialized analysis based on findings:

| Finding | Analysis Skill |
|---------|---------------|
| Multiple related IPs/domains | infra-fingerprint |
| Geographic signals | geo-locate |
| Identity information | person-link |
| Visual content/screenshots | visual-osint |
| Known vulnerabilities | NVD lookup |

### Phase 4: Convergence

Stop expanding when:
- Reached configured depth limit (auto_expand_depth)
- No new high-value IOCs discovered
- Investigation question can be answered
- All expansion paths exhausted

### Phase 5: Reporting

Generate structured report with:
- Executive summary
- IOC timeline
- Relationship graph
- Risk assessment
- Recommended actions

## Expansion Priority Rules

When selecting which IOCs to expand next:

1. **Malicious verdict** IOCs first (highest threat)
2. **Multiple source confirmation** over single source
3. **Recent activity** over historical
4. **Direct relationships** (resolves_to, communicates_with) over indirect
5. **Unexplored types** — prefer expanding into IOC types not yet covered

## Depth Control

| Depth | Behavior |
|-------|----------|
| 1 | Enrich initial IOCs only, no expansion |
| 2 | Expand top-3 related IOCs from initial results (default) |
| 3 | Expand top-3 from depth-2 results |
| 4-5 | Continue expansion (risk of noise increases) |

## Quality Signals

High-value expansion targets:
- IOC appears in multiple threat intelligence pulses
- IOC has recent activity (last 30 days)
- IOC is directly related (not 2+ hops away)
- IOC type provides new dimension (e.g., found domain from IP)

Low-value (skip unless depth allows):
- IOC only appears in 1 old pulse
- IOC is a well-known benign service (Google DNS, Cloudflare, etc.)
- IOC is 3+ hops from initial target
- IOC type already well-covered in current investigation

## Common Investigation Patterns

### Pattern: C2 Infrastructure Mapping
1. Start with known C2 IP/domain
2. enrich-ioc → get related IOCs
3. infra-fingerprint → find infrastructure cluster
4. Expand to all cluster members
5. geo-locate → determine operator location

### Pattern: Phishing Campaign Analysis
1. Start with phishing URL/domain
2. enrich-ioc → get hosting info
3. crt.sh → find related domains (same cert)
4. infra-fingerprint → identify campaign infrastructure
5. visual-osint → confirm phishing template
6. person-link → trace registrant

### Pattern: Malware Attribution
1. Start with malware hash
2. enrich-ioc → get C2 domains/IPs
3. Expand C2 infrastructure
4. infra-fingerprint → cluster related infrastructure
5. person-link → trace operator identity
6. geo-locate → determine origin

### Pattern: Data Breach Investigation
1. Start with leaked email/domain
2. HIBP → find breach sources
3. person-link → correlate identities
4. enrich-ioc on any IPs/domains found
5. infra-fingerprint if infrastructure found

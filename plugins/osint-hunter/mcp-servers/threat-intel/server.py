# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""Unified Threat Intelligence MCP Server — AbuseIPDB + AlienVault OTX."""

import os
import httpx
from fastmcp import FastMCP

mcp = FastMCP("threat-intel")

# ─── AbuseIPDB ────────────────────────────────────────────
ABUSEIPDB_KEY = os.environ.get("ABUSEIPDB_API_KEY", "")
ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2"
ABUSEIPDB_HEADERS = {"Key": ABUSEIPDB_KEY, "Accept": "application/json"}

# ─── OTX ──────────────────────────────────────────────────
OTX_KEY = os.environ.get("OTX_API_KEY", "")
OTX_URL = "https://otx.alienvault.com/api/v1"
OTX_HEADERS = {"X-OTX-API-KEY": OTX_KEY, "Accept": "application/json"}

OTX_TYPE_MAP = {
    "ip": "IPv4",
    "ipv4": "IPv4",
    "ipv6": "IPv6",
    "domain": "domain",
    "hash": "file",
    "md5": "file",
    "sha1": "file",
    "sha256": "file",
    "url": "url",
}


# ═══════════════════════════════════════════════════════════
# AbuseIPDB Tools
# ═══════════════════════════════════════════════════════════

@mcp.tool()
async def abuseipdb_check_ip(ip: str, max_age_days: int = 90) -> dict:
    """Check an IP address against AbuseIPDB. Returns abuse confidence score,
    total reports, categories, ISP, country, and usage type."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{ABUSEIPDB_URL}/check",
            headers=ABUSEIPDB_HEADERS,
            params={"ipAddress": ip, "maxAgeInDays": max_age_days, "verbose": ""},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return {
            "ip": data["ipAddress"],
            "abuse_score": data["abuseConfidenceScore"],
            "total_reports": data["totalReports"],
            "country": data.get("countryCode"),
            "isp": data.get("isp"),
            "usage_type": data.get("usageType"),
            "domain": data.get("domain"),
            "is_tor": data.get("isTor", False),
            "is_whitelisted": data.get("isWhitelisted", False),
            "last_reported": data.get("lastReportedAt"),
            "categories": list(set(
                cat
                for report in (data.get("reports") or [])
                for cat in (report.get("categories") or [])
            )),
        }


@mcp.tool()
async def abuseipdb_check_network(cidr: str) -> dict:
    """Check a CIDR network range for reported IPs. Returns list of
    reported IPs with their abuse scores."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{ABUSEIPDB_URL}/check-block",
            headers=ABUSEIPDB_HEADERS,
            params={"network": cidr, "maxAgeInDays": 30},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return {
            "network": data.get("networkAddress"),
            "netmask": data.get("netmask"),
            "reported_ips": [
                {
                    "ip": item["ipAddress"],
                    "abuse_score": item["abuseConfidenceScore"],
                    "reports": item["numReports"],
                    "country": item.get("countryCode"),
                }
                for item in data.get("reportedAddress", [])
            ],
        }


@mcp.tool()
async def abuseipdb_get_reports(ip: str, limit: int = 25) -> dict:
    """Get detailed abuse reports for an IP address. Returns individual
    reports with timestamps, categories, and reporter comments."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{ABUSEIPDB_URL}/reports",
            headers=ABUSEIPDB_HEADERS,
            params={"ipAddress": ip, "perPage": limit},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return {
            "ip": ip,
            "total": data.get("total", 0),
            "reports": [
                {
                    "reported_at": r["reportedAt"],
                    "categories": r["categories"],
                    "comment": r.get("comment", ""),
                    "reporter_country": r.get("reporterCountryCode"),
                }
                for r in data.get("results", [])[:limit]
            ],
        }


# ═══════════════════════════════════════════════════════════
# OTX Tools
# ═══════════════════════════════════════════════════════════

@mcp.tool()
async def otx_get_indicator(indicator_type: str, value: str) -> dict:
    """Get OTX threat intelligence for an IOC. Returns pulse count,
    tags, malware families, and threat assessment.

    indicator_type: one of ip, ipv4, ipv6, domain, hash, md5, sha1, sha256, url
    value: the IOC value to look up
    """
    section = OTX_TYPE_MAP.get(indicator_type.lower())
    if not section:
        return {"error": f"Unsupported type: {indicator_type}. Use: {list(OTX_TYPE_MAP.keys())}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{OTX_URL}/indicators/{section}/{value}/general",
            headers=OTX_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

        pulses = data.get("pulse_info", {})
        return {
            "indicator": value,
            "type": section,
            "pulse_count": pulses.get("count", 0),
            "tags": list(set(
                tag
                for p in pulses.get("pulses", [])
                for tag in p.get("tags", [])
            ))[:20],
            "malware_families": list(set(
                family
                for p in pulses.get("pulses", [])
                for family in p.get("malware_families", [])
            )),
            "adversary": list(set(
                p.get("adversary", "")
                for p in pulses.get("pulses", [])
                if p.get("adversary")
            )),
            "country": data.get("country_name"),
            "asn": data.get("asn"),
        }


@mcp.tool()
async def otx_get_pulses(query: str, limit: int = 10) -> dict:
    """Search OTX pulses by keyword. Returns matching threat intelligence
    pulses with descriptions, tags, and IOC counts."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{OTX_URL}/search/pulses",
            headers=OTX_HEADERS,
            params={"q": query, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        return {
            "query": query,
            "count": data.get("count", 0),
            "pulses": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "description": (p.get("description") or "")[:200],
                    "tags": p.get("tags", [])[:10],
                    "created": p.get("created"),
                    "modified": p.get("modified"),
                    "indicators_count": p.get("indicator_count", 0),
                    "adversary": p.get("adversary"),
                }
                for p in data.get("results", [])[:limit]
            ],
        }


@mcp.tool()
async def otx_get_related(indicator_type: str, value: str) -> dict:
    """Get related IOCs from OTX pulses containing this indicator.
    Returns other IPs, domains, hashes found in the same pulses.

    indicator_type: one of ip, ipv4, ipv6, domain, hash, md5, sha1, sha256, url
    value: the IOC value to look up
    """
    section = OTX_TYPE_MAP.get(indicator_type.lower())
    if not section:
        return {"error": f"Unsupported type: {indicator_type}. Use: {list(OTX_TYPE_MAP.keys())}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{OTX_URL}/indicators/{section}/{value}/general",
            headers=OTX_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

        related = {"domains": [], "ips": [], "hashes": [], "urls": []}
        for pulse in data.get("pulse_info", {}).get("pulses", [])[:5]:
            pulse_id = pulse["id"]
            detail_resp = await client.get(
                f"{OTX_URL}/pulses/{pulse_id}/indicators",
                headers=OTX_HEADERS,
                params={"limit": 50},
            )
            if detail_resp.status_code != 200:
                continue
            for ind in detail_resp.json().get("results", []):
                ind_type = ind.get("type", "")
                ind_val = ind.get("indicator", "")
                if ind_val == value:
                    continue
                if ind_type in ("IPv4", "IPv6"):
                    related["ips"].append(ind_val)
                elif ind_type == "domain":
                    related["domains"].append(ind_val)
                elif ind_type in ("FileHash-MD5", "FileHash-SHA1", "FileHash-SHA256"):
                    related["hashes"].append(ind_val)
                elif ind_type == "URL":
                    related["urls"].append(ind_val)

        return {
            "indicator": value,
            "related_domains": list(set(related["domains"]))[:20],
            "related_ips": list(set(related["ips"]))[:20],
            "related_hashes": list(set(related["hashes"]))[:20],
            "related_urls": list(set(related["urls"]))[:10],
        }


if __name__ == "__main__":
    mcp.run()

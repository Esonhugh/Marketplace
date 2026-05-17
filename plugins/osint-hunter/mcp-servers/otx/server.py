"""AlienVault OTX MCP Server — threat intelligence pulses and IOC correlation."""

import os
import httpx
from fastmcp import FastMCP

mcp = FastMCP("otx")

API_KEY = os.environ.get("OTX_API_KEY", "")
BASE_URL = "https://otx.alienvault.com/api/v1"
HEADERS = {"X-OTX-API-KEY": API_KEY, "Accept": "application/json"}

# Map user-facing types to OTX API section names
TYPE_MAP = {
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


@mcp.tool()
async def get_indicator(indicator_type: str, value: str) -> dict:
    """Get OTX threat intelligence for an IOC. Returns pulse count,
    tags, malware families, and threat assessment.

    indicator_type: one of ip, ipv4, ipv6, domain, hash, md5, sha1, sha256, url
    value: the IOC value to look up
    """
    section = TYPE_MAP.get(indicator_type.lower())
    if not section:
        return {"error": f"Unsupported type: {indicator_type}. Use: {list(TYPE_MAP.keys())}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/indicators/{section}/{value}/general",
            headers=HEADERS,
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
async def get_pulses(query: str, limit: int = 10) -> dict:
    """Search OTX pulses by keyword. Returns matching threat intelligence
    pulses with descriptions, tags, and IOC counts."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/search/pulses",
            headers=HEADERS,
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
async def get_related(indicator_type: str, value: str) -> dict:
    """Get related IOCs from OTX pulses containing this indicator.
    Returns other IPs, domains, hashes found in the same pulses.

    indicator_type: one of ip, ipv4, ipv6, domain, hash, md5, sha1, sha256, url
    value: the IOC value to look up
    """
    section = TYPE_MAP.get(indicator_type.lower())
    if not section:
        return {"error": f"Unsupported type: {indicator_type}. Use: {list(TYPE_MAP.keys())}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/indicators/{section}/{value}/general",
            headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

        related = {"domains": [], "ips": [], "hashes": [], "urls": []}
        for pulse in data.get("pulse_info", {}).get("pulses", [])[:5]:
            pulse_id = pulse["id"]
            detail_resp = await client.get(
                f"{BASE_URL}/pulses/{pulse_id}/indicators",
                headers=HEADERS,
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

"""AlienVault OTX — threat intelligence pulses and IOC correlation."""

import os
import httpx

KEY = os.environ.get("OTX_API_KEY", "")
URL = "https://otx.alienvault.com/api/v1"

TYPE_MAP = {
    "ip": "IPv4", "ipv4": "IPv4", "ipv6": "IPv6",
    "domain": "domain",
    "hash": "file", "md5": "file", "sha1": "file", "sha256": "file",
    "url": "url",
}


def _headers():
    return {"X-OTX-API-KEY": KEY, "Accept": "application/json"}


def register(mcp):
    @mcp.tool()
    async def otx_get_indicator(indicator_type: str, value: str) -> dict:
        """Get OTX threat intelligence for an IOC — pulse count, tags, malware families.

        indicator_type: ip, ipv4, ipv6, domain, hash, md5, sha1, sha256, url
        """
        section = TYPE_MAP.get(indicator_type.lower())
        if not section:
            return {"error": f"Unsupported type: {indicator_type}. Use: {list(TYPE_MAP.keys())}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{URL}/indicators/{section}/{value}/general", headers=_headers())
            resp.raise_for_status()
            data = resp.json()
            pulses = data.get("pulse_info", {})
            return {
                "indicator": value, "type": section, "pulse_count": pulses.get("count", 0),
                "tags": list(set(tag for p in pulses.get("pulses", []) for tag in p.get("tags", [])))[:20],
                "malware_families": list(set(f for p in pulses.get("pulses", []) for f in p.get("malware_families", []))),
                "adversary": list(set(p.get("adversary", "") for p in pulses.get("pulses", []) if p.get("adversary"))),
                "country": data.get("country_name"), "asn": data.get("asn"),
            }

    @mcp.tool()
    async def otx_get_pulses(query: str, limit: int = 10) -> dict:
        """Search OTX pulses by keyword. Requires OTX_API_KEY."""
        if not KEY:
            return {"error": "OTX_API_KEY required for pulse search"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{URL}/search/pulses", headers=_headers(), params={"q": query, "limit": limit})
            if resp.status_code == 403:
                return {"error": "OTX API key invalid or insufficient permissions"}
            resp.raise_for_status()
            data = resp.json()
            return {"query": query, "count": data.get("count", 0), "pulses": [
                {"id": p["id"], "name": p["name"], "description": (p.get("description") or "")[:200], "tags": p.get("tags", [])[:10], "created": p.get("created"), "indicators_count": p.get("indicator_count", 0)}
                for p in data.get("results", [])[:limit]
            ]}

    @mcp.tool()
    async def otx_get_related(indicator_type: str, value: str) -> dict:
        """Get related IOCs from OTX pulses containing this indicator."""
        section = TYPE_MAP.get(indicator_type.lower())
        if not section:
            return {"error": f"Unsupported type: {indicator_type}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{URL}/indicators/{section}/{value}/general", headers=_headers())
            resp.raise_for_status()
            data = resp.json()
            related = {"domains": [], "ips": [], "hashes": [], "urls": []}
            for pulse in data.get("pulse_info", {}).get("pulses", [])[:5]:
                detail = await client.get(f"{URL}/pulses/{pulse['id']}/indicators", headers=_headers(), params={"limit": 50})
                if detail.status_code != 200:
                    continue
                for ind in detail.json().get("results", []):
                    iv = ind.get("indicator", "")
                    if iv == value:
                        continue
                    it = ind.get("type", "")
                    if it in ("IPv4", "IPv6"):
                        related["ips"].append(iv)
                    elif it == "domain":
                        related["domains"].append(iv)
                    elif "FileHash" in it:
                        related["hashes"].append(iv)
                    elif it == "URL":
                        related["urls"].append(iv)
            return {"indicator": value, "related_domains": list(set(related["domains"]))[:20], "related_ips": list(set(related["ips"]))[:20], "related_hashes": list(set(related["hashes"]))[:20], "related_urls": list(set(related["urls"]))[:10]}


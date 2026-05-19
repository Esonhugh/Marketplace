"""AbuseIPDB — IP reputation and abuse reports."""

import os
import httpx

KEY = os.environ.get("ABUSEIPDB_API_KEY", "")
URL = "https://api.abuseipdb.com/api/v2"


def _headers():
    return {"Key": KEY, "Accept": "application/json"}


def register(mcp):
    @mcp.tool()
    async def abuseipdb_check_ip(ip: str, max_age_days: int = 90) -> dict:
        """Check IP reputation on AbuseIPDB — abuse score, reports, ISP, country."""
        if not KEY:
            return {"error": "ABUSEIPDB_API_KEY not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{URL}/check", headers=_headers(), params={"ipAddress": ip, "maxAgeInDays": max_age_days, "verbose": ""})
            resp.raise_for_status()
            data = resp.json()["data"]
            return {
                "ip": data["ipAddress"], "abuse_score": data["abuseConfidenceScore"],
                "total_reports": data["totalReports"], "country": data.get("countryCode"),
                "isp": data.get("isp"), "usage_type": data.get("usageType"),
                "domain": data.get("domain"), "is_tor": data.get("isTor", False),
                "last_reported": data.get("lastReportedAt"),
                "categories": list(set(cat for r in (data.get("reports") or []) for cat in (r.get("categories") or []))),
            }

    @mcp.tool()
    async def abuseipdb_check_network(cidr: str) -> dict:
        """Check a CIDR range for reported IPs on AbuseIPDB."""
        if not KEY:
            return {"error": "ABUSEIPDB_API_KEY not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{URL}/check-block", headers=_headers(), params={"network": cidr, "maxAgeInDays": 30})
            resp.raise_for_status()
            data = resp.json()["data"]
            return {
                "network": data.get("networkAddress"), "netmask": data.get("netmask"),
                "reported_ips": [{"ip": i["ipAddress"], "abuse_score": i["abuseConfidenceScore"], "reports": i["numReports"]} for i in data.get("reportedAddress", [])],
            }

    @mcp.tool()
    async def abuseipdb_get_reports(ip: str, limit: int = 25) -> dict:
        """Get detailed abuse reports for an IP from AbuseIPDB."""
        if not KEY:
            return {"error": "ABUSEIPDB_API_KEY not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{URL}/reports", headers=_headers(), params={"ipAddress": ip, "perPage": limit})
            resp.raise_for_status()
            data = resp.json()["data"]
            return {"ip": ip, "total": data.get("total", 0), "reports": [{"reported_at": r["reportedAt"], "categories": r["categories"], "comment": r.get("comment", "")} for r in data.get("results", [])[:limit]]}

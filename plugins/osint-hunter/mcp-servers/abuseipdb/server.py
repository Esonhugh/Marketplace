"""AbuseIPDB MCP Server — IP reputation and abuse reports."""

import os
import httpx
from fastmcp import FastMCP

mcp = FastMCP("abuseipdb")

API_KEY = os.environ.get("ABUSEIPDB_API_KEY", "")
BASE_URL = "https://api.abuseipdb.com/api/v2"
HEADERS = {"Key": API_KEY, "Accept": "application/json"}


@mcp.tool()
async def check_ip(ip: str, max_age_days: int = 90) -> dict:
    """Check an IP address against AbuseIPDB. Returns abuse confidence score,
    total reports, categories, ISP, country, and usage type."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/check",
            headers=HEADERS,
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
async def check_network(cidr: str) -> dict:
    """Check a CIDR network range for reported IPs. Returns list of
    reported IPs with their abuse scores."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/check-block",
            headers=HEADERS,
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
async def get_reports(ip: str, limit: int = 25) -> dict:
    """Get detailed abuse reports for an IP address. Returns individual
    reports with timestamps, categories, and reporter comments."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{BASE_URL}/reports",
            headers=HEADERS,
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


if __name__ == "__main__":
    mcp.run()

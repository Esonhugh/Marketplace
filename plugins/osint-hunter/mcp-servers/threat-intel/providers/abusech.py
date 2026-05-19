"""abuse.ch — ThreatFox IOC, URLhaus URL, MalwareBazaar sample lookup."""

import os
import httpx

KEY = os.environ.get("ABUSECH_AUTH_KEY") or os.environ.get("CLAUDE_PLUGIN_OPTION_ABUSECH_KEY", "")

THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"
URLHAUS_URL = "https://urlhaus-api.abuse.ch/v1/"
MALWAREBAZAAR_URL = "https://mb-api.abuse.ch/api/v1/"


def _headers():
    return {"Auth-Key": KEY} if KEY else {}


def register(mcp):
    @mcp.tool()
    async def abusech_threatfox(ioc: str) -> dict:
        """Search ThreatFox for an IOC — malware families, threat types, confidence.

        ioc: IP:port, domain, URL, or hash
        """
        if not KEY:
            return {"error": "ABUSECH_AUTH_KEY not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(THREATFOX_URL, json={"query": "search_ioc", "search_term": ioc}, headers=_headers())
            resp.raise_for_status()
            data = resp.json()
        if data.get("query_status") != "ok" or not data.get("data"):
            return {"ioc": ioc, "matches": []}
        return {"ioc": ioc, "matches": [
            {"ioc": r.get("ioc"), "threat_type": r.get("threat_type"), "malware": r.get("malware_printable"),
             "confidence": r.get("confidence_level"), "first_seen": r.get("first_seen_utc"), "tags": r.get("tags")}
            for r in data["data"][:10]
        ]}

    @mcp.tool()
    async def abusech_urlhaus(url: str) -> dict:
        """Check a URL against URLhaus — malware distribution, threat classification.

        url: full URL to check
        """
        if not KEY:
            return {"error": "ABUSECH_AUTH_KEY not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{URLHAUS_URL}url/", data={"url": url}, headers=_headers())
            resp.raise_for_status()
            data = resp.json()
        if data.get("query_status") != "ok":
            return {"url": url, "status": "not_found"}
        return {
            "url": data.get("url"), "url_status": data.get("url_status"),
            "threat": data.get("threat"), "host": data.get("host"),
            "date_added": data.get("date_added"), "tags": data.get("tags"),
            "payloads": [{"filename": p.get("filename"), "file_type": p.get("file_type"),
                          "sha256": p.get("sha256_hash"), "signature": p.get("signature")}
                         for p in (data.get("payloads") or [])[:5]],
        }

    @mcp.tool()
    async def abusech_malwarebazaar(hash: str) -> dict:
        """Look up a malware sample on MalwareBazaar by hash (MD5/SHA1/SHA256).

        hash: file hash to look up
        """
        if not KEY:
            return {"error": "ABUSECH_AUTH_KEY not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(MALWAREBAZAAR_URL, data={"query": "get_info", "hash": hash}, headers=_headers())
            resp.raise_for_status()
            data = resp.json()
        if data.get("query_status") != "ok" or not data.get("data"):
            return {"hash": hash, "status": "not_found"}
        sample = data["data"][0]
        return {
            "sha256": sample.get("sha256_hash"), "md5": sample.get("md5_hash"),
            "file_type": sample.get("file_type"), "file_size": sample.get("file_size"),
            "signature": sample.get("signature"), "first_seen": sample.get("first_seen"),
            "tags": sample.get("tags"), "intelligence": sample.get("intelligence", {}),
        }

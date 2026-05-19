"""crt.sh — certificate transparency subdomain discovery."""

import httpx

CRTSH_URL = "https://crt.sh/"


def register(mcp):
    @mcp.tool()
    async def crtsh_subdomains(domain: str, include_expired: bool = False) -> dict:
        """Discover subdomains via crt.sh certificate transparency logs.

        domain: target domain (e.g. example.com)
        include_expired: include expired certificates (default False)
        """
        params = {"q": f"%.{domain}", "output": "json"}
        if not include_expired:
            params["exclude"] = "expired"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(CRTSH_URL, params=params, follow_redirects=True)
            if resp.status_code != 200:
                return {"error": f"crt.sh returned HTTP {resp.status_code}", "domain": domain}
            entries = resp.json()

        if not entries:
            return {"domain": domain, "subdomains": [], "total_certs": 0}

        subdomains = set()
        for entry in entries[:200]:
            for name in entry.get("name_value", "").split("\n"):
                name = name.strip().lower()
                if name and not name.startswith("*"):
                    subdomains.add(name)

        return {
            "domain": domain,
            "total_certs": len(entries),
            "unique_subdomains": len(subdomains),
            "subdomains": sorted(subdomains)[:100],
        }

    @mcp.tool()
    async def crtsh_certs(domain: str, limit: int = 20) -> dict:
        """Get recent certificate details for a domain from crt.sh.

        domain: target domain
        limit: max certificates to return (default 20)
        """
        params = {"q": f"%.{domain}", "output": "json", "exclude": "expired"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(CRTSH_URL, params=params, follow_redirects=True)
            if resp.status_code != 200:
                return {"error": f"crt.sh returned HTTP {resp.status_code}", "domain": domain}
            entries = resp.json()

        if not entries:
            return {"domain": domain, "certs": []}

        certs = []
        for entry in entries[:limit]:
            certs.append({
                "id": entry.get("id"),
                "issuer": entry.get("issuer_name"),
                "common_name": entry.get("common_name"),
                "name_value": entry.get("name_value"),
                "not_before": entry.get("not_before"),
                "not_after": entry.get("not_after"),
                "serial": entry.get("serial_number"),
            })

        return {"domain": domain, "total_certs": len(entries), "certs": certs}

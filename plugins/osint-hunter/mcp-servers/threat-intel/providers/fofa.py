"""FOFA — internet asset search engine."""

import os
from base64 import b64encode

import httpx

KEY = os.environ.get("FOFA_KEY") or os.environ.get("CLAUDE_PLUGIN_OPTION_FOFA_KEY", "")
API = "https://fofa.info/api/v1"


def register(mcp):
    @mcp.tool()
    async def fofa_search(query: str, fields: str = "ip,port,protocol,host,title", size: int = 50) -> dict:
        """Search FOFA for internet assets.

        query: FOFA syntax (e.g. 'host="example.com"', 'port="443" && country="CN"')
        fields: ip,port,protocol,host,domain,title,server,country,city,as_organization,banner
        size: max results (default 50)
        """
        if not KEY:
            return {"error": "FOFA_KEY not configured"}
        qbase64 = b64encode(query.encode()).decode()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{API}/search/all", params={"key": KEY, "qbase64": qbase64, "size": size, "fields": fields})
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return {"error": data.get("errmsg", "Unknown FOFA error")}
            field_list = fields.split(",")
            results = [dict(zip(field_list, row)) for row in data.get("results", [])]
            return {"query": query, "total": data.get("size", 0), "count": len(results), "results": results}

    @mcp.tool()
    async def fofa_count(query: str) -> dict:
        """Get total result count for a FOFA query without fetching data."""
        if not KEY:
            return {"error": "FOFA_KEY not configured"}
        qbase64 = b64encode(query.encode()).decode()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{API}/search/all", params={"key": KEY, "qbase64": qbase64, "size": 1, "fields": "ip"})
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return {"error": data.get("errmsg", "Unknown FOFA error")}
            return {"query": query, "count": data.get("size", 0)}

    @mcp.tool()
    async def fofa_stats(query: str, fields: str = "title,country", size: int = 5) -> dict:
        """Get aggregated statistics for a FOFA query (top values by field).

        fields: title,country,city,protocol,server,domain,os,as_organization
        """
        if not KEY:
            return {"error": "FOFA_KEY not configured"}
        qbase64 = b64encode(query.encode()).decode()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{API}/search/stats", params={"key": KEY, "qbase64": qbase64, "fields": fields, "size": size})
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return {"error": data.get("errmsg", "Unknown FOFA error")}
            return {"query": query, "stats": data.get("aggs", data)}

    @mcp.tool()
    async def fofa_host(host: str) -> dict:
        """Get detailed host info (IP or domain) from FOFA — ports, protocols, products."""
        if not KEY:
            return {"error": "FOFA_KEY not configured"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{API}/host/{host}", params={"key": KEY, "detail": "true"})
            resp.raise_for_status()
            return resp.json()


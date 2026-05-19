# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.0",
#     "httpx>=0.27",
# ]
# ///
"""Unified Threat Intelligence MCP Server."""

import os
from fastmcp import FastMCP

mcp = FastMCP("threat-intel")

# Always-available providers (no auth required)
from providers.crtsh import register as register_crtsh
from providers.nvd import register as register_nvd
from providers.otx import register as register_otx

register_crtsh(mcp)
register_nvd(mcp)
register_otx(mcp)

# Key-gated providers — only register if API key is configured
from providers import fofa, abuseipdb, abusech

if fofa.KEY:
    from providers.fofa import register as register_fofa
    register_fofa(mcp)

if abuseipdb.KEY:
    from providers.abuseipdb import register as register_abuseipdb
    register_abuseipdb(mcp)

if abusech.KEY:
    from providers.abusech import register as register_abusech
    register_abusech(mcp)


@mcp.tool()
async def available_tools() -> dict:
    """List all registered tools and which providers are active."""
    from providers import fofa, abuseipdb, otx, nvd, abusech
    sources = {
        "crtsh": {"loaded": True, "auth_required": False, "tools": ["crtsh_subdomains", "crtsh_certs"]},
        "nvd": {"loaded": True, "auth_required": False, "tools": ["nvd_cve_lookup", "nvd_search"]},
        "otx": {"loaded": True, "auth_required": False, "note": "key optional, needed for pulse search", "tools": ["otx_get_indicator", "otx_get_pulses", "otx_get_related"]},
        "fofa": {"loaded": bool(fofa.KEY), "auth_required": True, "tools": ["fofa_search", "fofa_count", "fofa_stats", "fofa_host"]},
        "abuseipdb": {"loaded": bool(abuseipdb.KEY), "auth_required": True, "tools": ["abuseipdb_check_ip", "abuseipdb_check_network", "abuseipdb_get_reports"]},
        "abusech": {"loaded": bool(abusech.KEY), "auth_required": True, "tools": ["abusech_threatfox", "abusech_urlhaus", "abusech_malwarebazaar"]},
    }
    active = [t for s in sources.values() if s["loaded"] for t in s["tools"]]
    inactive = [t for s in sources.values() if not s["loaded"] for t in s["tools"]]
    return {"sources": sources, "active_tools": active, "inactive_providers": [k for k, v in sources.items() if not v["loaded"]]}


if __name__ == "__main__":
    mcp.run()

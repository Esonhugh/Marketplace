"""NVD (National Vulnerability Database) — CVE lookup and search."""

import os
import httpx

KEY = os.environ.get("NVD_API_KEY") or os.environ.get("CLAUDE_PLUGIN_OPTION_NVD_KEY", "")
NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _headers():
    h = {}
    if KEY:
        h["apiKey"] = KEY
    return h


def _extract_cvss(metrics: dict) -> tuple:
    for version in ("cvssMetricV31", "cvssMetricV30"):
        if version in metrics:
            cvss_data = metrics[version][0].get("cvssData", {})
            return cvss_data.get("baseScore"), cvss_data.get("baseSeverity"), cvss_data.get("vectorString")
    if "cvssMetricV2" in metrics:
        cvss_data = metrics["cvssMetricV2"][0].get("cvssData", {})
        return cvss_data.get("baseScore"), None, cvss_data.get("vectorString")
    return None, None, None


def register(mcp):
    @mcp.tool()
    async def nvd_cve_lookup(cve_id: str) -> dict:
        """Look up a CVE by ID from NVD — description, CVSS score, CWEs, references.

        cve_id: CVE identifier (e.g. CVE-2023-44487)
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(NVD_BASE, params={"cveId": cve_id}, headers=_headers())
            resp.raise_for_status()
            data = resp.json()

        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return {"error": f"CVE {cve_id} not found"}

        cve = vulns[0].get("cve", {})
        metrics = cve.get("metrics", {})
        score, severity, vector = _extract_cvss(metrics)

        descriptions = cve.get("descriptions", [])
        desc_en = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

        cwes = []
        for weakness in cve.get("weaknesses", []):
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en":
                    cwes.append(desc.get("value"))

        refs = [{"url": r.get("url"), "source": r.get("source")} for r in cve.get("references", [])[:10]]

        return {
            "cve_id": cve.get("id"),
            "description": desc_en[:500],
            "published": cve.get("published"),
            "last_modified": cve.get("lastModified"),
            "cvss_score": score,
            "cvss_severity": severity,
            "cvss_vector": vector,
            "cwes": cwes,
            "references": refs,
        }

    @mcp.tool()
    async def nvd_search(keyword: str, limit: int = 10) -> dict:
        """Search NVD for CVEs by keyword.

        keyword: search term (e.g. 'apache log4j', 'openssl buffer overflow')
        limit: max results (default 10, max 50)
        """
        limit = min(limit, 50)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(NVD_BASE, params={"keywordSearch": keyword, "resultsPerPage": limit}, headers=_headers())
            resp.raise_for_status()
            data = resp.json()

        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return {"keyword": keyword, "total_results": 0, "results": []}

        results = []
        for v in vulns[:limit]:
            cve = v.get("cve", {})
            score, severity, _ = _extract_cvss(cve.get("metrics", {}))
            descriptions = cve.get("descriptions", [])
            desc_en = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")
            results.append({
                "cve_id": cve.get("id"),
                "description": desc_en[:200],
                "cvss_score": score,
                "cvss_severity": severity,
                "published": cve.get("published"),
            })

        return {"keyword": keyword, "total_results": data.get("totalResults", 0), "results": results}

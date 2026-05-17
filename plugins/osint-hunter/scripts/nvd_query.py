# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""NVD (National Vulnerability Database) query script — CVE lookup and keyword search."""

import argparse
import json
import sys
import os
import httpx

NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def query_cve(cve_id: str, api_key: str | None = None) -> dict:
    """Look up a specific CVE by ID."""
    headers = {}
    if api_key:
        headers["apiKey"] = api_key

    resp = httpx.get(
        NVD_BASE,
        params={"cveId": cve_id},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    vulns = data.get("vulnerabilities", [])
    if not vulns:
        return {"source": "nvd", "status": "no_data", "error": None, "data": None}

    cve = vulns[0].get("cve", {})
    metrics = cve.get("metrics", {})

    # Extract CVSS score (prefer v3.1, fallback to v3.0, then v2.0)
    cvss_score = None
    cvss_severity = None
    cvss_vector = None
    for version in ("cvssMetricV31", "cvssMetricV30"):
        if version in metrics:
            cvss_data = metrics[version][0].get("cvssData", {})
            cvss_score = cvss_data.get("baseScore")
            cvss_severity = cvss_data.get("baseSeverity")
            cvss_vector = cvss_data.get("vectorString")
            break
    if cvss_score is None and "cvssMetricV2" in metrics:
        cvss_data = metrics["cvssMetricV2"][0].get("cvssData", {})
        cvss_score = cvss_data.get("baseScore")
        cvss_vector = cvss_data.get("vectorString")

    # Extract descriptions
    descriptions = cve.get("descriptions", [])
    desc_en = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

    # Extract references
    refs = [
        {"url": r.get("url"), "source": r.get("source")}
        for r in cve.get("references", [])[:10]
    ]

    # Extract weaknesses (CWE)
    cwes = []
    for weakness in cve.get("weaknesses", []):
        for desc in weakness.get("description", []):
            if desc.get("lang") == "en":
                cwes.append(desc.get("value"))

    return {
        "source": "nvd",
        "status": "success",
        "error": None,
        "data": {
            "cve_id": cve.get("id"),
            "description": desc_en[:500],
            "published": cve.get("published"),
            "last_modified": cve.get("lastModified"),
            "cvss_score": cvss_score,
            "cvss_severity": cvss_severity,
            "cvss_vector": cvss_vector,
            "cwes": cwes,
            "references": refs,
        },
    }


def search_cves(keyword: str, api_key: str | None = None, limit: int = 10) -> dict:
    """Search CVEs by keyword."""
    headers = {}
    if api_key:
        headers["apiKey"] = api_key

    resp = httpx.get(
        NVD_BASE,
        params={"keywordSearch": keyword, "resultsPerPage": limit},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    vulns = data.get("vulnerabilities", [])
    if not vulns:
        return {"source": "nvd", "status": "no_data", "error": None, "data": None}

    results = []
    for v in vulns[:limit]:
        cve = v.get("cve", {})
        metrics = cve.get("metrics", {})
        score = None
        for version in ("cvssMetricV31", "cvssMetricV30"):
            if version in metrics:
                score = metrics[version][0].get("cvssData", {}).get("baseScore")
                break

        descriptions = cve.get("descriptions", [])
        desc_en = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

        results.append({
            "cve_id": cve.get("id"),
            "description": desc_en[:200],
            "cvss_score": score,
            "published": cve.get("published"),
        })

    return {
        "source": "nvd",
        "status": "success",
        "error": None,
        "data": {
            "keyword": keyword,
            "total_results": data.get("totalResults", 0),
            "results": results,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="NVD vulnerability query")
    parser.add_argument("--type", required=True, choices=["cve", "search"],
                        help="Query type: cve (lookup by ID), search (keyword search)")
    parser.add_argument("--value", required=True, help="CVE ID or search keyword")
    parser.add_argument("--limit", type=int, default=10, help="Max results for search")
    parser.add_argument("--format", default="json", choices=["json", "text"])
    args = parser.parse_args()

    api_key = os.environ.get("NVD_API_KEY") or os.environ.get("CLAUDE_PLUGIN_OPTION_NVD_KEY")

    try:
        if args.type == "cve":
            result = query_cve(args.value, api_key)
        elif args.type == "search":
            result = search_cves(args.value, api_key, args.limit)
        else:
            result = {"source": "nvd", "status": "error", "error": f"Unknown type: {args.type}", "data": None}
    except httpx.HTTPStatusError as e:
        result = {"source": "nvd", "status": "error", "error": f"HTTP {e.response.status_code}", "data": None}
    except httpx.TimeoutException:
        result = {"source": "nvd", "status": "error", "error": "Request timed out", "data": None}
    except Exception as e:
        result = {"source": "nvd", "status": "error", "error": str(e), "data": None}

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()

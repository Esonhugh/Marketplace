# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""crt.sh certificate transparency query — subdomain discovery and cert history."""

import argparse
import json
import sys
import httpx

CRTSH_URL = "https://crt.sh/"


def query_crtsh(domain: str, include_expired: bool = False) -> dict:
    """Query crt.sh for certificates matching a domain."""
    params = {"q": f"%.{domain}", "output": "json"}
    if not include_expired:
        params["exclude"] = "expired"

    resp = httpx.get(CRTSH_URL, params=params, timeout=30, follow_redirects=True)
    resp.raise_for_status()

    try:
        entries = resp.json()
    except json.JSONDecodeError:
        return {"source": "crtsh", "status": "error", "error": "Invalid JSON response", "data": None}

    if not entries:
        return {"source": "crtsh", "status": "no_data", "error": None, "data": None}

    # Deduplicate subdomains
    subdomains = set()
    certs = []
    for entry in entries[:200]:
        name_value = entry.get("name_value", "")
        for name in name_value.split("\n"):
            name = name.strip().lower()
            if name and not name.startswith("*"):
                subdomains.add(name)

        certs.append({
            "id": entry.get("id"),
            "issuer": entry.get("issuer_name"),
            "common_name": entry.get("common_name"),
            "name_value": name_value,
            "not_before": entry.get("not_before"),
            "not_after": entry.get("not_after"),
            "serial": entry.get("serial_number"),
        })

    # Sort subdomains and limit certs
    sorted_subdomains = sorted(subdomains)

    return {
        "source": "crtsh",
        "status": "success",
        "error": None,
        "data": {
            "domain": domain,
            "total_certs": len(entries),
            "unique_subdomains": len(sorted_subdomains),
            "subdomains": sorted_subdomains[:100],
            "recent_certs": certs[:20],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="crt.sh certificate transparency query")
    parser.add_argument("--type", default="domain", choices=["domain"],
                        help="Query type (currently only domain)")
    parser.add_argument("--value", required=True, help="Domain to query")
    parser.add_argument("--include-expired", action="store_true",
                        help="Include expired certificates")
    parser.add_argument("--format", default="json", choices=["json", "text"])
    args = parser.parse_args()

    try:
        result = query_crtsh(args.value, include_expired=args.include_expired)
    except httpx.HTTPStatusError as e:
        result = {"source": "crtsh", "status": "error", "error": f"HTTP {e.response.status_code}", "data": None}
    except httpx.TimeoutException:
        result = {"source": "crtsh", "status": "error", "error": "Request timed out", "data": None}
    except Exception as e:
        result = {"source": "crtsh", "status": "error", "error": str(e), "data": None}

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()

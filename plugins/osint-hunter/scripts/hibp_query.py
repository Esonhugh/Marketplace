# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""Have I Been Pwned (HIBP) query script — email breach lookup and domain search."""

import argparse
import json
import sys
import os
import httpx

HIBP_BASE = "https://haveibeenpwned.com/api/v3"
HEADERS_BASE = {"User-Agent": "osint-hunter-plugin"}


def query_email(email: str, api_key: str) -> dict:
    """Check if an email has been in known data breaches."""
    headers = {**HEADERS_BASE, "hibp-api-key": api_key}

    resp = httpx.get(
        f"{HIBP_BASE}/breachedaccount/{email}",
        headers=headers,
        params={"truncateResponse": "false"},
        timeout=30,
    )

    if resp.status_code == 404:
        return {"source": "hibp", "status": "no_data", "error": None, "data": {"email": email, "breaches": []}}
    resp.raise_for_status()
    breaches = resp.json()

    return {
        "source": "hibp",
        "status": "success",
        "error": None,
        "data": {
            "email": email,
            "breach_count": len(breaches),
            "breaches": [
                {
                    "name": b.get("Name"),
                    "title": b.get("Title"),
                    "domain": b.get("Domain"),
                    "breach_date": b.get("BreachDate"),
                    "added_date": b.get("AddedDate"),
                    "pwn_count": b.get("PwnCount"),
                    "data_classes": b.get("DataClasses", []),
                    "is_verified": b.get("IsVerified"),
                    "is_sensitive": b.get("IsSensitive"),
                }
                for b in breaches[:20]
            ],
        },
    }


def query_domain(domain: str, api_key: str) -> dict:
    """Search for breaches affecting a domain."""
    headers = {**HEADERS_BASE, "hibp-api-key": api_key}

    resp = httpx.get(
        f"{HIBP_BASE}/breaches",
        headers=headers,
        params={"domain": domain},
        timeout=30,
    )
    resp.raise_for_status()
    breaches = resp.json()

    if not breaches:
        return {"source": "hibp", "status": "no_data", "error": None, "data": {"domain": domain, "breaches": []}}

    return {
        "source": "hibp",
        "status": "success",
        "error": None,
        "data": {
            "domain": domain,
            "breach_count": len(breaches),
            "breaches": [
                {
                    "name": b.get("Name"),
                    "title": b.get("Title"),
                    "breach_date": b.get("BreachDate"),
                    "pwn_count": b.get("PwnCount"),
                    "data_classes": b.get("DataClasses", []),
                }
                for b in breaches[:20]
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="HIBP breach query")
    parser.add_argument("--type", required=True, choices=["email", "domain"],
                        help="Query type: email (breach lookup), domain (domain breaches)")
    parser.add_argument("--value", required=True, help="Email address or domain")
    parser.add_argument("--format", default="json", choices=["json", "text"])
    args = parser.parse_args()

    api_key = os.environ.get("HIBP_API_KEY") or os.environ.get("CLAUDE_PLUGIN_OPTION_HIBP_KEY")
    if not api_key:
        result = {"source": "hibp", "status": "error", "error": "HIBP API key required (paid)", "data": None}
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()
        sys.exit(1)

    try:
        if args.type == "email":
            result = query_email(args.value, api_key)
        elif args.type == "domain":
            result = query_domain(args.value, api_key)
        else:
            result = {"source": "hibp", "status": "error", "error": f"Unknown type: {args.type}", "data": None}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            result = {"source": "hibp", "status": "error", "error": "Invalid API key", "data": None}
        elif e.response.status_code == 429:
            result = {"source": "hibp", "status": "error", "error": "Rate limited, retry later", "data": None}
        else:
            result = {"source": "hibp", "status": "error", "error": f"HTTP {e.response.status_code}", "data": None}
    except httpx.TimeoutException:
        result = {"source": "hibp", "status": "error", "error": "Request timed out", "data": None}
    except Exception as e:
        result = {"source": "hibp", "status": "error", "error": str(e), "data": None}

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
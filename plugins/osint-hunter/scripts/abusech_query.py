# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27"]
# ///
"""abuse.ch unified query script — ThreatFox IOC, URLhaus URL, MalwareBazaar sample lookup."""

import argparse
import json
import sys
import httpx

THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"
URLHAUS_URL = "https://urlhaus-api.abuse.ch/v1/"
MALWAREBAZAAR_URL = "https://mb-api.abuse.ch/api/v1/"


def query_threatfox(value: str) -> dict:
    """Query ThreatFox for IOC match."""
    resp = httpx.post(
        THREATFOX_URL,
        json={"query": "search_ioc", "search_term": value},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("query_status") != "ok" or not data.get("data"):
        return {"source": "threatfox", "status": "no_data", "error": None, "data": None}

    results = data["data"][:10]
    return {
        "source": "threatfox",
        "status": "success",
        "error": None,
        "data": {
            "matches": [
                {
                    "ioc": r.get("ioc"),
                    "threat_type": r.get("threat_type"),
                    "malware": r.get("malware_printable"),
                    "confidence": r.get("confidence_level"),
                    "first_seen": r.get("first_seen_utc"),
                    "last_seen": r.get("last_seen_utc"),
                    "tags": r.get("tags"),
                }
                for r in results
            ],
        },
    }


def query_urlhaus(value: str) -> dict:
    """Query URLhaus for malicious URL."""
    resp = httpx.post(
        f"{URLHAUS_URL}url/",
        data={"url": value},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("query_status") != "ok":
        return {"source": "urlhaus", "status": "no_data", "error": None, "data": None}

    return {
        "source": "urlhaus",
        "status": "success",
        "error": None,
        "data": {
            "url": data.get("url"),
            "url_status": data.get("url_status"),
            "threat": data.get("threat"),
            "host": data.get("host"),
            "date_added": data.get("date_added"),
            "tags": data.get("tags"),
            "payloads": [
                {
                    "filename": p.get("filename"),
                    "file_type": p.get("file_type"),
                    "sha256": p.get("sha256_hash"),
                    "signature": p.get("signature"),
                }
                for p in (data.get("payloads") or [])[:5]
            ],
        },
    }


def query_malwarebazaar(hash_value: str) -> dict:
    """Query MalwareBazaar for malware sample by hash."""
    resp = httpx.post(
        f"{MALWAREBAZAAR_URL}",
        data={"query": "get_info", "hash": hash_value},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("query_status") != "ok" or not data.get("data"):
        return {"source": "malwarebazaar", "status": "no_data", "error": None, "data": None}

    sample = data["data"][0]
    return {
        "source": "malwarebazaar",
        "status": "success",
        "error": None,
        "data": {
            "sha256": sample.get("sha256_hash"),
            "md5": sample.get("md5_hash"),
            "file_type": sample.get("file_type"),
            "file_size": sample.get("file_size"),
            "signature": sample.get("signature"),
            "first_seen": sample.get("first_seen"),
            "last_seen": sample.get("last_seen"),
            "tags": sample.get("tags"),
            "intelligence": sample.get("intelligence", {}),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="abuse.ch unified query")
    parser.add_argument("--type", required=True, choices=["ioc", "url", "hash"],
                        help="Query type: ioc (ThreatFox), url (URLhaus), hash (MalwareBazaar)")
    parser.add_argument("--value", required=True, help="IOC value to query")
    parser.add_argument("--format", default="json", choices=["json", "text"])
    args = parser.parse_args()

    try:
        if args.type == "ioc":
            result = query_threatfox(args.value)
        elif args.type == "url":
            result = query_urlhaus(args.value)
        elif args.type == "hash":
            result = query_malwarebazaar(args.value)
        else:
            result = {"source": "abusech", "status": "error", "error": f"Unknown type: {args.type}", "data": None}
    except httpx.HTTPStatusError as e:
        result = {"source": "abusech", "status": "error", "error": f"HTTP {e.response.status_code}", "data": None}
    except httpx.TimeoutException:
        result = {"source": "abusech", "status": "error", "error": "Request timed out", "data": None}
    except Exception as e:
        result = {"source": "abusech", "status": "error", "error": str(e), "data": None}

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()

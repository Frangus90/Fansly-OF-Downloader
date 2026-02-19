"""HAR File API Parser - Discover API endpoints from Chrome DevTools HAR exports.

Usage:
    python tools/har_parser.py FAN session.har
    python tools/har_parser.py OF session.har

Parses HAR files to extract Fansly/OnlyFans API endpoints,
then diffs against known endpoints in the codebase.
Reports are saved to the tools/ directory automatically.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SCRIPT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Known endpoint registry
# ---------------------------------------------------------------------------

KNOWN_ENDPOINTS: dict[str, dict] = {
    "fansly": {
        "base_url": "https://apiv3.fansly.com/api/v1",
        "endpoints": [
            "/account/me",
            "/account",
            "/subscriptions",
            "/account/media/orders/",
            "/account/media",
            "/post",
            "/timelinenew/{id}",
            "/messaging/groups",
            "/message",
            "/device/id",
        ],
    },
    "onlyfans": {
        "base_url": "https://onlyfans.com/api2/v2",
        "endpoints": [
            "/users/me",
            "/users/{id}",
            "/users/{id}/posts",
            "/posts/{id}",
            "/users/{id}/posts/photos",
            "/subscriptions/subscribes",
            "/chats",
            "/chats/{id}/messages",
        ],
    },
}

# Patterns for dynamic path segments
NUMERIC_ID = re.compile(r"^\d{4,}$")
COMMA_IDS = re.compile(r"^\d+(,\d+)+$")

# Headers to strip values from (privacy)
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "fansly-client-check",
    "fansly-session-id",
    "x-bc",
    "sign",
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ParsedEndpoint:
    platform: str
    method: str
    raw_url: str
    normalized_path: str
    query_params: dict[str, list[str]]
    request_headers: list[str]
    response_status: int
    response_shape: dict | None


@dataclass
class EndpointGroup:
    method: str
    normalized_path: str
    hit_count: int = 0
    status: str = "NEW"
    query_params: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    sample_urls: list[str] = field(default_factory=list)
    request_headers: set[str] = field(default_factory=set)
    response_statuses: list[int] = field(default_factory=list)
    response_shape: dict | None = None


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def load_har(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "log" not in data or "entries" not in data["log"]:
        raise ValueError(f"Invalid HAR file: {file_path}")
    return data


def detect_platform(url: str) -> tuple[str, str] | None:
    for name, info in KNOWN_ENDPOINTS.items():
        if url.startswith(info["base_url"]):
            return name, info["base_url"]
    return None


def normalize_path(path: str) -> str:
    segments = path.strip("/").split("/")
    normalized = []
    for seg in segments:
        if NUMERIC_ID.match(seg):
            normalized.append("{id}")
        elif COMMA_IDS.match(seg):
            normalized.append("{ids}")
        else:
            normalized.append(seg)
    return "/" + "/".join(normalized) if normalized else "/"


def strip_base_path(url_path: str, base_url: str) -> str:
    base_path = urlparse(base_url).path
    if url_path.startswith(base_path):
        return url_path[len(base_path):] or "/"
    return url_path


def extract_query_params(entry: dict) -> dict[str, list[str]]:
    params: dict[str, list[str]] = defaultdict(list)
    for item in entry.get("request", {}).get("queryString", []):
        params[item["name"]].append(item.get("value", ""))
    return dict(params)


def extract_response_shape(entry: dict) -> dict | None:
    content = entry.get("response", {}).get("content", {})
    mime = content.get("mimeType", "")
    if "json" not in mime:
        return None

    text = content.get("text", "")
    if not text:
        return None

    encoding = content.get("encoding", "")
    if encoding == "base64":
        try:
            text = base64.b64decode(text).decode("utf-8")
        except Exception:
            return None

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(data, dict):
        return {k: type(v).__name__ for k, v in data.items()}
    if isinstance(data, list):
        return {"_type": "array", "_length": len(data)}
    return None


def extract_header_names(entry: dict) -> list[str]:
    headers = entry.get("request", {}).get("headers", [])
    return [h["name"].lower() for h in headers]


def parse_har_entries(
    har_data: dict, include_response: bool = True
) -> tuple[list[ParsedEndpoint], int]:
    entries = har_data["log"]["entries"]
    total = len(entries)
    parsed = []

    for entry in entries:
        url = entry.get("request", {}).get("url", "")
        result = detect_platform(url)
        if result is None:
            continue

        platform, base_url = result
        method = entry["request"].get("method", "GET").upper()

        # Skip OPTIONS preflight requests
        if method == "OPTIONS":
            continue

        parsed_url = urlparse(url)
        relative = strip_base_path(parsed_url.path, base_url)
        norm = normalize_path(relative)

        response_shape = None
        if include_response:
            response_shape = extract_response_shape(entry)

        parsed.append(ParsedEndpoint(
            platform=platform,
            method=method,
            raw_url=url,
            normalized_path=norm,
            query_params=extract_query_params(entry),
            request_headers=extract_header_names(entry),
            response_status=entry.get("response", {}).get("status", 0),
            response_shape=response_shape,
        ))

    return parsed, total


def group_endpoints(
    endpoints: list[ParsedEndpoint],
) -> dict[str, list[EndpointGroup]]:
    grouped: dict[str, dict[str, EndpointGroup]] = defaultdict(dict)

    for ep in endpoints:
        key = f"{ep.method} {ep.normalized_path}"
        platform_groups = grouped[ep.platform]

        if key not in platform_groups:
            platform_groups[key] = EndpointGroup(
                method=ep.method,
                normalized_path=ep.normalized_path,
            )

        group = platform_groups[key]
        group.hit_count += 1

        for param, values in ep.query_params.items():
            group.query_params[param].update(values)

        if len(group.sample_urls) < 3:
            group.sample_urls.append(ep.raw_url)

        group.request_headers.update(ep.request_headers)
        group.response_statuses.append(ep.response_status)

        if group.response_shape is None and ep.response_shape is not None:
            group.response_shape = ep.response_shape

    return {
        platform: sorted(groups.values(), key=lambda g: g.normalized_path)
        for platform, groups in grouped.items()
    }


def match_known(path: str, known_paths: list[str]) -> bool:
    """Check if a normalized path matches any known endpoint pattern."""
    # Strip trailing slashes for comparison
    clean = path.rstrip("/")
    for known in known_paths:
        if clean == known.rstrip("/"):
            return True
        # Handle patterns where known has {id} and discovered also has {id}
        known_parts = known.rstrip("/").split("/")
        path_parts = clean.split("/")
        if len(known_parts) != len(path_parts):
            continue
        if all(
            kp == pp or kp.startswith("{")
            for kp, pp in zip(known_parts, path_parts)
        ):
            return True
    return False


def diff_against_known(
    grouped: dict[str, list[EndpointGroup]],
    platform_filter: str | None = None,
) -> dict[str, dict[str, list[str]]]:
    diff: dict[str, dict[str, list[str]]] = {}

    platforms = KNOWN_ENDPOINTS.items()
    if platform_filter:
        platforms = [
            (k, v) for k, v in platforms if k == platform_filter
        ]

    for platform, info in platforms:
        known_paths = info["endpoints"]
        discovered = grouped.get(platform, [])
        discovered_paths = [g.normalized_path for g in discovered]

        known_found = []
        new_found = []

        for group in discovered:
            if match_known(group.normalized_path, known_paths):
                group.status = "KNOWN"
                known_found.append(group.normalized_path)
            else:
                group.status = "NEW"
                new_found.append(group.normalized_path)

        # Find endpoints we know about but didn't see in the HAR
        missing = []
        for kp in known_paths:
            if not any(match_known(dp, [kp]) for dp in discovered_paths):
                missing.append(kp)

        diff[platform] = {
            "known": sorted(set(known_found)),
            "new": sorted(set(new_found)),
            "missing": sorted(missing),
        }

    return diff


def build_report(
    har_files: list[str],
    grouped: dict[str, list[EndpointGroup]],
    diff: dict,
    total_requests: int,
    api_requests: int,
) -> dict:
    platforms = {}
    for platform, groups in grouped.items():
        base_url = KNOWN_ENDPOINTS.get(platform, {}).get("base_url", "")
        endpoints = []
        for g in groups:
            endpoints.append({
                "path": g.normalized_path,
                "method": g.method,
                "hit_count": g.hit_count,
                "status": g.status,
                "query_params": {
                    k: sorted(v) for k, v in g.query_params.items()
                },
                "sample_urls": g.sample_urls,
                "request_headers": sorted(g.request_headers),
                "response_statuses": g.response_statuses,
                "response_shape": g.response_shape,
            })
        platforms[platform] = {
            "base_url": base_url,
            "endpoints": endpoints,
        }

    return {
        "metadata": {
            "har_files": har_files,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "total_requests": total_requests,
            "api_requests": api_requests,
        },
        "platforms": platforms,
        "diff": diff,
    }


# ---------------------------------------------------------------------------
# Platform flag mapping
# ---------------------------------------------------------------------------

PLATFORM_FLAGS = {
    "FAN": "fansly",
    "OF": "onlyfans",
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse HAR files to discover Fansly/OnlyFans API endpoints.",
        epilog="Examples:\n"
               "  python tools/har_parser.py FAN session.har\n"
               "  python tools/har_parser.py OF session1.har session2.har\n"
               "  python tools/har_parser.py FAN session.har --diff-only\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "platform",
        choices=list(PLATFORM_FLAGS.keys()),
        help="Platform the HAR was captured from (FAN = Fansly, OF = OnlyFans)",
    )
    parser.add_argument(
        "har_files",
        nargs="+",
        help="Path to one or more .har files",
    )
    parser.add_argument(
        "--diff-only",
        action="store_true",
        help="Only show NEW/unknown endpoints",
    )
    parser.add_argument(
        "--no-response",
        action="store_true",
        help="Skip response body analysis",
    )
    args = parser.parse_args()

    platform_filter = PLATFORM_FLAGS[args.platform]

    all_parsed: list[ParsedEndpoint] = []
    total_requests = 0

    for har_file in args.har_files:
        try:
            har_data = load_har(har_file)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading {har_file}: {e}", file=sys.stderr)
            sys.exit(1)

        parsed, total = parse_har_entries(
            har_data, include_response=not args.no_response
        )
        all_parsed.extend(parsed)
        total_requests += total

    all_parsed = [ep for ep in all_parsed if ep.platform == platform_filter]

    grouped = group_endpoints(all_parsed)
    diff = diff_against_known(grouped, platform_filter=platform_filter)

    if args.diff_only:
        for plat in list(grouped.keys()):
            grouped[plat] = [
                g for g in grouped[plat] if g.status == "NEW"
            ]
        for plat in diff:
            diff[plat] = {
                "new": diff[plat]["new"],
                "missing": diff[plat]["missing"],
            }

    report = build_report(
        har_files=args.har_files,
        grouped=grouped,
        diff=diff,
        total_requests=total_requests,
        api_requests=len(all_parsed),
    )

    output = json.dumps(report, indent=2, ensure_ascii=False)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{platform_filter}_{timestamp}.json"
    output_path = SCRIPT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Report saved to {output_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
import time
import hashlib
import re
from datetime import datetime, timezone
import smtplib
import ssl
from email.mime.text import MIMEText

import requests

BASE_URL = (
    "https://services2.arcgis.com/OqejhVam51LdtxGa/arcgis/rest/services/"
    "WaterAdvisoryCR021_DeptView/FeatureServer/0/query"
)


# ------------------ Helpers for API data ------------------ #

def fetch_open_outages_by_county(county: str) -> list:
    where = f"STATUS='Open' AND APPROVALSTATUS='Approved' AND COUNTY='{county}'"

    params = {
        "f": "json",
        "where": where,
        "outFields": "*",
        "returnGeometry": "true",
        "returnIdsOnly": "false",
        "orderByFields": "STARTDATE DESC",
        "outSR": "4326",
    }

    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    return [
        f.get("properties") or f.get("attributes") or {}
        for f in features
    ]


def strip_html(html: str | None) -> str:
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</div\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<.*?>", "", text)
    return "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())


def extract_reference(description: str) -> str | None:
    # Looks for stuff like COR00098700 / MAY00102991
    match = re.search(r"\b[A-Z]{3}\d{8}\b", description)
    return match.group(0) if match else None


def format_epoch(value) -> str | None:
    """Convert ArcGIS epoch (ms or s) to human-readable string."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None

    # Heuristic: if it's huge, assume milliseconds
    if v > 1e12:
        v = v / 1000.0
    try:
        dt = datetime.fromtimestamp(v, tz=timezone.utc)
        # You can change this format if you prefer local time or different layout
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return None


def normalize_outage(props: dict) -> dict:
    raw_desc = props.get("DESCRIPTION") or ""
    plain_desc = strip_html(raw_desc)

    ref = props.get("REFERENCENUM") or extract_reference(plain_desc)

    start_human = format_epoch(props.get("STARTDATE"))
    end_human = format_epoch(props.get("ENDDATE"))

    return {
        "objectid": props.get("OBJECTID"),
        "globalid": props.get("GLOBALID"),
        "title": props.get("TITLE") or "",
        "status": props.get("STATUS") or "",
        "location": props.get("LOCATION") or "",
        "county": props.get("COUNTY") or "",
        "startdate_raw": props.get("STARTDATE"),
        "enddate_raw": props.get("ENDDATE"),
        "startdate": start_human,
        "enddate": end_human,
        "reference": ref,
        "description": plain_desc,
    }


def hash_data(data) -> str:
    payload = json.dumps(data, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ------------------ Email helpers ------------------ #

def format_outage_text(outages: list, county: str, refnum: str | None,
                       location_filter: str | None) -> str:
    if not outages:
        base = f"No matching open outages found.\nCounty: {county}\n"
        if refnum:
            base += f"Reference filter: {refnum}\n"
        if location_filter:
            base += f"Location filter: {location_filter}\n"
        return base

    lines = []
    lines.append("Water.ie outage update")
    lines.append("")
    lines.append(f"County: {county}")
    if refnum:
        lines.append(f"Reference filter: {refnum}")
    if location_filter:
        lines.append(f"Location filter: {location_filter}")
    lines.append("")

    for o in outages:
        lines.append("-" * 60)
        lines.append(f"Location : {o['location']}, {o['county']}")
        lines.append(f"Status   : {o['status']}")
        lines.append(f"Reference: {o['reference'] or '(unknown)'}")
        lines.append(f"Start    : {o['startdate']} (raw: {o['startdate_raw']})")
        lines.append(f"End      : {o['enddate']} (raw: {o['enddate_raw']})")
        if o["description"]:
            lines.append("")
            lines.append("Description:")
            lines.append(o["description"])
        lines.append("")

    return "\n".join(lines)


def email_config_valid(args) -> bool:
    """Return True if email notifications should be enabled."""
    required = [
        args.smtp_server,
        args.smtp_user,
        args.smtp_password,
        args.from_email,
        args.to_email,
    ]
    return all(required)


def send_email(args, subject: str, body: str):
    """Send an email (only if email params are valid)."""
    if not email_config_valid(args):
        return  # silently skip

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = args.from_email
    msg["To"] = args.to_email

    context = ssl.create_default_context()
    with smtplib.SMTP(args.smtp_server, args.smtp_port) as server:
        server.starttls(context=context)
        server.login(args.smtp_user, args.smtp_password)
        server.send_message(msg)


# ------------------ Printing helpers ------------------ #

def print_outages(outages: list, county: str, refnum: str | None,
                  location_filter: str | None):
    print(format_outage_text(outages, county, refnum, location_filter))


def location_matches(outage: dict, needle: str) -> bool:
    """Check if outage location/description contains the needle (case-insensitive)."""
    if not needle:
        return True
    n = needle.lower()

    combined_loc = f"{outage.get('location', '')}, {outage.get('county', '')}".lower()
    desc = outage.get("description", "").lower()

    return (n in combined_loc) or (n in desc)


# ------------------ Main loop ------------------ #

def main():
    parser = argparse.ArgumentParser(
        description="Monitor Water.ie outages (via ArcGIS) and optionally send email alerts."
    )

    parser.add_argument("--county", required=True, help="County name, e.g. 'Mayo'.")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds.")
    parser.add_argument("--refnum", default=None, help="Optional outage reference code to filter.")
    parser.add_argument(
        "--location-contains",
        default=None,
        help="Filter outages whose location/description contains this text (case-insensitive), e.g. 'Ballina'.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print outage details to stdout on initial fetch and when changes are detected.",
    )

    # Email params (all optional)
    parser.add_argument("--smtp-server")
    parser.add_argument("--smtp-port", type=int, default=587)
    parser.add_argument("--smtp-user")
    parser.add_argument("--smtp-password")
    parser.add_argument("--from-email")
    parser.add_argument("--to-email")
    parser.add_argument("--subject-prefix", default="[Water.ie]")

    args = parser.parse_args()

    print(f"[{datetime.now()}] Monitoring Water.ie outages")
    print(f"  County           : {args.county}")
    print(f"  Interval         : {args.interval}s")
    print(f"  Refnum filter    : {args.refnum or 'None (all in county)'}")
    print(f"  Location filter  : {args.location_contains or 'None'}")
    print(f"  Verbose          : {'YES' if args.verbose else 'NO'}")

    if email_config_valid(args):
        print("  Email            : ENABLED")
        print(f"    To             : {args.to_email}")
    else:
        print("  Email            : DISABLED (missing SMTP parameters)")

    last_hash = None

    while True:
        try:
            raw_list = fetch_open_outages_by_county(args.county)
            outages = [normalize_outage(o) for o in raw_list]

            # Reference filter
            if args.refnum:
                outages = [o for o in outages if o["reference"] == args.refnum]

            # Location filter
            if args.location_contains:
                outages = [
                    o for o in outages if location_matches(o, args.location_contains)
                ]

            current_hash = hash_data(outages)

            # First run
            if last_hash is None:
                print(f"[{datetime.now()}] Initial state fetched. Matching outages: {len(outages)}")
                if args.verbose:
                    print_outages(outages, args.county, args.refnum, args.location_contains)
                last_hash = current_hash

            # Subsequent runs
            elif current_hash != last_hash:
                print(f"[{datetime.now()}] CHANGE DETECTED! Matching outages: {len(outages)}")
                if args.verbose:
                    print_outages(outages, args.county, args.refnum, args.location_contains)

                body = format_outage_text(outages, args.county, args.refnum, args.location_contains)
                subject_suffix_parts = [args.county]
                if args.refnum:
                    subject_suffix_parts.append(args.refnum)
                if args.location_contains:
                    subject_suffix_parts.append(args.location_contains)
                suffix = " / ".join(subject_suffix_parts)

                subject = f"{args.subject_prefix} Change in outage data ({suffix})"
                send_email(args, subject, body)

                last_hash = current_hash
            else:
                if args.verbose:
                    print(f"[{datetime.now()}] No change. Matching outages: {len(outages)}")
                else:
                    print(f"[{datetime.now()}] No change.")

        except Exception as e:
            print(f"[{datetime.now()}] Error: {e}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()

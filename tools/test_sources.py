#!/usr/bin/env python3
"""Quick test harness to check external sources used by the enricher.

Runs Overpass, Nominatim, DuckDuckGo discovery and basic website parsing
against the first N rows of the provided merged CSV and prints a brief
JSON-like report to stdout.
"""
import argparse
import asyncio
import csv
import json
from pathlib import Path


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", nargs="?", default="../Data/merged_all_unique.csv")
    parser.add_argument("--limit", type=int, default=2)
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    # import the command helpers
    module_path = "optimalroute.infrastructure.management.commands.export_station_enrichment_csvs"
    cmd = __import__(module_path, fromlist=["*"])

    input_csv = Path(args.input_csv).expanduser().resolve()
    if not input_csv.exists():
        print(json.dumps({"error": f"input csv not found: {input_csv}"}))
        return

    rows = []
    with input_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            rows.append({
                "query": row.get("query", ""),
                "name": row.get("name", ""),
                "street": row.get("street", ""),
                "city": row.get("city", ""),
                "state": row.get("state", ""),
                "state_code": row.get("state_code", ""),
                "latitude": row.get("latitude", ""),
                "longitude": row.get("longitude", ""),
                "h3": row.get("h3", ""),
            })
            if idx + 1 >= args.limit:
                break

    async with cmd.aiohttp.ClientSession(connector=cmd.aiohttp.TCPConnector(limit=8, ssl=False), headers={"User-Agent": "PlanTripFuelEnricherTest/1.0"}) as session:
        reports = []
        for idx, row in enumerate(rows, start=1):
            report = {"row": idx, "name": row.get("name")}

            try:
                overpass = await cmd.overpass_lookup(session, float(row["latitude"]), float(row["longitude"]), row.get("name", ""), 250)
                report["overpass_count"] = len(overpass or [])
            except Exception as exc:
                report["overpass_error"] = str(exc)

            try:
                nomi = await cmd.nominatim_lookup(session, row, country_code="et", country_name="Ethiopia")
                report["nominatim_count"] = len(nomi or [])
            except Exception as exc:
                report["nominatim_error"] = str(exc)

            try:
                urls = await cmd.discover_website_urls(session, row, limit=3, country_name="Ethiopia", country_code="et")
                report["discovered_urls_count"] = len(urls or [])
                report["discovered_urls"] = urls[:3]
            except Exception as exc:
                report["discover_error"] = str(exc)

            # try fetching first discovered url and parse JSON-LD
            website_text = ""
            website_json_ld = {}
            if report.get("discovered_urls_count", 0) > 0:
                first = report["discovered_urls"][0]
                try:
                    website_text = await cmd.fetch_text(session, first)
                    website_json_ld = cmd.extract_json_ld_business_data(website_text)
                    report["website_text_snippet_len"] = len(website_text[:1000])
                    report["website_json_ld_keys"] = list(website_json_ld.keys())
                except Exception as exc:
                    report["website_fetch_error"] = str(exc)

            # capabilities
            report["pdf_text_extraction_available"] = cmd.PdfReader is not None
            report["docx_extraction_available"] = cmd.DocxDocument is not None
            report["image_ocr_available"] = (cmd.Image is not None and cmd.pytesseract is not None)

            # contact/fuel parsing quick checks
            try:
                tags = {}
                # emulate tags from nominatim if present
                if nomi:
                    tags = cmd.build_nominatim_tags(nomi[0])
                emails = cmd.extract_contact_emails(tags, website_text=website_text, website_data=website_json_ld)
                phones = cmd.extract_contact_phones(tags, website_text=website_text, website_data=website_json_ld)
                fuels = cmd.extract_fuel_offers(tags, website_json_ld)
                payments = cmd.extract_payment_methods(tags, website_text=website_text)
                report.update({"emails_found": emails, "phones_found": phones, "fuel_offers_found": len(fuels), "payment_methods_found": payments})
            except Exception as exc:
                report["parsing_error"] = str(exc)

            reports.append(report)

        print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

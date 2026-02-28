#!/usr/bin/env python3
"""
Usage: python scripts/scrape.py [--max-professors N] [--workers N]

Runs the professor scraping pipeline:
  1. Fetch CSRankings CSV and build professor list (parse_scraped_data)
  2. Scrape each professor homepage in parallel (professor_router)
  3. Save results to logs/scraped_professors.json
"""

import argparse
import json
import os
import sys

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.professor_router import (
    get_professors_from_ranking,
    scrape_professors_parallel,
    MAX_WORKERS,
)

OUTPUT_FILE = os.path.join(os.getcwd(), "logs", "scraped_professors.json")


def main():
    parser = argparse.ArgumentParser(description="Scrape professor homepages from CSRankings")
    parser.add_argument("--max-professors", type=int, default=None, metavar="N",
                        help="Limit scraping to the first N professors (default: all)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, metavar="N",
                        help=f"Number of parallel workers (default: {MAX_WORKERS})")
    parser.add_argument("--output", default=OUTPUT_FILE, metavar="PATH",
                        help=f"Output JSON file (default: {OUTPUT_FILE})")
    args = parser.parse_args()

    print("Step 1/3 — Fetching CSRankings data...")
    professors = get_professors_from_ranking()
    if not professors:
        print("ERROR: Could not load professor data. Check your network connection.")
        sys.exit(1)
    print(f"  Found {len(professors)} professors with homepages")

    limit = args.max_professors
    if limit:
        print(f"\nStep 2/3 — Scraping up to {limit} professor homepages ({args.workers} workers)...")
    else:
        print(f"\nStep 2/3 — Scraping {len(professors)} professor homepages ({args.workers} workers)...")

    results, stats = scrape_professors_parallel(professors, max_professors=limit, max_workers=args.workers)

    print(f"\nStep 3/3 — Saving results to {args.output}...")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone.")
    print(f"  Scraped:    {stats['total_professors']} professors")
    print(f"  Cache hits: {stats['cached_count']} ({stats['cache_hit_rate']:.0%})")
    print(f"  Elapsed:    {stats['elapsed_seconds']:.1f}s")
    print(f"  Output:     {args.output}")


if __name__ == "__main__":
    main()

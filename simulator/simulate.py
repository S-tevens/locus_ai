"""Streams rows from traffic_emergency_cyber_dataset.csv to the backend's
POST /ingest endpoint, one at a time, so the FastAPI -> WebSocket -> dashboard
pipeline has live traffic to show.

Usage:
    python simulate.py
    python simulate.py --interval 0.1 --shuffle
    python simulate.py --loop --limit 200
"""

import argparse
import csv
import random
import sys
import time
from pathlib import Path

import requests

INT_COLS = {
    "src_port", "dst_port", "packet_size", "bytes_transferred",
    "unique_dst_ips_contacted", "syn_flag_count", "rst_flag_count",
    "failed_login_attempts", "is_encrypted", "mac_ip_mismatch",
    "signal_preemption_request", "hour_of_day",
}
FLOAT_COLS = {
    "packets_per_second", "connection_duration", "avg_request_interval",
    "gps_deviation_km",
}

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "traffic_emergency_cyber_dataset.csv"


def load_rows(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for col in INT_COLS:
            row[col] = int(row[col])
        for col in FLOAT_COLS:
            row[col] = float(row[col])
    return rows


def to_payload(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "label"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to the dataset CSV")
    parser.add_argument("--url", default="http://127.0.0.1:8000/ingest", help="Backend /ingest URL")
    parser.add_argument("--interval", type=float, default=0.3, help="Seconds to sleep between rows")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle row order instead of streaming in file order")
    parser.add_argument("--loop", action="store_true", help="Loop back to the start when the dataset is exhausted")
    parser.add_argument("--limit", type=int, default=None, help="Stop after N rows")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for --shuffle")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"error: dataset not found at {args.csv}", file=sys.stderr)
        sys.exit(1)

    rows = load_rows(args.csv)
    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(rows)

    print(f"[simulator] loaded {len(rows)} rows from {args.csv.name}")
    print(f"[simulator] streaming to {args.url} every {args.interval}s "
          f"(shuffle={args.shuffle}, loop={args.loop}, limit={args.limit})")
    print("[simulator] press Ctrl+C to stop\n")

    sent = 0
    matches = 0
    mismatches = 0
    label_counts: dict[str, int] = {}

    try:
        while True:
            for row in rows:
                if args.limit is not None and sent >= args.limit:
                    raise StopIteration

                actual_label = row["label"]
                payload = to_payload(row)

                try:
                    resp = requests.post(args.url, json=payload, timeout=5)
                    resp.raise_for_status()
                except requests.exceptions.ConnectionError:
                    print(f"[simulator] could not reach {args.url} — "
                          f"is the backend running? (uvicorn main:app --port 8000)", file=sys.stderr)
                    sys.exit(1)
                except requests.exceptions.RequestException as exc:
                    print(f"[simulator] request failed: {exc}", file=sys.stderr)
                    time.sleep(args.interval)
                    continue

                result = resp.json()
                predicted_label = result["label"]
                sent += 1
                label_counts[predicted_label] = label_counts.get(predicted_label, 0) + 1
                if predicted_label == actual_label:
                    matches += 1
                    marker = "match   "
                else:
                    mismatches += 1
                    marker = "MISMATCH"

                print(
                    f"[{sent:5d}] {marker}  actual={actual_label:18s} "
                    f"predicted={predicted_label:18s} risk={result['risk_score']:.3f} "
                    f"({result['risk_level']:6s}) mode={result['inference_mode']:9s} "
                    f"{result['device_type']}/{result['zone_id']}"
                )

                time.sleep(args.interval)

            if not args.loop:
                break
    except (KeyboardInterrupt, StopIteration):
        pass

    print(f"\n[simulator] stopped after {sent} rows sent "
          f"({matches} matched CSV label, {mismatches} mismatched)")
    if label_counts:
        print("[simulator] predicted label breakdown:", label_counts)


if __name__ == "__main__":
    main()

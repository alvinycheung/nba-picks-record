#!/usr/bin/env python3
"""Verify one record or the whole chain. Needs openssl (with ts) and the ots client on PATH."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CA = {"digicert": HERE / "ca/digicert_roots.pem", "freetsa": HERE / "ca/freetsa_ca.pem"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def check(path, prev_sha):
    rec = json.loads(path.read_text())
    ok = True
    digest = sha256(path)
    if prev_sha is not None and rec["prev_sha256"] != prev_sha:
        print(f"  chain: FAIL prev_sha256 {rec['prev_sha256']} != {prev_sha}"); ok = False
    else:
        print(f"  chain: ok sha256 {digest[:16]} prev {str(rec['prev_sha256'])[:16]}")
    tsr = Path(str(path) + ".tsr")
    if tsr.exists():
        text = run("openssl", "ts", "-reply", "-in", str(tsr), "-text").stdout
        when = re.search(r"Time stamp: (.*)", text)
        verified = any(run("openssl", "ts", "-verify", "-data", str(path), "-in", str(tsr), "-CAfile", str(ca)).returncode == 0
                       for ca in CA.values())
        print(f"  rfc3161: {'ok' if verified else 'FAIL'} {when.group(1) if when else ''}")
        ok &= verified
    else:
        print("  rfc3161: missing"); ok = False
    ots = Path(str(path) + ".ots")
    if ots.exists():
        info = run(shutil.which("ots") or "ots", "info", str(ots)).stdout
        heights = re.findall(r"BitcoinBlockHeaderAttestation\((\d+)\)", info)
        print(f"  ots: {'Bitcoin block ' + min(heights, key=int) if heights else 'pending (calendar receipts only)'}")
    else:
        print("  ots: missing"); ok = False
    late = [g["game_id"] for g in rec["games"] if g["pick"] and g["tip_utc"] and g["pick"]["created_at"] > g["tip_utc"]]
    print(f"  picks before tip: {'ok' if not late else 'FAIL ' + ' '.join(late)}")
    ok &= not late
    bets = [g for g in rec["games"] if g["decision"] == "BET"]
    print(f"  {rec['record_ts']}: {len(rec['games'])} games, {len(bets)} bets" +
          "".join(f"\n    {g['away']}@{g['home']} {g['pick']['market']} {g['pick']['side']} {g['pick']['line']} {g['pick']['price_american']:+d} @ {g['pick']['book']}" for g in bets))
    return ok, digest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record", nargs="?")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all:
        paths = sorted(HERE.glob("records/*/*/*/*.json"))
    elif args.record:
        paths = [Path(args.record)]
    else:
        ap.error("give a record path or --all")
    prev, ok = None, True
    for p in paths:
        print(p.relative_to(HERE) if p.is_absolute() else p)
        good, prev = check(p, prev if args.all else None)
        ok &= good
    print("ALL OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

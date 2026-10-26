#!/usr/bin/env python3
"""family_matrix.py — price a family round trip across many airport pairs x date pairs.

Built for: Temple TX -> Appleton WI, Jan 2027, 3 adults + 2 kids (8, 10), 4-6 night stay,
home by Jan 18. Generic enough to re-aim at any trip (edit TRIP below or pass flags).

Why 1 adult and x5: Google's search page inlines ZERO rows for multi-passenger
parties (measured 2026-10-26: AUS-MKE 1 adult = 17 rows, 5 adults = 0, 3A+2C = 0).
US domestic kids pay adult fares, so price per head x party size, then confirm the
finalists for N seats on google.com/travel/flights (fare-bucket depth can differ).

Usage:
  python braatz/family_matrix.py pairs   [--out pairs.json]     # 25 pairs x 2 reference windows
  python braatz/family_matrix.py sweep --pairs AUS-MKE,DFW-ORD  # every valid date combo for those pairs
  python braatz/family_matrix.py any                            # all-airports search per date combo
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from fli.models import (Airport, FlightSearchFilters, FlightSegment, PassengerInfo,
                        SortBy, TripType)
from fli.search import SearchFlights

TRIP = dict(
    origins=["GRK", "AUS", "SAT", "DFW", "DAL"],
    dests=["ATW", "GRB", "MKE", "ORD", "MDW"],
    first_depart=date(2027, 1, 1),
    last_return=date(2027, 1, 18),   # daughter back in TX before classes on the 19th
    nights=(4, 5, 6),
    ref_windows=[(date(2027, 1, 6), date(2027, 1, 11)), (date(2027, 1, 12), date(2027, 1, 17))],
)
OUT_DIR = Path(__file__).resolve().parent / "out"


def date_combos():
    d = TRIP["first_depart"]
    while True:
        any_ok = False
        for n in TRIP["nights"]:
            r = d + timedelta(days=n)
            if r <= TRIP["last_return"]:
                any_ok = True
                yield d, r
        if not any_ok:
            return
        d += timedelta(days=1)


def ap(codes):
    return [[getattr(Airport, c), 0] for c in codes]


def search(origins, dests, dout, dret, top_n=6, tries=3):
    segs = [
        FlightSegment(departure_airport=ap(origins), arrival_airport=ap(dests), travel_date=dout.isoformat()),
        FlightSegment(departure_airport=ap(dests), arrival_airport=ap(origins), travel_date=dret.isoformat()),
    ]
    f = FlightSearchFilters(trip_type=TripType.ROUND_TRIP, passenger_info=PassengerInfo(adults=1),
                            flight_segments=segs, sort_by=SortBy.CHEAPEST)
    for i in range(tries):
        try:
            return SearchFlights().search(f, top_n=top_n) or []
        except Exception as e:  # noqa: BLE001 — network/parse hiccups; retry then record
            err = repr(e)[:200]
            time.sleep(2 + 3 * i)
    return [{"error": err}]


def legs_str(fr):
    return " / ".join(f"{l.airline.name}{l.flight_number} {l.departure_airport.name}>{l.arrival_airport.name}"
                      for l in fr.legs)


def rows_from(res, dout, dret):
    out = []
    for item in res:
        if isinstance(item, dict):
            out.append({"error": item["error"], "out": dout.isoformat(), "ret": dret.isoformat()})
            continue
        o, r = item[0], item[-1]
        out.append(dict(
            out=dout.isoformat(), ret=dret.isoformat(), nights=(dret - dout).days,
            origin=o.legs[0].departure_airport.name, dest=o.legs[-1].arrival_airport.name,
            ret_from=r.legs[0].departure_airport.name, ret_to=r.legs[-1].arrival_airport.name,
            pp_price=r.price if r.price is not None else o.price,
            airlines=sorted({l.airline.name for l in o.legs + r.legs}),
            out_dep=o.legs[0].departure_datetime.strftime("%H:%M"), out_arr=o.legs[-1].arrival_datetime.strftime("%H:%M"),
            out_stops=len(o.legs) - 1, out_min=o.duration,
            ret_dep=r.legs[0].departure_datetime.strftime("%H:%M"), ret_arr=r.legs[-1].arrival_datetime.strftime("%H:%M"),
            ret_stops=len(r.legs) - 1, ret_min=r.duration,
            out_legs=legs_str(o), ret_legs=legs_str(r),
        ))
    return out


def dump(rows, name):
    OUT_DIR.mkdir(exist_ok=True)
    p = OUT_DIR / name
    p.write_text(json.dumps(rows, indent=1))
    ok = [x for x in rows if "error" not in x]
    print(f"wrote {p} rows={len(rows)} ok={len(ok)} errors={len(rows) - len(ok)}", flush=True)


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("phase", choices=["pairs", "sweep", "any"])
    ap_.add_argument("--pairs", default="")
    ap_.add_argument("--out", default="")
    ap_.add_argument("--sleep", type=float, default=1.0)
    a = ap_.parse_args()
    rows = []
    if a.phase == "pairs":
        jobs = [([o], [d], w) for o in TRIP["origins"] for d in TRIP["dests"] for w in TRIP["ref_windows"]]
    elif a.phase == "sweep":
        pairs = [p.split("-") for p in a.pairs.split(",") if p]
        jobs = [([o], [d], w) for o, d in pairs for w in date_combos()]
    else:
        jobs = [(TRIP["origins"], TRIP["dests"], w) for w in date_combos()]
    t0 = time.time()
    for i, (o, d, (dout, dret)) in enumerate(jobs, 1):
        res = search(o, d, dout, dret)
        got = rows_from(res, dout, dret)
        rows.extend(got)
        best = min((x["pp_price"] for x in got if x.get("pp_price")), default=None)
        print(f"[{i}/{len(jobs)} {time.time()-t0:5.0f}s] {','.join(o)}->{','.join(d)} {dout}..{dret} "
              f"rows={len(got)} best_pp={best}", flush=True)
        time.sleep(a.sleep)
    dump(rows, a.out or f"{a.phase}.json")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""rank.py — turn family_matrix.py output into a door-to-door, all-in ranking.

Jason's objective (2026-10-26): price first, time-in-transit second, departure time third
(late morning / early afternoon preferred). Ranking = cost banded to $BAND, then hours,
then departure fit — so a $12 saving never beats a 5-hour-shorter day.

Every number below is an assumption with its source; edit and re-run. Nothing is fetched.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

PARTY = 5
CHECKED_BAGS_EACH_WAY = 3            # winter trip, 5 people; personal items/carry-ons on top
# First-checked-bag fee, each way, prepaid where offered. PIRG table updated 2026-05-05.
BAG_FEE = {"AA": 45, "UA": 45, "DL": 45, "WN": 35, "AS": 45, "F9": 69, "G4": 45, "SY": 45}
BAG_FEE_DEFAULT = 50
# Frontier sells seats; to keep an 8- and 10-year-old next to an adult, budget seat picks.
SEAT_FEE_PP_EACH_WAY = {"F9": 20}    # ESTIMATE — check at checkout
MILE_COST = 0.30                    # gas + wear per mile, marginal (not the IRS rate)

# Temple TX -> airport: one-way miles, drive minutes, parking $/day.
TX = {
    "GRK": (22, 30, 8),     # parking ESTIMATE
    "AUS": (70, 70, 14),    # economy lot $14/day since 2026-05-12 (flyaustin.com)
    "SAT": (135, 125, 12),  # parking ESTIMATE
    "DFW": (150, 150, 14),  # remote/express parking ESTIMATE
    "DAL": (140, 140, 15),  # parking ESTIMATE
}
# airport -> Appleton: one-way miles, drive minutes (winter-ish, no snow padding).
WI = {"ATW": (8, 15), "GRB": (32, 35), "MKE": (110, 115), "ORD": (190, 210), "MDW": (200, 225)}
PICKUP_ROUND_TRIPS = 2               # in-laws drive out + back for arrival AND departure
AIRPORT_BUFFER_MIN = 90              # arrive at the TX airport this early with kids + bags
DEPLANE_MIN = 30
BAND = 100                           # $ — costs within the same $100 band count as a tie
PREF_DEP = (10 * 60, 14 * 60 + 30)   # 10:00–14:30 outbound departure is the sweet spot


def mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def score(r: dict) -> dict:
    o, d = r["origin"], r["dest"]
    tx_mi, tx_min, park = TX[o]
    wi_mi, wi_min = WI[d]
    fare = r["pp_price"] * PARTY
    bag = max(BAG_FEE.get(a, BAG_FEE_DEFAULT) for a in r["airlines"]) * CHECKED_BAGS_EACH_WAY * 2
    seats = max(SEAT_FEE_PP_EACH_WAY.get(a, 0) for a in r["airlines"]) * PARTY * 2
    parking = park * (r["nights"] + 1)
    tx_drive = 2 * tx_mi * MILE_COST
    wi_drive = PICKUP_ROUND_TRIPS * 2 * wi_mi * MILE_COST
    total = fare + bag + seats + parking + tx_drive + wi_drive
    d2d_out = tx_min + AIRPORT_BUFFER_MIN + r["out_min"] + DEPLANE_MIN + wi_min
    d2d_ret = wi_min + AIRPORT_BUFFER_MIN + r["ret_min"] + DEPLANE_MIN + tx_min
    leave_home = mins(r["out_dep"]) - AIRPORT_BUFFER_MIN - tx_min
    home_arr = mins(r["ret_arr"]) + DEPLANE_MIN + tx_min
    dep = mins(r["out_dep"])
    fit = 0 if PREF_DEP[0] <= dep <= PREF_DEP[1] else min(abs(dep - PREF_DEP[0]), abs(dep - PREF_DEP[1]))
    return dict(r, total=round(total), fare=round(fare), bags=bag, seats=seats, parking=parking,
                drive_cost=round(tx_drive + wi_drive), d2d_out_h=round(d2d_out / 60, 1),
                d2d_ret_h=round(d2d_ret / 60, 1), d2d_h=round((d2d_out + d2d_ret) / 60, 1),
                leave_home=f"{leave_home // 60 % 24:02d}:{leave_home % 60:02d}" + (" (prev day)" if leave_home < 0 else ""),
                home_by=f"{home_arr // 60 % 24:02d}:{home_arr % 60:02d}" + (" (+1)" if home_arr >= 1440 else ""),
                dep_fit_min=fit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    rows = [r for f in a.files for r in json.loads(Path(f).read_text()) if "error" not in r and r.get("pp_price")]
    # same airport both directions only — a split pair strands the car
    rows = [r for r in rows if r["origin"] == r["ret_to"] and r["dest"] == r["ret_from"]]
    scored = [score(r) for r in rows]
    # best itinerary per (pair, dates) by the same lexicographic key
    key = lambda s: (s["total"] // BAND, s["d2d_h"], s["dep_fit_min"], s["total"])
    best = {}
    for s in scored:
        k = (s["origin"], s["dest"], s["out"], s["ret"])
        if k not in best or key(s) < key(best[k]):
            best[k] = s
    ranked = sorted(best.values(), key=key)
    if a.json:
        Path(a.json).write_text(json.dumps(ranked, indent=1))
    hdr = f"{'#':>2} {'total':>6} {'fare/pp':>7} {'pair':8} {'dates':13} {'n':>1} {'air':6} {'leave':>11} {'out':>11} {'st':>2} {'back':>11} {'st':>2} {'home':>8} {'d2d h':>6}"
    print(hdr)
    for i, s in enumerate(ranked[: a.top], 1):
        print(f"{i:2} {s['total']:6} {s['pp_price']:7.0f} {s['origin']}-{s['dest']} {s['out'][5:]}..{s['ret'][5:]} {s['nights']} "
              f"{','.join(s['airlines']):6} {s['leave_home']:>11} {s['out_dep']}-{s['out_arr']} {s['out_stops']:2} "
              f"{s['ret_dep']}-{s['ret_arr']} {s['ret_stops']:2} {s['home_by']:>8} {s['d2d_h']:6}")
    return ranked


if __name__ == "__main__":
    main()

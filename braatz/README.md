# braatz/ — family-trip fare matrix (Jason's fork of punitarani/fli)

Built 2026-10-26 for: Temple TX -> Appleton WI, Jan 2027, 3 adults + kids 8 & 10,
4–6 nights, home by Jan 18. Re-aim by editing `TRIP` in `family_matrix.py`.

```
.venv/bin/python braatz/family_matrix.py pairs                 # every origin x dest, 2 reference windows
.venv/bin/python braatz/family_matrix.py sweep --pairs DFW-ORD,DAL-MKE   # every valid date combo
.venv/bin/python braatz/rank.py braatz/out/sweep.json braatz/out/pairs.json --top 25
```

## LUT (hard-won, 2026-10-26)
- **Price at adults=1, multiply by party size.** Google's search page inlines ZERO rows for
  adults=5 and for 3A+2C (fli's `sparse_passenger_mix`); adults=1 returns 17–59 rows. US domestic
  kids pay adult fares. Verified: 1-seat x5 matched the live 5-seat price on 3/3 finalists.
- Multi-airport segments work (`departure_airport=[[A,0],[B,0]]`) but one cheap pair floods the
  result set (38/40 rows DFW-ORD) — sweep per pair when ground cost differs per airport.
- `devWhyqueue/fli` (0 stars) is a fork; upstream is `punitarani/fli`.
- ~2 s/search, 390 searches in ~13 min with 0.8 s sleep, zero blocks.
- Spirit is out of business (PIRG, 2026-05); Frontier is the remaining ULCC on these routes.

## Result snapshot (fares fetched 2026-10-26; all-in = fare x5 + 3 bags each way + parking + mileage)
| all-in | route | dates | fare (5 pax, live-verified) |
|---|---|---|---|
| $1,682 | Frontier DFW–ORD nonstop 2:15p / 5:55p | Jan 12–16 | $680 |
| $1,986 | Southwest DAL–MKE nonstop 2:55p / 1:00p | Jan 11–15 | $1,484 |
| $2,137 | AUS–ATW 1-stop (DL/UA/AA all same fare) | Jan 12–16 | $1,742 |

Assumptions live at the top of `rank.py` with sources; parking for GRK/SAT/DFW/DAL is estimated.

## The shelf — Google Flights scrapers forked for future trips (2026-10-26)
None of these is an official API (Amadeus Self-Service died 2026-07-17). They all speak Google's own
web endpoints, so they break when Google changes them: when one breaks, try the next.

| fork | upstream | lang | use it for |
|---|---|---|---|
| **jasoncbraatz/fli** (this repo) | punitarani/fli (~3.4k stars) | Python | **Default.** Multi-airport segments, round trips, date search, MCP server, CLI. `braatz/` lives here. |
| jasoncbraatz/fast-flights | AWeirdDev/flights (~2.1k) | Python | The original protobuf `tfs=` trick. Fallback if fli breaks. |
| jasoncbraatz/google-flights-rs | nas-/google-flights-rs | Rust (+ Python bindings via PyPI `gflights`) | Full depart × return **date grid** and price graph in one call. License is "other": read it before shipping anything. |
| jasoncbraatz/fast-flights-ts | decocms/fast-flights-ts | TypeScript | Node/n8n Code nodes: calls Google's RPC directly, no HTML scraping. |
| jasoncbraatz/swoop-flights | saraswatayu/swoop | Python | The RPC approach fast-flights-ts was modeled on: second fallback. |

Before reusing: `git fetch upstream` on the fork first (these move monthly), then re-run the
adults=1 calibration from the LUT above — the multi-passenger zero-rows quirk may change.

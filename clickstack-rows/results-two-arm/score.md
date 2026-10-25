# Two-arm run score, from results-two-arm

Arm A: the rows run, table `default.otel_logs`. Arm B: the collector rule (opentelemetry-collector, cart INFO and DEBUG to its bucket), table `default.otel_logs_rule`.
R = 30099 rows an hour, so R/6 of a window = 5016 rows (window 600 s, ten rig minutes at 60 s a minute, from T0 = 1792893153). P = 43000.
Source: two-arm-windows.json, read from ClickHouse at collect. The pre-step level is window 5 (minutes 50 to 60) for both arms; window 4 (40 to 50) holds the first applied run's pickup and is shown, not used.
Phase marks, rig minutes after T0: phase_held 40.0, phase_growth 60.1, phase_hold_5x 120.1, phase_drain 160.1.

## 1. Arm A's rows per window at or under 1.10 R/6 = 5518, from the first growth step to the end of the hold: FAIL
w6 1.09, w7 0.92, w8 1.09, w9 0.91, w10 1.13, w11 0.95, w12 1.07, w13 0.91, w14 1.09, w15 1.01 (of R/6).

The 4-minute test of the rows run, reported: 24 windows, 2 over R/15 plus F/15, the largest at 1.15 of its bound.

## 2. Arm B's rows per window above 1.5x its pre-step level (2686 rows) in every window of the hold: PASS
w12 2.96, w13 2.95, w14 3.42, w15 3.03 (of the pre-step level).

## 3. Insert plus merge CPU: FAIL (arm A does not hold; arm B does not rise)
Arm A, every window from the first growth step to the end of the hold at or under 1.10 of its pre-step 17.13 s: w6 0.93, w7 1.07, w8 1.09, w9 1.24, w10 0.96, w11 0.92, w12 1.22, w13 0.87, w14 1.10, w15 0.88.
Arm B, every window of the hold above 1.5x its pre-step 122.50 s: w12 1.61, w13 0.53, w14 1.47, w15 0.40.
Arm B's half is scored on the hold, as criterion 2 is; every window is in the table below.

**No differentiator** on CPU: arm B's write CPU did not rise above 1.5x in every window of the hold.

Noise: these are ClickHouse's own user plus system time for the inserts into each table (system.query_log, Insert and AsyncInsertFlush, by `tables`) and the merges of each table (system.part_log MergeParts), on one container on one host, both arms sharing its three CPUs. Merge CPU depends on which parts the scheduler merged inside a window. The node column is the whole server (system.metric_log), both arms and everything else, and is noisier still.

## Comparison, per window of ten rig minutes
| w | minutes | phase | lines/s | A rows | A of R/6 | B rows | B of pre-step | A insert s | A merge s | A CPU of pre-step | B insert s | B merge s | B CPU of pre-step | A inserts | B inserts | node s (noisy) | A bucket rows | B bucket rows |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0-10 | baseline | 14 | 6939 | 1.38 | 4257 | 1.58 | 39.64 | 15.09 | 3.20 | 48.40 | 17.54 | 0.54 | 216 | 792 | 245.2 |  | 2883 |
| 1 | 10-20 | baseline | 14 | 7405 | 1.48 | 2256 | 0.84 | 20.33 | 19.05 | 2.30 | 32.03 | 21.40 | 0.44 | 250 | 854 | 170.4 |  | 6143 |
| 2 | 20-30 | baseline | 14 | 7102 | 1.42 | 2647 | 0.99 | 10.85 | 7.88 | 1.09 | 18.61 | 27.61 | 0.38 | 240 | 1032 | 113.8 |  | 5751 |
| 3 | 30-40 | dry run | 14 | 7143 | 1.42 | 2653 | 0.99 | 11.74 | 4.44 | 0.94 | 20.07 | 91.09 | 0.91 | 240 | 1048 | 197.2 |  | 5758 |
| 4 | 40-50 | held | 14 | 5131 | 1.02 | 2712 | 1.01 | 12.53 | 6.83 | 1.13 | 22.40 | 121.81 | 1.18 | 240 | 1032 | 250.4 | 1959 | 5708 |
| 5 | 50-60 | held | 14 | 4697 | 0.94 | 2686 | 1.00 | 11.82 | 5.31 | 1.00 | 18.62 | 103.88 | 1.00 | 240 | 1018 | 223.5 | 2365 | 5713 |
| 6 | 60-70 | growth | 19 | 5492 | 1.09 | 3572 | 1.33 | 10.98 | 4.92 | 0.93 | 20.23 | 9.03 | 0.24 | 240 | 1120 | 259.8 | 3932 | 7813 |
| 7 | 70-80 | growth | 19 | 4627 | 0.92 | 3631 | 1.35 | 11.66 | 6.69 | 1.07 | 20.90 | 11.75 | 0.27 | 240 | 1118 | 319.4 | 4798 | 7775 |
| 8 | 80-90 | growth, inject | 24 | 5471 | 1.09 | 5858 | 2.18 | 12.38 | 6.23 | 1.09 | 34.65 | 28.23 | 0.51 | 240 | 1798 | 381.7 | 7729 | 9740 |
| 9 | 90-100 | growth, inject | 24 | 4543 | 0.91 | 5761 | 2.14 | 16.50 | 4.71 | 1.24 | 45.60 | 98.60 | 1.18 | 238 | 1762 | 453.3 | 8479 | 9803 |
| 10 | 100-110 | growth, storm | 30 | 5671 | 1.13 | 12877 | 4.79 | 11.98 | 4.52 | 0.96 | 40.84 | 144.05 | 1.51 | 240 | 2098 | 265.4 | 16152 | 12232 |
| 11 | 110-120 | growth, storm | 30 | 4788 | 0.95 | 12854 | 4.79 | 11.65 | 4.05 | 0.92 | 39.85 | 65.05 | 0.86 | 240 | 2078 | 170.9 | 17297 | 12352 |
| 12 | 120-130 | hold | 35 | 5377 | 1.07 | 7963 | 2.96 | 13.44 | 7.43 | 1.22 | 38.42 | 159.30 | 1.61 | 240 | 1820 | 285.2 | 13096 | 14273 |
| 13 | 130-140 | hold | 35 | 4581 | 0.91 | 7932 | 2.95 | 11.08 | 3.77 | 0.87 | 32.93 | 31.74 | 0.53 | 240 | 1828 | 148.4 | 14011 | 14275 |
| 14 | 140-150 | hold | 35 | 5443 | 1.09 | 9179 | 3.42 | 12.15 | 6.71 | 1.10 | 38.00 | 141.89 | 1.47 | 230 | 1824 | 276.7 | 12996 | 13004 |
| 15 | 150-160 | hold | 35 | 5052 | 1.01 | 8142 | 3.03 | 10.90 | 4.25 | 0.88 | 30.69 | 17.86 | 0.40 | 236 | 1728 | 121.1 | 13004 | 14051 |
| 16 | 160-170 | drain | 0 | 9 | 0.00 | 58 | 0.02 | 0.28 | 0.06 | 0.02 | 0.16 | 0.20 | 0.00 | 4 | 10 | 39.8 | 57 | 53 |
| 17 | 170-180 | drain | 0 |  |  |  |  |  |  |  |  |  |  |  |  | 45.7 |  |  |

## Totals for the run
| | arm A (`otel_logs`) | arm B (`otel_logs_rule`) |
|---|---:|---:|
| rows written (part_log NewPart) | 89471 | 95038 |
| rows in the table at collect | 89471 | 95038 |
| rows in the bucket | 115875 | 147327 |
| inserts (of which async flushes) | 3814 (1907) | 22960 (11480) |
| failed inserts | 20 | 18 |
| insert CPU, s | 229.9 | 502.4 |
| merge CPU, s | 112.0 | 1091.0 |
| merges | 376 | 5125 |
| counts table merge CPU, s | 18.1 | 23.4 |

Arm B delivery: 242324 lines written to the feed, 242365 rows in its table plus its bucket (+41). Arm A's delivery is final.py's criterion 5.
Inserts and async flushes into neither logs table over the run: 2689 (36.4 s CPU), not attributed to either arm.

## Projection inputs, reported, not scored
Saving = W x R, W the buyer's write share of CPU from its own query_log and R the rows cut share: the rows sent to the bucket as a share of the table's rows plus the bucket's, the bucket's by record time. No dollar figure is computed.

| w | minutes | A rows cut share | B rows cut share | A insert plus merge CPU s | B insert plus merge CPU s |
|---:|---|---:|---:|---:|---:|
| 0 | 0-10 | 0.00 | 0.40 | 54.74 | 65.93 |
| 1 | 10-20 | 0.00 | 0.73 | 39.38 | 53.44 |
| 2 | 20-30 | 0.00 | 0.68 | 18.73 | 46.23 |
| 3 | 30-40 | 0.00 | 0.68 | 16.18 | 111.16 |
| 4 | 40-50 | 0.28 | 0.68 | 19.36 | 144.21 |
| 5 | 50-60 | 0.33 | 0.68 | 17.13 | 122.50 |
| 6 | 60-70 | 0.42 | 0.69 | 15.90 | 29.26 |
| 7 | 70-80 | 0.51 | 0.68 | 18.35 | 32.65 |
| 8 | 80-90 | 0.59 | 0.62 | 18.61 | 62.88 |
| 9 | 90-100 | 0.65 | 0.63 | 21.21 | 144.20 |
| 10 | 100-110 | 0.74 | 0.49 | 16.50 | 184.90 |
| 11 | 110-120 | 0.78 | 0.49 | 15.69 | 104.90 |
| 12 | 120-130 | 0.71 | 0.64 | 20.87 | 197.73 |
| 13 | 130-140 | 0.75 | 0.64 | 14.85 | 64.67 |
| 14 | 140-150 | 0.70 | 0.59 | 18.86 | 179.89 |
| 15 | 150-160 | 0.72 | 0.63 | 15.15 | 48.55 |
| 16 | 160-170 | 0.86 | 0.48 | 0.34 | 0.36 |
| 17 | 170-180 |  |  |  |  |
| run | 0-180 | 0.56 | 0.61 | 341.85 | 1593.47 |
| hold | 120-160 | 0.72 | 0.63 | 69.73 | 490.83 |

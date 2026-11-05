# Autoscaler rules, quoted

Read 2026-11-02 from the ClickHouse Cloud docs page "Scaling recommendations"
(clickhouse.com/docs, the vertical autoscaling section) and the blog post
"Smarter Auto-Scaling for ClickHouse: The Two-Window Approach" (Ashwath Singh and
Manas Alekar, 2026-03-24, clickhouse.com/blog/smarter-auto-scaling).

## Band (docs)

> | Target utilization | 53% | The utilization level ClickHouse aims to maintain |
> | High watermark | 75% | Triggers scale-up when CPU exceeds this threshold |
> | Low watermark | 37.5% | Triggers scale-down when CPU falls below this threshold |

> If the CPU utilization is between 37.5%–75% of allocated capacity, no scaling
> action is taken. Outside that band, the recommender computes the exact size
> needed to land back at 53% utilization, and the service is scaled accordingly.

## Windows (docs and blog, same wording)

> **Small Window (3 hours)**: Captures recent usage patterns, enables faster scale-down
> **Large Window (30 hours)**: Ensures we scale up in a single step to the maximum
> usage seen in the longer lookback window, rather than multiple gradual
> scale-ups.

> Each window's recommendation is then compared to the current allocation to
> determine the scaling direction: scale-up if it recommends more, scale-down if
> it recommends less, or no change.

## Merge table (blog)

| Large window | Small window | Picked | Reasoning |
|---|---|---|---|
| Scale-up | Scale-up | Large window | Single-step scale to longer-term peak |
| Scale-up | No change | Small window | Recent usage is stable, don't scale yet |
| Scale-up | Scale-down | Hunting check | If small window trending up, use large to avoid hunting; else use small |
| No change | Scale-up | — | Not possible (large window contains small window data) |
| No change | No change | Small window | No change |
| No change | Scale-down | Hunting check | If small window trending up, use large to avoid hunting; else use small |
| Scale-down | Scale-up | — | Not possible (large window contains small window data) |
| Scale-down | No change | Large window | Service likely idling/stopped |
| Scale-down | Scale-down | Small window | Faster scale-down |

> When both windows agree on direction, we pick the small window for scale-downs
> (faster) and the large window for scale-ups (single-step to peak).

> Hunting check : current_small_window > previous_small_window If trending up :
> Trust large window (usage is rising, prevents hunting and scale in single step
> rather than gradually) If stable/down : Trust small window (safe to scale down)

> scale-down latency reduced from 30 hours to 3 hours

## Reading for this run

After an up-step sized to arm A's peak, the large window keeps that peak for 30 h
and recommends the size the service already has: "No change". Once arm B has run
long enough that the small window (3 h) no longer holds arm A's peak, the small
window recommends less, "Scale-down", but only if arm B's utilisation is below the
37.5% low watermark. The row "No change | Scale-down" goes to the hunting check,
which picks the small window unless the small-window recommendation is rising.
Under arm B's steady load it is falling or flat, so the small window decides, and
a step down is possible from about 3 h after the cut, plus the recommender's
cadence (not stated in either source) and the make-before-break overlap. The 30-h
window governs the size after an up-step only while the small window also wants
up or holds.

Not stated in either source: how often the recommender runs, whether utilisation is
the busiest replica or the mean, and how "maximum usage" is aggregated.

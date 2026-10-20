# Data notes

`revenue_2026_07_09.csv` contains the 90 original operating-day records provided for this project, covering July 1 through September 30, 2026, for a family breakfast shop in Ningbo, China.

| Column | Meaning |
|---|---|
| `date` | Operating date in `YYYY-MM-DD` format |
| `revenue` | Recorded revenue in CNY, including estimated cash and excluding Alipay |

The supplied amounts are preserved without rounding or decomposition into payment channels. The method used to estimate cash has not been established in the supplied material. These are recorded amounts, not independently verified complete revenue, profit, or customer counts.

July 12 and 13 were closed because of a typhoon. They are absent from the input and excluded from operating-day statistics. The chart reindexes to the full 92-day calendar, leaving both dates missing so the line has a gap. It does not fill zeros or interpolate.

Month, weekday (Monday = 0), and weekend flags are derived in the script. Weekday/weekend means Monday–Friday/Saturday–Sunday; holidays, adjusted workdays and actual school attendance are not incorporated.

Monthly checks: July 29 records / CNY 12,851.50; August 31 / CNY 13,754.00; September 30 / CNY 16,222.00.

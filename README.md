# A/B Test Analysis: Moving a Game Gate from Level 30 to Level 40

Product-analytics case study on a **public dataset**: the "Cookie Cats" mobile-game experiment
(90,189 players). Cookie Cats is a tile-matching game where progress is periodically "gated" (players
wait or pay to continue). The experiment moved the first gate from **level 30 (control, `gate_30`)** to
**level 40 (treatment, `gate_40`)**.

> **Data source:** public Cookie Cats dataset (originally from a DataCamp project, widely mirrored on Kaggle and GitHub).
> I did not run this experiment. The project shows how I design, check and read one.

**Question:** Does moving the gate hurt or help retention and engagement?
**Primary metric:** 7-day retention. **Secondary:** 1-day retention. **Engagement:** rounds played in the first 14 days.

## Result (short)

| Metric | gate_30 | gate_40 | Difference | 95% CI | p-value (Holm-adjusted) |
|---|---|---|---|---|---|
| 1-day retention | 44.82% | 44.23% | -0.59 pp | -1.24 to +0.06 pp | 0.074 (0.100) |
| **7-day retention** | **19.02%** | **18.20%** | **-0.82 pp (-4.3% relative)** | **-1.33 to -0.31 pp** | **0.0016 (0.0047)** |
| Median rounds played | 17 | 16 | -1 | n/a (discrete) | 0.050 (0.100) |

**Recommendation:** keep the gate at level 30. Moving it to level 40 lowers 7-day retention, and the drop
survives a multiple-testing correction. The 1-day and engagement differences are not statistically
distinguishable from zero.

## Checks that change how much to trust the result

- **Sample ratio mismatch (SRM):** 44,700 vs 45,489 players (49.56% / 50.44%). A 50/50 split would be expected;
  chi-square = 6.90, p = 0.0086. That is below 0.05 but above the strict 0.001 alarm threshold many
  teams use. I cannot diagnose the cause from this table, so I treat the estimates with some caution.
- **No duplicate users, no missing values.**
- **One extreme outlier:** a single `gate_30` player has 49,854 rounds (the next highest is 2,961). It inflates the
  `gate_30` mean (52.5 vs 51.3) and its standard deviation (257 vs 103), so engagement is compared with the
  median and a rank test. Removing the outlier changes retention by less than 0.01 pp.
- **Statistical power:** with about 45k players per arm, the smallest effect detectable with 80% power is
  about **0.74 pp for 7-day retention** and **0.93 pp for 1-day retention**. The observed 7-day drop (0.82 pp) is close to
  that limit, so smaller real effects would be missed.
- **Multiple tests:** three metrics were tested, so p-values were adjusted with Holm-Bonferroni.
- **Descriptive only:** retention by "rounds played" bucket uses a post-treatment variable (rounds are played after
  assignment), so it is shown for context, not as a causal result.

## Limitations

- Only 14 days of behaviour and no revenue data, so long-term value and gate monetization are unknown.
- I cannot verify how players were assigned (hence the SRM caution).
- The analysis is at the user level and assumes independent users.

## What is in this repo

```
data/cookie_cats.csv              public dataset
sql/01_load_and_clean.sql         grain, nulls, outlier checks (BigQuery)
sql/02_sample_ratio_check.sql     SRM chi-square components
sql/03_retention_ztest.sql        rates, difference, 95% CI, z for both retention metrics
sql/04_engagement_and_buckets.sql median via window functions, retention by rounds bucket
src/analysis.py                   all tests, bootstrap, Holm correction, power, charts, Tableau exports
src/validate_sql_duckdb.py        runs the SQL in DuckDB and checks it equals the Python numbers
outputs/                          results as CSV, charts, Tableau-ready table
INTERVIEW_GUIDE.md                questions to be ready for
```

## Reproduce

```bash
pip install pandas numpy scipy matplotlib duckdb
python src/analysis.py               # writes everything in outputs/
python src/validate_sql_duckdb.py    # SQL vs Python cross-check
```

### Run the SQL in BigQuery

```bash
bq mk --dataset YOUR_PROJECT:ab_test
bq load --source_format=CSV --skip_leading_rows=1 ab_test.cookie_cats data/cookie_cats.csv \
  userid:INTEGER,version:STRING,sum_gamerounds:INTEGER,retention_1:BOOLEAN,retention_7:BOOLEAN
```

Set `ab_test` as the default dataset (or prefix the table name), then run files `01` to `04`.
The SQL was validated in DuckDB and uses only standard functions, so BigQuery should return the same figures.

### Tableau Public

Use `outputs/tableau_retention_long.csv` (retention with CI bounds per variant) and
`outputs/retention_by_rounds_bucket.csv`. Suggested sheets: retention bars with CI error bars, difference
with CI, and retention by rounds bucket.

## Methods

Two-proportion z-test (pooled SE) and Wald 95% CI for retention; bootstrap CI as a cross-check (20,000 resamples);
Mann-Whitney U and a bootstrap CI for the difference in medians for the skewed rounds metric; Holm-Bonferroni
across the three tests; SRM chi-square; power and minimum detectable effect from the normal approximation.

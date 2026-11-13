-- Two-proportion z-test for retention_1 and retention_7 (gate_40 vs gate_30).
-- Reports rates, absolute difference in percentage points, 95% CI and z.
-- |z| > 1.96  =>  significant at the 5% level (two-sided).
WITH g AS (
  SELECT version,
         COUNT(*) AS n,
         SUM(CASE WHEN retention_1 THEN 1 ELSE 0 END) AS x1,
         SUM(CASE WHEN retention_7 THEN 1 ELSE 0 END) AS x7
  FROM cookie_cats
  GROUP BY version
),
w AS (
  SELECT
    MAX(CASE WHEN version = 'gate_30' THEN n  END) AS na,
    MAX(CASE WHEN version = 'gate_40' THEN n  END) AS nb,
    MAX(CASE WHEN version = 'gate_30' THEN x1 END) AS xa1,
    MAX(CASE WHEN version = 'gate_40' THEN x1 END) AS xb1,
    MAX(CASE WHEN version = 'gate_30' THEN x7 END) AS xa7,
    MAX(CASE WHEN version = 'gate_40' THEN x7 END) AS xb7
  FROM g
),
m AS (
  SELECT 'retention_1' AS metric, na, nb, xa1 AS xa, xb1 AS xb FROM w
  UNION ALL
  SELECT 'retention_7', na, nb, xa7, xb7 FROM w
),
r AS (
  SELECT metric, na, nb, xa, xb,
         1.0 * xa / na AS pa,
         1.0 * xb / nb AS pb,
         1.0 * (xa + xb) / (na + nb) AS pooled
  FROM m
)
SELECT metric,
       ROUND(100 * pa, 3) AS gate_30_pct,
       ROUND(100 * pb, 3) AS gate_40_pct,
       ROUND(100 * (pb - pa), 3) AS diff_pp,
       ROUND(100 * ((pb - pa) - 1.96 * SQRT(pa * (1 - pa) / na + pb * (1 - pb) / nb)), 3) AS ci_low_pp,
       ROUND(100 * ((pb - pa) + 1.96 * SQRT(pa * (1 - pa) / na + pb * (1 - pb) / nb)), 3) AS ci_high_pp,
       ROUND((pb - pa) / SQRT(pooled * (1 - pooled) * (1.0 / na + 1.0 / nb)), 3) AS z,
       ROUND(100 * (pb - pa) / (100 * pa) * 100, 2) AS rel_lift_pct,
       ABS((pb - pa) / SQRT(pooled * (1 - pooled) * (1.0 / na + 1.0 / nb))) > 1.96 AS significant_5pct
FROM r
ORDER BY metric;

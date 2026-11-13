-- Engagement: rounds played in the first 14 days (heavy-tailed, so look at the median).
-- Median without vendor-specific functions: average the middle one or two rows.
WITH ranked AS (
  SELECT version, sum_gamerounds,
         ROW_NUMBER() OVER (PARTITION BY version ORDER BY sum_gamerounds) AS rn,
         COUNT(*)     OVER (PARTITION BY version) AS cnt
  FROM cookie_cats
)
SELECT version,
       COUNT(*) AS users,
       ROUND(AVG(sum_gamerounds), 2) AS mean_rounds_over_all_rows,
       MAX(sum_gamerounds) AS max_rounds,
       AVG(CASE WHEN rn IN (FLOOR((cnt + 1) / 2.0), CEIL((cnt + 1) / 2.0)) THEN sum_gamerounds END) AS median_rounds
FROM ranked
GROUP BY version
ORDER BY version;

-- Retention by how many rounds a player played (descriptive only: rounds are
-- measured AFTER assignment, so do not read these as causal effects).
SELECT
  CASE WHEN sum_gamerounds = 0   THEN '0'
       WHEN sum_gamerounds <= 9  THEN '1-9'
       WHEN sum_gamerounds <= 29 THEN '10-29'
       WHEN sum_gamerounds <= 49 THEN '30-49'
       WHEN sum_gamerounds <= 99 THEN '50-99'
       WHEN sum_gamerounds <= 199 THEN '100-199'
       ELSE '200+' END AS rounds_bucket,
  version,
  COUNT(*) AS users,
  ROUND(AVG(CASE WHEN retention_1 THEN 1.0 ELSE 0.0 END), 4) AS retention_1,
  ROUND(AVG(CASE WHEN retention_7 THEN 1.0 ELSE 0.0 END), 4) AS retention_7
FROM cookie_cats
GROUP BY rounds_bucket, version
ORDER BY MIN(sum_gamerounds), version;

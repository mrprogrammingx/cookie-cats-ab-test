-- Sample ratio check: a 50/50 experiment should give ~equal group sizes.
-- chi2 = sum((observed - expected)^2 / expected); with 1 degree of freedom,
-- chi2 > 3.84 means p < 0.05 and chi2 > 10.83 means p < 0.001.
WITH counts AS (
  SELECT version, COUNT(*) AS n FROM cookie_cats GROUP BY version
),
tot AS (SELECT SUM(n) AS total FROM counts)
SELECT c.version,
       c.n AS users,
       ROUND(100.0 * c.n / t.total, 3) AS share_pct,
       t.total / 2.0 AS expected_users,
       POW(c.n - t.total / 2.0, 2) / (t.total / 2.0) AS chi2_component
FROM counts c CROSS JOIN tot t
ORDER BY c.version;
-- Add the two chi2_component values for the total chi-square statistic.

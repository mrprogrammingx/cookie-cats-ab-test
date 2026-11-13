-- BigQuery: load data/cookie_cats.csv into a table called `cookie_cats`
-- (BigQuery console > Add data > Upload, or:
--   bq load --autodetect --source_format=CSV --skip_leading_rows=1 your_dataset.cookie_cats data/cookie_cats.csv )
-- Quick look + basic cleaning checks. Run each query separately.

-- 1) Preview
SELECT * FROM cookie_cats LIMIT 10;

-- 2) Grain check: one row per user? (expect 0 duplicates)
SELECT COUNT(*) AS rows_total,
       COUNT(DISTINCT userid) AS unique_users,
       COUNT(*) - COUNT(DISTINCT userid) AS duplicate_userids
FROM cookie_cats;

-- 3) Nulls per column (expect 0)
SELECT SUM(CASE WHEN userid IS NULL THEN 1 ELSE 0 END)        AS null_userid,
       SUM(CASE WHEN version IS NULL THEN 1 ELSE 0 END)       AS null_version,
       SUM(CASE WHEN sum_gamerounds IS NULL THEN 1 ELSE 0 END) AS null_rounds,
       SUM(CASE WHEN retention_1 IS NULL THEN 1 ELSE 0 END)   AS null_ret1,
       SUM(CASE WHEN retention_7 IS NULL THEN 1 ELSE 0 END)   AS null_ret7
FROM cookie_cats;

-- 4) Outliers: top 5 values of rounds played (one user played 49,854 rounds in 14 days)
SELECT userid, version, sum_gamerounds
FROM cookie_cats
ORDER BY sum_gamerounds DESC
LIMIT 5;

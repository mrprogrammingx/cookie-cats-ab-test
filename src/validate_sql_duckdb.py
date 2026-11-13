"""Run the portable SQL files against DuckDB and compare with the Python analysis.
Usage: python src/validate_sql_duckdb.py
The same SQL runs in BigQuery (table name `cookie_cats`)."""
import pathlib, re
import duckdb, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
con = duckdb.connect()
con.execute(f"CREATE TABLE cookie_cats AS SELECT * FROM read_csv_auto('{ROOT/'data'/'cookie_cats.csv'}')")

def run(path):
    sql = (ROOT / "sql" / path).read_text()
    out = []
    for stmt in [s.strip() for s in re.split(r";\s*\n", sql) if s.strip()]:
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body.upper().startswith(("SELECT", "WITH")):
            out.append(con.execute(body).df())
    return out

pd.set_option("display.width", 200, "display.max_columns", 30)
for f in ["01_load_and_clean.sql", "02_sample_ratio_check.sql", "03_retention_ztest.sql", "04_engagement_and_buckets.sql"]:
    print("=====", f)
    for d in run(f):
        print(d.to_string(index=False)); print()

py = pd.read_csv(ROOT / "outputs" / "summary_metrics.csv").set_index("metric")
sql = run("03_retention_ztest.sql")[0].set_index("metric")
for m in ["retention_1", "retention_7"]:
    assert abs(sql.loc[m, "diff_pp"] - py.loc[m, "abs_diff_pp"]) < 0.001, m
    assert abs(sql.loc[m, "z"] - py.loc[m, "z"]) < 0.001, m
    assert abs(sql.loc[m, "ci_low_pp"] - py.loc[m, "ci_low_pp"]) < 0.001, m
    assert abs(sql.loc[m, "ci_high_pp"] - py.loc[m, "ci_high_pp"]) < 0.001, m
print("SQL results match the Python analysis (diff, z, CI) for retention_1 and retention_7")

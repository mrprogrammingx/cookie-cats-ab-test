"""A/B test analysis: Cookie Cats gate placement (gate_30 vs gate_40).

Dataset: public "Cookie Cats" mobile-game experiment (90,189 players).
Control = gate_30 (first gate at level 30). Treatment = gate_40 (first gate moved to level 40).
Metrics: retention_1, retention_7 (booleans) and sum_gamerounds (rounds played in first 14 days).

Run:  python src/analysis.py
Writes CSVs and charts to ./outputs
"""
import json
import pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
RNG = np.random.default_rng(42)
ALPHA = 0.05
CONTROL, TREAT = "gate_30", "gate_40"

df = pd.read_csv(ROOT / "data" / "cookie_cats.csv")
df["retention_1"] = df["retention_1"].astype(bool)
df["retention_7"] = df["retention_7"].astype(bool)

# ---------------------------------------------------------------- 1. data quality
a = df[df.version == CONTROL]
b = df[df.version == TREAT]
dq = {
    "rows": len(df),
    "unique_users": int(df.userid.nunique()),
    "duplicate_userids": int(df.userid.duplicated().sum()),
    "null_cells": int(df.isna().sum().sum()),
    "n_gate_30": len(a),
    "n_gate_40": len(b),
    "max_gamerounds": int(df.sum_gamerounds.max()),
    "second_max_gamerounds": int(df.sum_gamerounds.nlargest(2).iloc[-1]),
    "zero_round_users_gate_30": int((a.sum_gamerounds == 0).sum()),
    "zero_round_users_gate_40": int((b.sum_gamerounds == 0).sum()),
}
# Sample-ratio mismatch: is the split consistent with 50/50 assignment?
chi2, srm_p = stats.chisquare([len(a), len(b)], f_exp=[len(df) / 2, len(df) / 2])
dq["srm_chi2"] = float(chi2)
dq["srm_p_value"] = float(srm_p)
pd.Series(dq).rename("value").to_csv(OUT / "data_quality.csv", header=True)

# ---------------------------------------------------------------- 2. binary metrics
def two_prop(col):
    xa, na = int(a[col].sum()), len(a)
    xb, nb = int(b[col].sum()), len(b)
    pa, pb = xa / na, xb / nb
    diff = pb - pa
    # Wald 95% CI (unpooled) for the difference
    se = np.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb)
    z = stats.norm.ppf(1 - ALPHA / 2)
    lo, hi = diff - z * se, diff + z * se
    # Pooled z-test for H0: pa == pb
    pp = (xa + xb) / (na + nb)
    se0 = np.sqrt(pp * (1 - pp) * (1 / na + 1 / nb))
    zstat = diff / se0
    p = 2 * (1 - stats.norm.cdf(abs(zstat)))
    # Bootstrap of the difference. For a 0/1 metric, resampling n users with
    # replacement is equivalent to drawing Binomial(n, p_hat) counts.
    boot = RNG.binomial(nb, pb, 20000) / nb - RNG.binomial(na, pa, 20000) / na
    blo, bhi = np.percentile(boot, [2.5, 97.5])
    return {
        "metric": col, "type": "proportion",
        "gate_30": pa, "gate_40": pb,
        "abs_diff_pp": diff * 100, "ci_low_pp": lo * 100, "ci_high_pp": hi * 100,
        "rel_lift_pct": diff / pa * 100,
        "z": zstat, "p_value": p,
        "boot_ci_low_pp": blo * 100, "boot_ci_high_pp": bhi * 100,
    }

rows = [two_prop("retention_1"), two_prop("retention_7")]

# ---------------------------------------------------------------- 3. engagement metric
ga, gb = a.sum_gamerounds.to_numpy(), b.sum_gamerounds.to_numpy()
u, mw_p = stats.mannwhitneyu(gb, ga, alternative="two-sided")
med_boot = np.array([
    np.median(RNG.choice(gb, gb.size)) - np.median(RNG.choice(ga, ga.size))
    for _ in range(2000)
])
mlo, mhi = np.percentile(med_boot, [2.5, 97.5])
rows.append({
    "metric": "sum_gamerounds", "type": "count (heavy-tailed)",
    "gate_30": float(np.median(ga)), "gate_40": float(np.median(gb)),
    "abs_diff_pp": float(np.median(gb) - np.median(ga)),
    "ci_low_pp": mlo, "ci_high_pp": mhi,
    "rel_lift_pct": float((np.median(gb) - np.median(ga)) / np.median(ga) * 100),
    "z": np.nan, "p_value": float(mw_p),
    "boot_ci_low_pp": mlo, "boot_ci_high_pp": mhi,
})
summary = pd.DataFrame(rows)

# Multiple-testing: Holm-Bonferroni across the three tests
order = summary.p_value.argsort().to_numpy()
m = len(summary)
holm = np.empty(m)
running = 0.0
for rank, idx in enumerate(order):
    running = max(running, min(1.0, (m - rank) * summary.p_value.iloc[idx]))
    holm[idx] = running
summary["p_value_holm"] = holm
summary["significant_after_holm"] = summary.p_value_holm < ALPHA
summary.to_csv(OUT / "summary_metrics.csv", index=False)

# mean/median/percentiles for the engagement metric (descriptive)
desc = df.groupby("version").sum_gamerounds.describe(percentiles=[.5, .9, .99]).reset_index()
desc.to_csv(OUT / "gamerounds_descriptive.csv", index=False)

# Robustness: same retention tests with the single extreme outlier removed
no_out = df[df.sum_gamerounds < dq["max_gamerounds"]]
ra, rb = no_out[no_out.version == CONTROL], no_out[no_out.version == TREAT]
robust = {}
for col in ["retention_1", "retention_7"]:
    pa_, pb_ = ra[col].mean(), rb[col].mean()
    robust[col] = {"gate_30": pa_, "gate_40": pb_, "diff_pp": (pb_ - pa_) * 100}
pd.DataFrame(robust).T.to_csv(OUT / "robustness_no_outlier.csv")

# ---------------------------------------------------------------- 4. power / MDE
def mde_abs(p, n, power=0.8):
    z = stats.norm.ppf(1 - ALPHA / 2) + stats.norm.ppf(power)
    return z * np.sqrt(2 * p * (1 - p) / n)

def n_per_arm(p, delta, power=0.8):
    z = stats.norm.ppf(1 - ALPHA / 2) + stats.norm.ppf(power)
    return int(np.ceil(2 * p * (1 - p) * (z / delta) ** 2))

p1, p7 = a.retention_1.mean(), a.retention_7.mean()
power_rows = [
    {"metric": "retention_1", "baseline": p1, "n_per_arm_observed": len(a),
     "mde_abs_pp_80pct_power": mde_abs(p1, len(a)) * 100,
     "n_per_arm_to_detect_0.5pp": n_per_arm(p1, 0.005)},
    {"metric": "retention_7", "baseline": p7, "n_per_arm_observed": len(a),
     "mde_abs_pp_80pct_power": mde_abs(p7, len(a)) * 100,
     "n_per_arm_to_detect_0.5pp": n_per_arm(p7, 0.005)},
]
pd.DataFrame(power_rows).to_csv(OUT / "power_mde.csv", index=False)

# ---------------------------------------------------------------- 5. segments (descriptive)
bins = [-1, 0, 9, 29, 49, 99, 199, np.inf]
labels = ["0", "1-9", "10-29", "30-49", "50-99", "100-199", "200+"]
df["rounds_bucket"] = pd.cut(df.sum_gamerounds, bins=bins, labels=labels)
seg = (df.groupby(["rounds_bucket", "version"], observed=True)
         .agg(users=("userid", "count"),
              retention_1=("retention_1", "mean"),
              retention_7=("retention_7", "mean"))
         .reset_index())
seg.to_csv(OUT / "retention_by_rounds_bucket.csv", index=False)

# ---------------------------------------------------------------- 6. charts
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
for i, col in enumerate(["retention_1", "retention_7"]):
    r = summary[summary.metric == col].iloc[0]
    vals = [r.gate_30 * 100, r.gate_40 * 100]
    pa_, pb_ = r.gate_30, r.gate_40
    errs = [1.96 * np.sqrt(pa_ * (1 - pa_) / len(a)) * 100, 1.96 * np.sqrt(pb_ * (1 - pb_) / len(b)) * 100]
    ax[i].bar(["gate_30", "gate_40"], vals, yerr=errs, capsize=6, color=["#1F3B57", "#7A9CC6"])
    ax[i].set_title(f"{col}  (diff {r.abs_diff_pp:+.2f} pp, p={r.p_value:.4f})", fontsize=9)
    ax[i].set_ylabel("% of players")
    lo = min(vals) - 2
    ax[i].set_ylim(lo, max(vals) + 2)
fig.suptitle("Retention by gate placement (95% CI)", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "retention_by_variant.png", dpi=150)

fig2, ax2 = plt.subplots(figsize=(6.5, 3.6))
for v, c in [(CONTROL, "#1F3B57"), (TREAT, "#7A9CC6")]:
    x = df[(df.version == v) & (df.sum_gamerounds > 0)].sum_gamerounds
    ax2.hist(np.log10(x), bins=40, alpha=.6, label=v, color=c)
ax2.set_xlabel("log10(game rounds played in first 14 days)")
ax2.set_ylabel("players")
ax2.legend()
ax2.set_title("Game rounds are heavily skewed", fontsize=10)
fig2.tight_layout()
fig2.savefig(OUT / "gamerounds_distribution.png", dpi=150)

# ---------------------------------------------------------------- 6b. Tableau-ready long table
long_rows = []
for col in ["retention_1", "retention_7"]:
    for v, grp in [(CONTROL, a), (TREAT, b)]:
        p_, n_ = grp[col].mean(), len(grp)
        h = 1.96 * np.sqrt(p_ * (1 - p_) / n_)
        long_rows.append({"metric": col, "variant": v, "users": n_, "rate_pct": p_ * 100,
                          "ci_low_pct": (p_ - h) * 100, "ci_high_pct": (p_ + h) * 100})
pd.DataFrame(long_rows).to_csv(OUT / "tableau_retention_long.csv", index=False)

# ---------------------------------------------------------------- 7. print
pd.set_option("display.width", 200, "display.max_columns", 30)
print(json.dumps(dq, indent=2))
print(summary.round(4).to_string(index=False))
print(desc.round(2).to_string(index=False))
print(pd.DataFrame(power_rows).round(4).to_string(index=False))
print(pd.DataFrame(robust).T.round(4))
print(seg.round(4).to_string(index=False))

"""
Does regional [11C]PBR28 SUV change with age in healthy adults?

Reads results/roi_suv_values.csv and writes correlation tables
plus scatter plots to the results/ folder.
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results")
sns.set_theme(style="whitegrid")


def partial_r(age, suv, sex):
    """Pearson r between age and SUV after regressing out sex (M=1, rest=0)."""
    s = (sex.astype(str).str.upper() == "M").astype(int).to_numpy()

    def resid(y, x):
        slope, intercept, *_ = stats.linregress(x, y)
        return y - (slope * x + intercept)

    return stats.pearsonr(resid(age, s), resid(suv, s))


def main():
    csv_path = os.path.join(OUT, "roi_suv_values.csv")
    if not os.path.isfile(csv_path):
        print(f"ERROR: missing {csv_path} — run 03 first.")
        sys.exit(1)

    df = pd.read_csv(csv_path).dropna(subset=["SUV_g_per_mL", "age"])
    if df.empty:
        print("ERROR: no usable rows in roi_suv_values.csv")
        sys.exit(1)

    rows = []
    regions = sorted(df["region"].unique())

    for reg in regions:
        sub = df[df["region"] == reg]
        if len(sub) < 5:
            print(f"  Skipping {reg}: only {len(sub)} subjects")
            continue

        r0, p0 = stats.pearsonr(sub["age"], sub["SUV_g_per_mL"])
        r1, p1 = partial_r(
            sub["age"].to_numpy(),
            sub["SUV_g_per_mL"].to_numpy(),
            sub["sex"],
        )

        rows.append({
            "region": reg,
            "n": len(sub),
            "pearson_r": r0,
            "pearson_p": p0,
            "partial_r_ctrl_sex": r1,
            "partial_p": p1,
        })

        # Scatter plot with regression line
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.regplot(data=sub, x="age", y="SUV_g_per_mL", ci=95, ax=ax)
        ax.set_xlabel("Age (years)")
        ax.set_ylabel("[11C]PBR28 SUV (g/mL)")
        ax.set_title(f"{reg}\nr = {r0:.2f}, p = {p0:.3f}, n = {len(sub)}")
        fig.tight_layout()

        safe_name = (
            reg.lower()
            .replace(" ", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
        fig.savefig(os.path.join(OUT, f"scatter_{safe_name}.png"), dpi=150)
        plt.close(fig)

    if not rows:
        print("ERROR: nothing to summarise.")
        sys.exit(1)

    summary = pd.DataFrame(rows).sort_values("partial_r_ctrl_sex")
    summary.to_csv(os.path.join(OUT, "age_suv_correlations.csv"), index=False)

    # Summary bar chart
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.barplot(
        data=summary,
        y="region",
        x="partial_r_ctrl_sex",
        hue="region",
        palette="vlag",
        legend=False,
        ax=ax,
    )
    ax.set_xlabel("Partial correlation with age (controlling for sex)")
    ax.set_ylabel("")
    n = df["participant_id"].nunique()
    ax.set_title(f"Regional [11C]PBR28 SUV vs age  (HC n = {n})")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "age_effect_summary.png"), dpi=150)
    plt.close(fig)

    print(summary.to_string(index=False))
    print(f"\nWrote plots and table to {OUT}")


if __name__ == "__main__":
    main()
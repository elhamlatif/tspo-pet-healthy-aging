"""
04_analyze_and_plot.py

Simple normative question:
Does regional [11C]PBR28 SUV (g/mL) change with age in healthy adults?

Reads results/roi_suv_values.csv and writes:
    results/age_suv_correlations.csv
    results/scatter_<region>.png
    results/age_effect_summary.png
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "..", "results")

sns.set_theme(style="whitegrid")


def partial_corr_sex(age, suv, sex):
    """Pearson r between age and SUV after residualising both on sex (0/1)."""
    sex_num = (sex.astype(str).str.upper() == "M").astype(int).to_numpy()

    def resid(y, x):
        slope, intercept, *_ = stats.linregress(x, y)
        return y - (slope * x + intercept)

    r, p = stats.pearsonr(resid(age, sex_num), resid(suv, sex_num))
    return r, p


def main():
    csv_path = os.path.join(RESULTS_DIR, "roi_suv_values.csv")
    if not os.path.isfile(csv_path):
        print(f"ERROR: {csv_path} not found. Run 03_extract_roi_values.py first.")
        sys.exit(1)

    df = pd.read_csv(csv_path).dropna(subset=["SUV_g_per_mL", "age"])
    if df.empty:
        print("ERROR: no usable rows in roi_suv_values.csv")
        sys.exit(1)

    summary = []
    regions = sorted(df["region"].unique())

    for region in regions:
        sub = df[df["region"] == region]
        if len(sub) < 5:
            print(f"  skip {region}: only {len(sub)} subjects")
            continue

        r_simple, p_simple = stats.pearsonr(sub["age"], sub["SUV_g_per_mL"])
        r_part, p_part = partial_corr_sex(
            sub["age"].to_numpy(),
            sub["SUV_g_per_mL"].to_numpy(),
            sub["sex"],
        )

        summary.append(
            {
                "region": region,
                "n": len(sub),
                "pearson_r": r_simple,
                "pearson_p": p_simple,
                "partial_r_ctrl_sex": r_part,
                "partial_p": p_part,
            }
        )

        # scatter
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.regplot(data=sub, x="age", y="SUV_g_per_mL", ci=95, ax=ax)
        ax.set_xlabel("Age (years)")
        ax.set_ylabel("[11C]PBR28 SUV (g/mL)")
        ax.set_title(f"{region}\nr = {r_simple:.2f}, p = {p_simple:.3f}, n = {len(sub)}")
        fig.tight_layout()

        safe = (
            region.lower()
            .replace(" ", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
        fig.savefig(os.path.join(RESULTS_DIR, f"scatter_{safe}.png"), dpi=150)
        plt.close(fig)

    if not summary:
        print("Nothing to summarise.")
        sys.exit(1)

    summary_df = pd.DataFrame(summary)

    def fdr_bh(pvals):
        pvals = np.asarray(pvals)
        n = len(pvals)
        order = np.argsort(pvals)
        ranked = pvals[order] * n / (np.arange(n) + 1)
        ranked = np.minimum.accumulate(ranked[::-1])[::-1]
        adjusted = np.empty(n)
        adjusted[order] = np.clip(ranked, 0, 1)
        return adjusted

    summary_df["pearson_p_fdr"] = fdr_bh(summary_df["pearson_p"].to_numpy())
    summary_df["partial_p_fdr"] = fdr_bh(summary_df["partial_p"].to_numpy())
    summary_df = summary_df.sort_values("partial_r_ctrl_sex")

    summary_df.to_csv(
        os.path.join(RESULTS_DIR, "age_suv_correlations.csv"), index=False
    )

    # bar chart of partial correlations
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.barplot(
        data=summary_df,
        y="region",
        x="partial_r_ctrl_sex",
        hue="region",
        palette="vlag",
        legend=False,
        ax=ax,
    )
    ax.set_xlabel("Partial correlation with age (controlling for sex)")
    ax.set_ylabel("")
    n_sub = df["participant_id"].nunique()
    ax.set_title(f"Regional [11C]PBR28 SUV vs age  (HC n = {n_sub})")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "age_effect_summary.png"), dpi=150)
    plt.close(fig)

    print(summary_df.to_string(index=False))
    print(f"\nFigures and table written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()

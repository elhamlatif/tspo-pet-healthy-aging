"""
Does regional [11C]PBR28 SUV change with age in healthy adults?

This script reads results/roi_suv_values.csv,
computes the correlation between age and SUV for each brain region,
corrects p-values with FDR,
and saves the table plus plots to results/.
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from statsmodels.stats.multitest import multipletests

# Path to the results folder
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "results")

# Style for the plots
sns.set_theme(style="whitegrid")


def partial_r(age, suv, sex):
    """
    Partial correlation between age and SUV, controlling for sex.

    How it works: first we remove the effect of sex from both age and SUV
    (residualize), then compute the Pearson correlation on the residuals.

    Sex coding: M = 1, everyone else = 0.
    """
    # Turn sex into a number
    sex_num = (sex.astype(str).str.upper() == "M").astype(int).to_numpy()

    def residualize(y, x):
        # Fit a line of y on x, then return the residuals
        slope, intercept, *_ = stats.linregress(x, y)
        return y - (slope * x + intercept)

    # Age with the effect of sex removed
    age_res = residualize(age, sex_num)
    # SUV with the effect of sex removed
    suv_res = residualize(suv, sex_num)

    # Correlate the two residuals
    return stats.pearsonr(age_res, suv_res)


def main():
    # ----------------------------------------------------------------
    # 1. Load the data
    # ----------------------------------------------------------------
    csv_path = os.path.join(OUT, "roi_suv_values.csv")
    if not os.path.isfile(csv_path):
        print(f"ERROR: {csv_path} not found. Run 03 first.")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    # Drop rows missing SUV or age
    df = df.dropna(subset=["SUV_g_per_mL", "age"])

    if df.empty:
        print("ERROR: no usable rows in roi_suv_values.csv")
        sys.exit(1)

    # ----------------------------------------------------------------
    # 2. For each region, compute the correlations
    # ----------------------------------------------------------------
    rows = []
    regions = sorted(df["region"].unique())

    for region in regions:
        sub = df[df["region"] == region]

        # Skip if fewer than 5 subjects
        if len(sub) < 5:
            print(f"  Skipping {region}: only {len(sub)} subjects")
            continue

        # Simple Pearson correlation between age and SUV
        r_simple, p_simple = stats.pearsonr(sub["age"], sub["SUV_g_per_mL"])

        # Partial correlation, controlling for sex
        r_partial, p_partial = partial_r(
            sub["age"].to_numpy(),
            sub["SUV_g_per_mL"].to_numpy(),
            sub["sex"],
        )

        # Store this region's results
        rows.append({
            "region": region,
            "n": len(sub),
            "pearson_r": r_simple,
            "pearson_p": p_simple,
            "partial_r_ctrl_sex": r_partial,
            "partial_p": p_partial,
        })

        # ------------------------------------------------------------
        # Scatter plot for this region
        # ------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.regplot(data=sub, x="age", y="SUV_g_per_mL", ci=95, ax=ax)
        ax.set_xlabel("Age (years)")
        ax.set_ylabel("[11C]PBR28 SUV (g/mL)")
        ax.set_title(f"{region}\nr = {r_simple:.2f}, p = {p_simple:.3f}, n = {len(sub)}")
        fig.tight_layout()

        # Build a safe filename from the region name
        safe_name = (
            region.lower()
            .replace(" ", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
        fig.savefig(os.path.join(OUT, f"scatter_{safe_name}.png"), dpi=150)
        plt.close(fig)

    # If nothing could be computed, bail out
    if not rows:
        print("ERROR: nothing to summarise.")
        sys.exit(1)

    # ----------------------------------------------------------------
    # 3. FDR correction (Benjamini-Hochberg)
    # ----------------------------------------------------------------
    # Because we're testing many regions at once,
    # we adjust the p-values using FDR
    summary = pd.DataFrame(rows)

    _, p_fdr_pearson, _, _ = multipletests(summary["pearson_p"], method="fdr_bh")
    _, p_fdr_partial, _, _ = multipletests(summary["partial_p"], method="fdr_bh")

    summary["pearson_p_fdr"] = p_fdr_pearson
    summary["partial_p_fdr"] = p_fdr_partial

    # Did anything stay significant after FDR?
    summary["significant_after_fdr"] = summary["partial_p_fdr"] < 0.05

    # Sort by the partial correlation
    summary = summary.sort_values("partial_r_ctrl_sex")

    # Save the table
    summary.to_csv(os.path.join(OUT, "age_suv_correlations.csv"), index=False)

    # ----------------------------------------------------------------
    # 4. Summary bar chart
    # ----------------------------------------------------------------
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
    n_subjects = df["participant_id"].nunique()
    ax.set_title(f"Regional [11C]PBR28 SUV vs age  (HC n = {n_subjects})")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "age_effect_summary.png"), dpi=150)
    plt.close(fig)

    # ----------------------------------------------------------------
    # 5. Print the result
    # ----------------------------------------------------------------
    print(summary.to_string(index=False))
    print(f"\nWrote plots and table to {OUT}")


if __name__ == "__main__":
    main()
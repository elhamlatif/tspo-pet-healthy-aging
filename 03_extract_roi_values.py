"""
Extract mean PET SUV (g/mL) inside selected Harvard-Oxford ROIs
for every HC subject that has an MNI-space PET image
(output of 02_preprocess_t1_pet.sh).

Merges results with age and sex from participants.tsv
and writes results/roi_suv_values.csv.
"""

import glob
import os
import sys

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.datasets import fetch_atlas_harvard_oxford
from nilearn.image import resample_to_img

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "results")
os.makedirs(OUT, exist_ok=True)

# ROI names matched as substrings against atlas labels
CORTICAL = [
    "Frontal Pole",
    "Insular Cortex",
    "Cingulate Gyrus, anterior",
    "Cingulate Gyrus, posterior",
    "Temporal Pole",
]

SUBCORTICAL = [
    "Left Hippocampus",
    "Right Hippocampus",
    "Left Thalamus",
    "Right Thalamus",
    "Left Amygdala",
    "Right Amygdala",
]


def load_atlases():
    cort = fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm")
    sub = fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm")
    return (
        nib.load(cort.maps), list(cort.labels),
        nib.load(sub.maps), list(sub.labels),
    )


def find_label(labels, query):
    """Return first index whose label contains `query` (case-insensitive)."""
    q = query.lower()
    for i, lab in enumerate(labels):
        if q in lab.lower():
            return i
    return None


def roi_mean(pet_img, atlas_img, idx):
    atlas = resample_to_img(atlas_img, pet_img, interpolation="nearest")
    mask = atlas.get_fdata() == idx
    if not np.any(mask):
        return np.nan
    return float(pet_img.get_fdata()[mask].mean())


def main():
    participants_file = os.path.join(DATA, "participants.tsv")
    if not os.path.isfile(participants_file):
        print(f"ERROR: missing {participants_file} — run 01 first.")
        sys.exit(1)

    df = pd.read_csv(participants_file, sep="\t")

    # Keep only HC subjects
    if "group" in df.columns:
        hc = df[df["group"].str.contains("HC", case=False, na=False)].copy()
    else:
        hc = df[df["participant_id"].str.startswith("sub-HC")].copy()

    if hc.empty:
        print("ERROR: no HC subjects found in participants.tsv")
        sys.exit(1)

    print(f"Found {len(hc)} HC subjects")

    cort_img, cort_labels, sub_img, sub_labels = load_atlases()

    wanted = (
        [(cort_img, cort_labels, name) for name in CORTICAL]
        + [(sub_img, sub_labels, name) for name in SUBCORTICAL]
    )

    rows = []
    for _, row in hc.iterrows():
        sid = row["participant_id"]
        hits = glob.glob(os.path.join(DATA, sid, "derivatives", "PET_SUV_MNI.nii.gz"))

        if not hits:
            print(f"  Skipping {sid}: no MNI PET found")
            continue

        pet = nib.load(hits[0])

        for atlas_img, labels, query in wanted:
            idx = find_label(labels, query)
            if idx is None:
                print(f"  Warning: no atlas label matched '{query}'")
                continue

            rows.append({
                "participant_id": sid,
                "age": row.get("age", np.nan),
                "sex": row.get("sex", ""),
                "region": query,
                "SUV_g_per_mL": roi_mean(pet, atlas_img, idx),
            })

    if not rows:
        print("ERROR: nothing extracted — did preprocessing finish?")
        sys.exit(1)

    result = pd.DataFrame(rows)
    out_path = os.path.join(OUT, "roi_suv_values.csv")
    result.to_csv(out_path, index=False)

    n_subjects = result["participant_id"].nunique()
    print(f"Wrote {len(result)} rows from {n_subjects} subjects ? {out_path}")


if __name__ == "__main__":
    main()
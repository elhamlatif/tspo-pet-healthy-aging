"""
03_extract_roi_values.py

Extract mean PET SUV (g/mL) inside a set of Harvard-Oxford ROIs for every
HC subject that has an MNI-space PET image (produced by 02_preprocess_t1_pet.sh).
Results are merged with age and sex from participants.tsv.

Output
------
results/roi_suv_values.csv
    participant_id, age, sex, region, SUV_g_per_mL
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
DATA_DIR = os.path.join(HERE, "..", "data")
RESULTS_DIR = os.path.join(HERE, "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Regions we care about.  Names are matched with a simple substring search
# against the atlas labels, so small differences in wording still work.
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
        cort.maps,
        list(cort.labels),
        sub.maps,
        list(sub.labels),
    )


def find_label_index(labels, query):
    """Return the first atlas index whose label contains the query string
    (case-insensitive).  Returns None if nothing matches."""
    q = query.lower()
    for i, lab in enumerate(labels):
        if q in lab.lower():
            return i
    return None


def region_mean(pet_img, atlas_img, label_idx):
    atlas_resamp = resample_to_img(atlas_img, pet_img, interpolation="nearest")
    mask = atlas_resamp.get_fdata() == label_idx
    if not np.any(mask):
        return np.nan
    return float(np.mean(pet_img.get_fdata()[mask]))


def main():
    participants_path = os.path.join(DATA_DIR, "participants.tsv")
    if not os.path.isfile(participants_path):
        print(f"ERROR: {participants_path} not found. Run 01_get_hc_subjects.sh first.")
        sys.exit(1)

    participants = pd.read_csv(participants_path, sep="\t")

    # keep only rows that look like healthy controls
    if "group" in participants.columns:
        hc = participants[participants["group"].str.contains("HC", case=False, na=False)].copy()
    else:
        # fall back to participant_id pattern
        hc = participants[participants["participant_id"].str.startswith("sub-HC")].copy()

    if hc.empty:
        print("ERROR: no healthy-control subjects found in participants.tsv")
        sys.exit(1)

    print(f"Processing {len(hc)} HC subjects...")

    cort_img, cort_labels, sub_img, sub_labels = load_atlases()

    # build list of (atlas_img, labels, query_name)
    wanted = [(cort_img, cort_labels, name) for name in CORTICAL] + [
        (sub_img, sub_labels, name) for name in SUBCORTICAL
    ]

    rows = []
    for _, prow in hc.iterrows():
        sub_id = prow["participant_id"]
        pet_candidates = glob.glob(
            os.path.join(DATA_DIR, sub_id, "derivatives", "PET_SUV_MNI.nii.gz")
        )
        if not pet_candidates:
            print(f"  skip {sub_id}: no MNI-space PET found")
            continue

        pet_img = nib.load(pet_candidates[0])

        for atlas_img, labels, query in wanted:
            idx = find_label_index(labels, query)
            if idx is None:
                print(f"  WARNING: no atlas label matched '{query}'")
                continue

            suv = region_mean(pet_img, atlas_img, idx)
            rows.append(
                {
                    "participant_id": sub_id,
                    "age": prow.get("age", np.nan),
                    "sex": prow.get("sex", ""),
                    "region": query,          # keep the short name we asked for
                    "SUV_g_per_mL": suv,
                }
            )

    if not rows:
        print("ERROR: nothing extracted. Check that preprocessing finished successfully.")
        sys.exit(1)

    out_df = pd.DataFrame(rows)
    out_path = os.path.join(RESULTS_DIR, "roi_suv_values.csv")
    out_df.to_csv(out_path, index=False)
    n_sub = out_df["participant_id"].nunique()
    print(f"Wrote {len(out_df)} rows ({n_sub} subjects) → {out_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Preprocess T1 + PET for each HC subject:
#   1. bet     — skull-strip T1
#   2. flirt   — affine registration to MNI152 2mm
#   3. fnirt   — nonlinear refinement
#   4. applywarp — apply the same warp to PET
#
# PET is already co-registered to native T1 by the data providers,
# so a single transform is used for both. PET remains in SUV (g/mL).
#
# Requires: FSL >= 6.0 and $FSLDIR set.
set -euo pipefail

if [[ -z "${FSLDIR:-}" ]]; then
    echo "ERROR: FSLDIR is not set."
    echo "Source your FSL config first, or run 'ml fsl' in Neurodesk."
    exit 1
fi

DATA="$(cd "$(dirname "$0")/.." && pwd)/data"
MNI_BRAIN="${FSLDIR}/data/standard/MNI152_T1_2mm_brain.nii.gz"
MNI_HEAD="${FSLDIR}/data/standard/MNI152_T1_2mm.nii.gz"
MNI_CNF="${FSLDIR}/etc/flirtsch/T1_2_MNI152_2mm.cnf"

for f in "$MNI_BRAIN" "$MNI_HEAD" "$MNI_CNF"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: missing FSL file: $f"
        exit 1
    fi
done

shopt -s nullglob
SUBJECTS=("$DATA"/sub-HC*)

if [[ ${#SUBJECTS[@]} -eq 0 ]]; then
    echo "ERROR: no sub-HC* folders found under $DATA"
    echo "Run 01_get_hc_subjects.sh first."
    exit 1
fi

for subject_dir in "${SUBJECTS[@]}"; do
    subject=$(basename "$subject_dir")
    t1=$(find "$subject_dir/anat" -iname "*T1w.nii.gz" 2>/dev/null | head -n1)
    pet=$(find "$subject_dir/pet"  -iname "*pet.nii.gz" 2>/dev/null | head -n1)

    if [[ -z "$t1" || -z "$pet" ]]; then
        echo "Skipping $subject — missing T1 or PET"
        continue
    fi

    out_dir="$subject_dir/derivatives"
    mkdir -p "$out_dir"

    echo "=== $subject ==="
    echo "  bet (skull-stripping)"
    bet "$t1" "$out_dir/T1_brain.nii.gz" -f 0.35 -R

    echo "  flirt (affine registration)"
    flirt -in  "$out_dir/T1_brain.nii.gz" \
          -ref "$MNI_BRAIN" \
          -omat "$out_dir/T1_to_MNI_affine.mat" \
          -out  "$out_dir/T1_to_MNI_linear.nii.gz"

    echo "  fnirt (nonlinear registration)"
    fnirt --in="$t1" \
          --ref="$MNI_HEAD" \
          --aff="$out_dir/T1_to_MNI_affine.mat" \
          --config="$MNI_CNF" \
          --cout="$out_dir/T1_to_MNI_warp.nii.gz" \
          --iout="$out_dir/T1_to_MNI_nonlinear.nii.gz"

    echo "  applywarp (transform PET)"
    applywarp --in="$pet" \
              --ref="$MNI_HEAD" \
              --warp="$out_dir/T1_to_MNI_warp.nii.gz" \
              --out="$out_dir/PET_SUV_MNI.nii.gz" \
              --interp=trilinear

    echo "  ? $out_dir/PET_SUV_MNI.nii.gz"
done

echo
echo "All done."
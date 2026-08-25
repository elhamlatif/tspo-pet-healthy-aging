#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 02_preprocess_t1_pet.sh
#
# For each HC subject:
#   1. Brain-extract the T1w image          (bet)
#   2. Linear registration to MNI152 2 mm   (flirt)
#   3. Nonlinear refinement                 (fnirt)
#   4. Apply the same warp to the PET image (applywarp)
#
# The PET image is already co-registered to the native T1 by the data
# providers, so one transform carries both modalities into MNI space.
# PET intensities are left untouched — they stay in SUV (g/mL).
#
# Requires: FSL >= 6.0  ($FSLDIR must be set)
# ---------------------------------------------------------------------------
set -euo pipefail

if [[ -z "${FSLDIR:-}" ]]; then
    echo "Error: FSLDIR is not set."
    echo "Source your FSL configuration first, e.g.:"
    echo "  source \${FSLDIR}/etc/fslconf/fsl.sh"
    echo "Or, if you are inside Neurodesk:  ml fsl"
    exit 1
fi

DATA_DIR="$(cd "$(dirname "$0")/.." && pwd)/data"
MNI_BRAIN="${FSLDIR}/data/standard/MNI152_T1_2mm_brain.nii.gz"
MNI_HEAD="${FSLDIR}/data/standard/MNI152_T1_2mm.nii.gz"
MNI_CONFIG="${FSLDIR}/etc/flirtsch/T1_2_MNI152_2mm.cnf"

# quick sanity check that the standard templates exist
for f in "${MNI_BRAIN}" "${MNI_HEAD}" "${MNI_CONFIG}"; do
    if [[ ! -f "${f}" ]]; then
        echo "Error: expected FSL file not found: ${f}"
        exit 1
    fi
done

shopt -s nullglob
SUBJECTS=("${DATA_DIR}"/sub-HC*)
if [[ ${#SUBJECTS[@]} -eq 0 ]]; then
    echo "No sub-HC* folders found under ${DATA_DIR}."
    echo "Run scripts/01_get_hc_subjects.sh first."
    exit 1
fi

for SUBDIR in "${SUBJECTS[@]}"; do
    SUB=$(basename "${SUBDIR}")
    T1=$(find "${SUBDIR}/anat" -iname "*T1w.nii.gz" 2>/dev/null | head -n 1)
    PET=$(find "${SUBDIR}/pet"  -iname "*pet.nii.gz" 2>/dev/null | head -n 1)

    if [[ -z "${T1}" || -z "${PET}" ]]; then
        echo "WARNING: missing T1 or PET for ${SUB} — skipping."
        continue
    fi

    OUT="${SUBDIR}/derivatives"
    mkdir -p "${OUT}"
    echo "=== ${SUB} ==="

    # 1. Brain extraction
    echo "  bet..."
    bet "${T1}" "${OUT}/T1_brain.nii.gz" -f 0.35 -R

    # 2. Linear registration (brain → MNI brain)
    echo "  flirt..."
    flirt -in  "${OUT}/T1_brain.nii.gz" \
          -ref "${MNI_BRAIN}" \
          -omat "${OUT}/T1_to_MNI_affine.mat" \
          -out  "${OUT}/T1_to_MNI_linear.nii.gz"

    # 3. Nonlinear refinement (full head + affine)
    echo "  fnirt..."
    fnirt --in="${T1}" \
          --ref="${MNI_HEAD}" \
          --aff="${OUT}/T1_to_MNI_affine.mat" \
          --config="${MNI_CONFIG}" \
          --cout="${OUT}/T1_to_MNI_warp.nii.gz" \
          --iout="${OUT}/T1_to_MNI_nonlinear.nii.gz"

    # 4. Warp the PET image (SUV values preserved)
    echo "  applywarp (PET)..."
    applywarp --in="${PET}" \
              --ref="${MNI_HEAD}" \
              --warp="${OUT}/T1_to_MNI_warp.nii.gz" \
              --out="${OUT}/PET_SUV_MNI.nii.gz" \
              --interp=trilinear

    echo "  → ${OUT}/PET_SUV_MNI.nii.gz"
done

echo ""
echo "All subjects processed."

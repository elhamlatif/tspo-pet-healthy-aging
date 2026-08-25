#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 01_get_hc_subjects.sh
#
# Downloads only the healthy-control (HC) subjects from OpenNeuro ds007907
# (T1w + PET SUV images + JSON sidecars + participants.tsv/json).
# Patient data (CLBP, KOA, etc.) is left out on purpose.
#
# Uses the public OpenNeuro S3 mirror — no AWS credentials needed.
# Requires: awscli (pip install awscli  or  aws-cli v2)
# ---------------------------------------------------------------------------
set -euo pipefail

DATASET_ID="ds007907"
BUCKET="s3://openneuro.org/${DATASET_ID}"
DEST_DIR="$(cd "$(dirname "$0")/.." && pwd)/data"

mkdir -p "${DEST_DIR}"

echo "Downloading top-level metadata..."
aws s3 cp "${BUCKET}/participants.tsv"          "${DEST_DIR}/" --no-sign-request
aws s3 cp "${BUCKET}/participants.json"         "${DEST_DIR}/" --no-sign-request
aws s3 cp "${BUCKET}/dataset_description.json"  "${DEST_DIR}/" --no-sign-request

# ---------------------------------------------------------------
# Figure out which column holds the group label, then pull HC IDs.
# (Column order can vary slightly across dataset versions.)
# ---------------------------------------------------------------
HEADER=$(head -n 1 "${DEST_DIR}/participants.tsv")
IFS=$'\t' read -r -a COLS <<< "${HEADER}"

GROUP_COL=-1
for i in "${!COLS[@]}"; do
    if [[ "${COLS[$i]}" == "group" ]]; then
        GROUP_COL=$((i + 1))   # awk is 1-indexed
        break
    fi
done

if [[ ${GROUP_COL} -eq -1 ]]; then
    echo "ERROR: could not find a 'group' column in participants.tsv"
    echo "Header was: ${HEADER}"
    exit 1
fi

echo "Using column ${GROUP_COL} ('group') to select healthy controls."

# Collect unique group values so the user can see what is available
echo "Available groups:"
cut -f"${GROUP_COL}" "${DEST_DIR}/participants.tsv" | tail -n +2 | sort | uniq -c

HC_SUBJECTS=$(awk -F'\t' -v col="${GROUP_COL}" \
    'NR>1 && $col ~ /HC/ {print $1}' "${DEST_DIR}/participants.tsv")

N_HC=$(echo "${HC_SUBJECTS}" | grep -c . || true)
echo "Found ${N_HC} HC subjects."

if [[ ${N_HC} -eq 0 ]]; then
    echo "ERROR: no subjects matched the HC filter. Check the group labels above."
    exit 1
fi

for SUB in ${HC_SUBJECTS}; do
    echo "  → ${SUB}"
    aws s3 sync "${BUCKET}/${SUB}/" "${DEST_DIR}/${SUB}/" \
        --no-sign-request \
        --exclude "*" \
        --include "anat/*T1w*" \
        --include "pet/*"
done

echo ""
echo "Done. HC-only data is in: ${DEST_DIR}"

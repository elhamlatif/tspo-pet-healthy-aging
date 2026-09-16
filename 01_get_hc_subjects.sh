#!/usr/bin/env bash
# Download only healthy-control (HC) subjects from OpenNeuro ds007907.
# Includes T1w + PET images and sidecars. Patients are skipped on purpose.
# Uses the public S3 mirror (no AWS credentials required).
# Requires: awscli
set -euo pipefail

DATASET="ds007907"
BUCKET="s3://openneuro.org/${DATASET}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${ROOT}/data"

mkdir -p "${DATA}"

echo "Downloading top-level metadata..."
aws s3 cp "${BUCKET}/participants.tsv"         "${DATA}/" --no-sign-request
aws s3 cp "${BUCKET}/participants.json"        "${DATA}/" --no-sign-request
aws s3 cp "${BUCKET}/dataset_description.json" "${DATA}/" --no-sign-request

# Find the 'group' column (column order can change between dataset versions)
HEADER=$(head -n1 "${DATA}/participants.tsv")
IFS=$'\t' read -r -a COLS <<< "${HEADER}"

GROUP_COL=""
for i in "${!COLS[@]}"; do
    if [[ "${COLS[$i]}" == "group" ]]; then
        GROUP_COL=$((i + 1))
        break
    fi
done

if [[ -z "${GROUP_COL}" ]]; then
    echo "ERROR: no 'group' column found in participants.tsv"
    echo "Header was: ${HEADER}"
    exit 1
fi

echo "Available groups:"
cut -f"${GROUP_COL}" "${DATA}/participants.tsv" | tail -n +2 | sort | uniq -c

# Select HC subjects
HC_SUBJECTS=$(awk -F'\t' -v col="${GROUP_COL}" \
    'NR>1 && $col ~ /HC/ {print $1}' "${DATA}/participants.tsv")

N_HC=$(printf '%s\n' "${HC_SUBJECTS}" | grep -c . || true)
echo "Found ${N_HC} HC subjects"

if [[ "${N_HC}" -eq 0 ]]; then
    echo "ERROR: no subjects matched the HC filter. Check the groups listed above."
    exit 1
fi

# Download T1w and PET data for each HC subject
for sub in ${HC_SUBJECTS}; do
    echo "  ? ${sub}"
    aws s3 sync "${BUCKET}/${sub}/" "${DATA}/${sub}/" \
        --no-sign-request \
        --exclude "*" \
        --include "anat/*T1w*" \
        --include "pet/*"
done

echo
echo "Done. Data is in: ${DATA}"
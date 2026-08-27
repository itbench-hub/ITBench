#!/usr/bin/env bash
# Prints AWS credentials as export statements for eval.
# Usage: eval $(scripts/export-aws-credentials.sh [profile])
# If aws CLI is not installed, prints a warning to stderr and exits cleanly.

PROFILE=${1:-default}

if ! command -v aws > /dev/null 2>&1; then
    echo "Warning: aws CLI not found — skipping credential export. S3 storage will not be available." >&2
    exit 0
fi

aws configure export-credentials --format env --profile "$PROFILE"

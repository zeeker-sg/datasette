#!/bin/bash
set -e

# Run the S3 download script if S3_BUCKET is provided
if [ -n "$S3_BUCKET" ]; then
    echo "Downloading databases from S3 bucket: $S3_BUCKET"
    uv run /app/scripts/download_from_s3.py
else
    echo "No S3_BUCKET specified, skipping database download"
fi

# Check if any databases were downloaded
if [ -z "$(ls -A /data)" ]; then
    echo "Warning: No databases found in /data directory"
fi

# List downloaded databases
echo "Available databases:"
ls -la /data

# Start Datasette with immutable flag
# Phase-7 prune: --template-dir /app/templates and --static static:/app/static
# flags removed because Plan 07-04 deleted the corresponding top-level
# directories. Datasette 0.65.2 does NOT gracefully handle a missing
# --template-dir (it errors `Invalid value for '--template-dir': Directory
# '/app/templates' does not exist.`); the same applies to --static. The
# frontend service now owns all HTML rendering + static assets, so neither
# flag is needed by the datasette image.
echo "Starting Datasette in immutable mode"
exec uv run datasette serve --host 0.0.0.0 --port 8001 \
    --metadata /app/metadata.json \
    --plugins-dir /app/plugins \
    --cors \
    --immutable \
    $(ls /data/*.db)
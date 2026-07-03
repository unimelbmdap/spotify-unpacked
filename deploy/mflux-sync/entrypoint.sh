#!/bin/sh
# Continuously mirror /data/donations into Mediaflux with one-shot uploads.
# Each cycle is a full server-side compare (idempotent + backfills existing files).
set -eu

# Validate required config up front and exit with a clear message if missing.
# (With restart: unless-stopped this crash-loops with logs naming the missing
#  var, rather than silently running with bad config.)
: "${MFLUX_TOKEN:?MFLUX_TOKEN is required (secure identity token)}"
: "${MFLUX_DEST_PARENT:?MFLUX_DEST_PARENT is required (parent collection path)}"
: "${MFLUX_SCAN_INTERVAL:=300}"

echo "mflux-sync: /data/donations -> ${MFLUX_DEST_PARENT}/donations every ${MFLUX_SCAN_INTERVAL}s"

while true; do
  # MFLUX_HOST/PORT/TRANSPORT/TOKEN are read from the environment by the client.
  # Never pass --sync-delete-assets: this worker is upload-only, local bundles
  # are the durable copy and must never be deleted from Mediaflux.
  java -cp /opt/mf.jar unimelb.mf.client.sync.cli.MFUpload \
    --dest "$MFLUX_DEST_PARENT" --create-parents --csum-check --nb-workers 2 \
    /data/donations \
    || echo "mflux-sync: upload cycle failed; retrying in ${MFLUX_SCAN_INTERVAL}s"
  sleep "$MFLUX_SCAN_INTERVAL"
done

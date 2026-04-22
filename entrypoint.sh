#!/bin/sh
# API entrypoint. Training/ingest are handled by the separate "trainer" service
# in docker-compose.yml, which writes to the shared model-data and processed-data
# volumes before the API is allowed to start.
#
# As a safety net for environments that run this image standalone (without the
# trainer service), we still invoke train.sh — it's idempotent and will be a
# near-instant no-op when weights and processed CSVs are already present.
set -e

./train.sh

exec "$@"

#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-only
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel)
IMAGE=${AGENT_BRAID_T013_IMAGE:-agent-braid-t013:py312-git247-v1}
CONTEXT=$(mktemp -d "${TMPDIR:-/tmp}/agent-braid-t013-build.XXXXXX")
trap 'rm -rf "$CONTEXT"' EXIT HUP INT TERM

cp "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR/apt-packages.lock" \
    "$SCRIPT_DIR/constraints-t013.txt" "$CONTEXT/"
cp "$ROOT/requirements-dev.txt" "$ROOT/requirements-speckit.txt" "$CONTEXT/"

docker build --pull=false --network=default --platform=linux/arm64 --tag "$IMAGE" \
    --label "org.agent-braid.t013.base=python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9" \
    --file "$CONTEXT/Dockerfile" "$CONTEXT"

docker image inspect "$IMAGE" \
    --format 'image={{.Id}} platform={{.Os}}/{{.Architecture}}'
docker run --rm --network=none --entrypoint python "$IMAGE" -c \
    'import json, platform, sys; print(json.dumps({"python": sys.version.split()[0], "platform": platform.platform()}, sort_keys=True))'

#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-only
set -eu

usage() {
    echo "usage: $0 quick|pr|t013 [artifact-directory]" >&2
    exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
MODE=$1
case "$MODE" in quick|pr|t013) ;; *) usage ;; esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel)
COMMON_GIT_DIR=$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)
IMAGE=${AGENT_BRAID_T013_IMAGE:-agent-braid-t013:py312-git247-v1}
UID_VALUE=$(id -u)
GID_VALUE=$(id -g)

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "Docker image '$IMAGE' is missing; run scripts/docker/t013/build-image.sh first." >&2
    exit 2
fi

ARTIFACTS=
CREATED_ARTIFACTS=false
if [ "$MODE" = t013 ]; then
    if [ "$#" -eq 2 ]; then
        ARTIFACTS=$(mkdir -p "$2" && CDPATH= cd -- "$2" && pwd)
    else
        ARTIFACTS=$(mktemp -d "${TMPDIR:-/tmp}/agent-braid-t013-artifacts.XXXXXX")
        CREATED_ARTIFACTS=true
    fi
fi

set -- docker run --rm --network=none --read-only \
    --memory=2g --cpus=2 --pids-limit=512 \
    --cap-drop=ALL --security-opt=no-new-privileges \
    --user "$UID_VALUE:$GID_VALUE" \
    --tmpfs /tmp:rw,nosuid,nodev,size=512m,mode=1777 \
    --mount "type=bind,src=$ROOT,dst=$ROOT,readonly" \
    --mount "type=bind,src=$COMMON_GIT_DIR,dst=$COMMON_GIT_DIR,readonly" \
    --workdir "$ROOT" \
    --env HOME=/tmp/home \
    --env TMPDIR=/tmp \
    --env GIT_OPTIONAL_LOCKS=0 \
    --env GIT_CONFIG_COUNT=1 \
    --env GIT_CONFIG_KEY_0=safe.directory \
    --env "GIT_CONFIG_VALUE_0=$ROOT" \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --env PYTHONWARNINGS=error::ResourceWarning

if [ "$MODE" = t013 ]; then
    set -- "$@" --mount "type=bind,src=$ARTIFACTS,dst=/artifacts"
fi

set -- "$@" "$IMAGE" /bin/sh -eu -c
case "$MODE" in
    quick|pr)
        COMMAND="mkdir -p /tmp/home; exec python scripts/validate_change.py --base develop --profile $MODE"
        ;;
    t013)
        COMMAND="mkdir -p /tmp/home; python scripts/docker/t013/verify-resource-profile.py; PYTHONPATH=$ROOT PYTHONWARNINGS=error::ResourceWarning python -m unittest -v tests.test_git_integration_prototype; exec python scripts/run_git_integration_benchmark.py --output /artifacts/t013-benchmark.json"
        ;;
esac
set -- "$@" "$COMMAND"

echo "Docker image: $IMAGE"
echo "Checkout (read-only): $ROOT"
echo "Common Git directory (read-only): $COMMON_GIT_DIR"
echo "Network: disabled; memory: 2 GiB; CPU: 2; pids: 512 Linux tasks"
if [ "$MODE" = t013 ]; then
    echo "T013 artifacts: $ARTIFACTS/t013-benchmark.json"
fi

"$@"

if [ "$MODE" = t013 ] && [ "$CREATED_ARTIFACTS" = true ]; then
    echo "Artifacts retained at: $ARTIFACTS"
fi

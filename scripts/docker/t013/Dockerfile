# SPDX-License-Identifier: AGPL-3.0-only
# Pinned local validation runtime for the T013 Linux resource profile.
FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9

ARG DEBIAN_FRONTEND=noninteractive

LABEL org.opencontainers.image.title="Agent Braid T013 validation runtime" \
      org.opencontainers.image.description="Offline runtime for bounded T013 resource validation"

COPY apt-packages.lock constraints-t013.txt requirements-dev.txt requirements-speckit.txt /tmp/requirements/

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        $(tr '\n' ' ' < /tmp/requirements/apt-packages.lock) \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m pip install --no-cache-dir \
        -c /tmp/requirements/constraints-t013.txt \
        -r /tmp/requirements/requirements-dev.txt \
        -r /tmp/requirements/requirements-speckit.txt \
    && python -m pip check \
    && git --version \
    && python --version \
    && python -c "from importlib.metadata import version; print('jsonschema', version('jsonschema')); print('specify-cli', version('specify-cli'))" \
    && rm -rf /tmp/requirements

WORKDIR /workspace

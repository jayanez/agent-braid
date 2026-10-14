# SPDX-License-Identifier: AGPL-3.0-only
FROM docker.io/library/python@sha256:739ba32ae445e8d58f3d90feb85f83bebc8346f8dd280fa1eb5848f4ff1ed163
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
COPY requirements-cpu-linux-arm64-py312.lock /tmp/requirements-cpu-linux-arm64-py312.lock
RUN python -m pip install --no-cache-dir --require-hashes --no-deps -r /tmp/requirements-cpu-linux-arm64-py312.lock
COPY agent_braid-0.1.0a1-py3-none-any.whl /tmp/agent_braid-0.1.0a1-py3-none-any.whl
RUN python -m pip install --no-deps --no-index --disable-pip-version-check /tmp/agent_braid-0.1.0a1-py3-none-any.whl && rm -f /tmp/*.whl /tmp/requirements-cpu-linux-arm64-py312.lock
RUN mkdir -p /opt/agent-braid
COPY requirements-cpu-linux-arm64-py312.lock /opt/agent-braid/requirements-cpu.lock
ENTRYPOINT ["python", "-I", "-m", "agent_braid.forecast_worker_entry"]

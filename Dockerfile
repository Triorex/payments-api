# payments-api: multi-stage build on Chainguard (Wolfi) images.
# Builder has pip and a shell; the runtime image has neither, runs as nonroot (65532),
# and ships near-zero known CVEs. Bases are pinned by digest; Dependabot (docker) updates them.

FROM cgr.dev/chainguard/python:latest-dev@sha256:88d8715285b78746679a86fa126fe01e68b7940c3299ee3b4cf8245d4b17095f AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN python -m venv /app/venv
COPY requirements.txt .
# --require-hashes: every package must match the hash in the lock, or the build fails.
RUN /app/venv/bin/pip install --require-hashes --no-deps -r requirements.txt \
 && /app/venv/bin/pip uninstall --yes pip
# The runtime never installs packages, so pip (and the setuptools code it vendors) is removed:
# Trivy flagged CVE-2025-47273 in pip's vendored setuptools; not shipping a package manager fixes the class.

FROM cgr.dev/chainguard/python:latest@sha256:d914788ef74519450a69bc5cce6a1cc747dbefb95a3d431daa4ff707767fea8a
LABEL org.opencontainers.image.title="payments-api" \
      org.opencontainers.image.vendor="Triorex" \
      org.opencontainers.image.licenses="MIT"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/venv/bin:$PATH"
WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY app/ ./app/
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-server-header", "--proxy-headers"]

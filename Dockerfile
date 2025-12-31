ARG PYTHON_VERSION=3.13.11
FROM python:${PYTHON_VERSION}-slim-trixie AS builder

# hadolint ignore=DL3008,DL4006
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     ca-certificates tzdata && update-ca-certificates \
     curl \
  && curl -LsSf https://astral.sh/uv/install.sh | sh \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY flower /flower/flower
# setup tooling files required to install /flower
COPY pyproject.toml /flower/pyproject.toml

# setup expects README.md and the requirements directory to be beside it
COPY README.md /flower/README.mkdir

# Install the required packages
RUN /root/.local/bin/uv pip install . --system --no-cache-dir

# Install the frontend Python package from the prebuilt wheel.
# The wheel is expected to be created by scripts/update_frontend.sh before `docker build`.
COPY frontend/dist/*.whl /tmp/frontend-wheels/
RUN uv pip install --no-cache-dir /tmp/frontend-wheels/*.whl \
    && uv pip install --no-cache-dir /flower

# PYTHONUNBUFFERED: Force stdin, stdout and stderr to be totally unbuffered. (equivalent to `python -u`)
# PYTHONHASHSEED: Enable hash randomization (equivalent to `python -R`)
# PYTHONDONTWRITEBYTECODE: Do not write byte files to disk, since we maintain it as readonly. (equivalent to `python -B`)
ENV PYTHONUNBUFFERED=1 PYTHONHASHSEED=random PYTHONDONTWRITEBYTECODE=1

# Default port
EXPOSE 5555

ENV FLOWER_DATA_DIR=/data
ENV PYTHONPATH=${FLOWER_DATA_DIR}

WORKDIR $FLOWER_DATA_DIR

# Add a user with an explicit UID/GID and create necessary directories
RUN set -eux; \
    groupadd -g 1000 flower; \
    useradd -u 1000 -g flower -m -s /usr/sbin/nologin flower; \
    mkdir -p "$FLOWER_DATA_DIR"; \
    chown flower:flower "$FLOWER_DATA_DIR"
USER flower

VOLUME $FLOWER_DATA_DIR

CMD ["celery", "flower"]

# Stage 1: Builder
FROM python:3.12-slim AS builder

# Install build dependencies (e.g., for packages like psycopg2 or numpy)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Create wheels for all requirements
COPY requirements/default.txt ./requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# Build flower as a wheel
COPY . .
RUN pip wheel --wheel-dir /build/wheels .

# Stage 2: Runtime
FROM python:3.12-alpine

# Get latest root certificates and update openssl to fix vulnerabilities
RUN apk add --no-cache ca-certificates tzdata && \
    apk upgrade --no-cache openssl && \
    update-ca-certificates

# Copy wheels from the builder stage
COPY --from=builder /build/wheels /wheels
# COPY --from=builder /build/requirements.txt .

# Install the required packages
RUN pip install --no-cache-dir redis /wheels/flower-*

# PYTHONUNBUFFERED: Force stdin, stdout and stderr to be totally unbuffered. (equivalent to `python -u`)
# PYTHONHASHSEED: Enable hash randomization (equivalent to `python -R`)
# PYTHONDONTWRITEBYTECODE: Do not write byte files to disk, since we maintain it as readonly. (equivalent to `python -B`)
ENV PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    FLOWER_DATA_DIR=/data
ENV PYTHONPATH=${FLOWER_DATA_DIR}

WORKDIR $FLOWER_DATA_DIR

# Add a user with an explicit UID/GID and create necessary directories
RUN set -eux; \
    addgroup -g 1000 flower; \
    adduser -u 1000 -G flower flower -D; \
    mkdir -p "$FLOWER_DATA_DIR"; \
    chown flower:flower "$FLOWER_DATA_DIR"
USER flower

VOLUME $FLOWER_DATA_DIR

# Default port
EXPOSE 5555

CMD ["celery", "flower"]

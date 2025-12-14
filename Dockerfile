ARG PYTHON_VERSION=3.13.11
FROM python:${PYTHON_VERSION}-slim-trixie AS builder

# Get latest root certificates
RUN apt-get update && apt-get install -y ca-certificates tzdata && update-ca-certificates

COPY flower /flower/flower
# setup tooling files required to install /flower
COPY setup.py /flower/setup.py
COPY setup.cfg /flower/setup.cfg
COPY MANIFEST.in /flower/MANIFEST.in
# setup.py expects README.rst and the requirements directory to be beside it
COPY README.rst /flower/README.rst
COPY requirements/ /flower/requirements/

# Install the required packages
RUN pip install --no-cache-dir -r /flower/requirements/default.txt \
    && pip install --no-cache-dir /flower

# PYTHONUNBUFFERED: Force stdin, stdout and stderr to be totally unbuffered. (equivalent to `python -u`)
# PYTHONHASHSEED: Enable hash randomization (equivalent to `python -R`)
# PYTHONDONTWRITEBYTECODE: Do not write byte files to disk, since we maintain it as readonly. (equivalent to `python -B`)
ENV PYTHONUNBUFFERED=1 PYTHONHASHSEED=random PYTHONDONTWRITEBYTECODE=1

# Default port
EXPOSE 5555

ENV FLOWER_DATA_DIR /data
ENV PYTHONPATH ${FLOWER_DATA_DIR}

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

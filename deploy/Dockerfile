FROM public.ecr.aws/docker/library/python:3.12

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONPATH="/workspace/flower"


RUN apt-get update && \
    apt-get install -y git libgl1 libglib2.0-0 gcc wget python3-magic ffmpeg && \
    apt-get autoremove


RUN mkdir -p -m 0600 ~/.ssh && \
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts

COPY ./requirements/default.txt /tmp/requirements.txt

RUN --mount=type=ssh \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    pip install py-spy && \
    rm -rf ~/.cache/pip && \
    rm /tmp/requirements.txt && \
    mkdir -p /var/log/api/ && \
    mkdir -p /var/log/nacos/

COPY ./deploy/entrypoint.sh /workspace/entrypoint.sh
ADD . /workspace/flower

WORKDIR /workspace
RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

FROM python:3.11-slim-bookworm

ARG NSDDOS_IMAGE_PROFILE=base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NSDDOS_IMAGE_PROFILE=${NSDDOS_IMAGE_PROFILE}

WORKDIR /opt/nsddos

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    default-jre-headless \
    iproute2 \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --upgrade pip setuptools wheel && pip install -e . --no-build-isolation

CMD ["nsddos", "health"]


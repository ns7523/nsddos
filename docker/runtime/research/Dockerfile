FROM nsddos-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    jq \
    procps \
    && rm -rf /var/lib/apt/lists/*

CMD ["nsddos", "runtime", "export-environment"]


FROM nsddos-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    && rm -rf /var/lib/apt/lists/*

CMD ["nsddos", "doctor", "--deep"]


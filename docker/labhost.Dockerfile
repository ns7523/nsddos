FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        iproute2 \
        iputils-ping \
        mininet \
        net-tools \
        openvswitch-switch \
        procps \
        python3 \
    && rm -rf /var/lib/apt/lists/*

COPY labhost-entrypoint.sh /usr/local/bin/labhost-entrypoint.sh
COPY labhost-mininet.py /usr/local/bin/labhost-mininet.py

RUN chmod +x /usr/local/bin/labhost-entrypoint.sh /usr/local/bin/labhost-mininet.py

CMD ["/usr/local/bin/labhost-entrypoint.sh"]

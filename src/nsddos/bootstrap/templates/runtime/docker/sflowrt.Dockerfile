FROM eclipse-temurin:8-jre

WORKDIR /opt/nsddos

COPY external/sflowrt/start.sh /opt/nsddos/start.sh
COPY external/sflowrt/lib /opt/nsddos/lib
COPY external/sflowrt/app /opt/nsddos/app
COPY external/sflowrt/resources /opt/nsddos/resources
COPY external/sflowrt/store /opt/nsddos-seed/store
COPY docker/sflowrt-entrypoint.sh /usr/local/bin/sflowrt-entrypoint.sh

RUN chmod +x /opt/nsddos/start.sh /usr/local/bin/sflowrt-entrypoint.sh \
    && mkdir -p /var/lib/nsddos/sflowrt

CMD ["/usr/local/bin/sflowrt-entrypoint.sh"]

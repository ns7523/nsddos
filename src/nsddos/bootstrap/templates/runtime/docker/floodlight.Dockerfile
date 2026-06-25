FROM eclipse-temurin:8-jre

WORKDIR /opt/floodlight

COPY external/floodlight/floodlight.jar /opt/floodlight/floodlight.jar
COPY external/floodlight/logback.xml /opt/floodlight/logback.xml
COPY external/floodlight/floodlightdefault.properties /opt/floodlight/floodlightdefault.properties

RUN mkdir -p /var/lib/nsddos/floodlight

CMD ["java", "-Dlogback.configurationFile=/opt/floodlight/logback.xml", "-jar", "/opt/floodlight/floodlight.jar", "-cf", "/opt/floodlight/floodlightdefault.properties"]

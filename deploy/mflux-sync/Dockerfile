# syntax=docker/dockerfile:1.7

# ---------- Build unimelb-mf-clients from pinned, checksum-verified source ----------
FROM maven:3-eclipse-temurin-17 AS build
ARG MF_CLIENTS_VERSION=0.8.6
ARG MF_CLIENTS_SHA256=5b56894439950f8a4b41e847ce38d3f42c35127eb827ad6f443e7895291c211b
WORKDIR /build
ADD https://gitlab.unimelb.edu.au/resplat-mediaflux/unimelb-mf-clients/-/archive/v${MF_CLIENTS_VERSION}/unimelb-mf-clients-v${MF_CLIENTS_VERSION}.tar.gz src.tgz
RUN echo "${MF_CLIENTS_SHA256}  src.tgz" | sha256sum -c - \
 && tar xzf src.tgz --strip-components=1 \
 && mvn -q -DskipTests -P platform-packages package

# ---------- Runtime: JRE + the self-contained client jar + loop entrypoint ----------
FROM eclipse-temurin:17-jre
ARG MF_CLIENTS_VERSION=0.8.6
# The -jar-with-dependencies.jar is byte-identical (verified, same sha256) to the
# distribution lib/unimelb-mf-clients.jar used in the successful manual upload.
COPY --from=build /build/target/unimelb-mf-clients-${MF_CLIENTS_VERSION}-jar-with-dependencies.jar /opt/mf.jar
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Connection defaults (token + dest come from the environment / .env).
ENV MFLUX_HOST=mediaflux.researchsoftware.unimelb.edu.au \
    MFLUX_PORT=443 \
    MFLUX_TRANSPORT=https \
    MFLUX_SCAN_INTERVAL=300
ENTRYPOINT ["/entrypoint.sh"]

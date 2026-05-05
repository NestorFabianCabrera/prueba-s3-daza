FROM nginx:alpine AS final
ARG BUILD_DATE
ARG VERSION=1.0
LABEL org.opencontainers.image.title="pulseboard-proxy" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

COPY infra/dockerfiles/proxy/proxy.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

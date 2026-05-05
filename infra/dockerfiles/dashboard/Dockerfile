FROM nginx:alpine AS final
ARG BUILD_DATE
ARG VERSION=1.0
LABEL org.opencontainers.image.title="pulseboard-dashboard" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

COPY infra/dockerfiles/dashboard/nginx.conf /etc/nginx/conf.d/default.conf
COPY servicios/dashboard/ /usr/share/nginx/html/
EXPOSE 80

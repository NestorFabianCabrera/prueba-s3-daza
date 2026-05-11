FROM nginx:alpine

LABEL org.opencontainers.image.title="pulseboard/dashboard" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.created="2025-05-08"

COPY servicios/dashboard/ /usr/share/nginx/html/
COPY infra/servicios/dashboard/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1/"]

CMD ["nginx", "-g", "daemon off;"]

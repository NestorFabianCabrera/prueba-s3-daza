FROM nginx:alpine

LABEL org.opencontainers.image.title="pulseboard/proxy" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.created="2025-05-08"

COPY infra/servicios/proxy/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1/nginx-health"]

CMD ["nginx", "-g", "daemon off;"]

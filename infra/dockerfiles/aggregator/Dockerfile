FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /build
COPY servicios/aggregator/requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS final
ARG BUILD_DATE
ARG VERSION=1.0
LABEL org.opencontainers.image.title="pulseboard-aggregator" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /install /usr/local
RUN useradd --no-create-home --shell /sbin/nologin appuser
COPY infra/dockerfiles/aggregator/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
COPY servicios/aggregator/ .
USER appuser
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "aggregator.py"]

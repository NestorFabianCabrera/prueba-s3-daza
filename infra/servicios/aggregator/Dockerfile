FROM python:3.12-slim AS builder

WORKDIR /build
COPY servicios/aggregator/requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="pulseboard/aggregator" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.created="2025-05-08"

WORKDIR /app

RUN groupadd -r app && useradd -r -g app appuser

COPY --from=builder /install /usr/local
COPY servicios/aggregator/ .
COPY infra/servicios/entrypoint.sh /entrypoint.sh

RUN chown -R appuser:app /app && \
    chmod +x /entrypoint.sh

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "aggregator.py"]

FROM python:3.12-slim AS builder

WORKDIR /build
COPY servicios/query-api/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="pulseboard/query-api" \
      org.opencontainers.image.version="1.0" \
      org.opencontainers.image.created="2025-05-08"

WORKDIR /app

RUN groupadd -r app && useradd -r -g app appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY servicios/query-api/ .
COPY infra/servicios/entrypoint.sh /entrypoint.sh

RUN chown -R appuser:app /app /home/appuser/.local && \
    chmod +x /entrypoint.sh

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/health')"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "wsgi:app"]

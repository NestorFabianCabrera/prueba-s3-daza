FROM python:3.12-slim AS build

WORKDIR /app

COPY requirements.txt .

RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.title = "alerter"
LABEL org.opencontainers.image.version = "1.0.0"
LABEL org.opencontainers.image.created = "today"

WORKDIR /app

COPY --from=build /install /usr/local

RUN useradd -r -s /bin/false appuser

USER appuser

COPY . .

CMD ["python3", "alerter.py"]
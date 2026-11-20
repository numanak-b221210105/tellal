FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TELLAL_DATA_DIR=/data

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --create-home appuser && mkdir -p /data && chown appuser /data
USER appuser
VOLUME /data

EXPOSE 8300
CMD ["uvicorn", "tellal.api:app", "--host", "0.0.0.0", "--port", "8300"]

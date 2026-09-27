FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system smartbiz && adduser --system --ingroup smartbiz smartbiz

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install .

RUN mkdir -p /app/data && chown -R smartbiz:smartbiz /app

USER smartbiz

EXPOSE 8000

CMD ["uvicorn", "smartbiz.main:app", "--host", "0.0.0.0", "--port", "8000"]

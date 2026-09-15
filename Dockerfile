FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY static ./static

USER appuser
EXPOSE 8000

CMD ["gunicorn", "backend.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-"]

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py engine.py ./

RUN useradd --uid 10001 --create-home dream-sla
USER 10001:10001
EXPOSE 8070

CMD ["gunicorn", "--bind", "0.0.0.0:8070", "--workers", "1", "--threads", "4", "--timeout", "30", "app:app"]

FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web_order_app.py .
COPY templates ./templates
COPY static ./static

EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "web_order_app:app", "--workers", "2", "--threads", "4", "--timeout", "120"]

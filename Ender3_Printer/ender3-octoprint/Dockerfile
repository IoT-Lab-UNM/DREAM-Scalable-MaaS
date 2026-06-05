FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY octoprint_client.py /app/octoprint_client.py
COPY gcode /app/gcode

CMD ["python", "/app/octoprint_client.py"]

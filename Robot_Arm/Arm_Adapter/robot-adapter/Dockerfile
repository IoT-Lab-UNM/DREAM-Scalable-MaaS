FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
RUN mkdir -p /data && useradd --system --uid 10001 adapter && chown -R adapter:adapter /data
USER 10001
CMD ["python", "-u", "adapter.py"]


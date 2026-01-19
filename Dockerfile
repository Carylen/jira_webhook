FROM python:3.11-slim

WORKDIR /app

# System deps (often needed for mysql client libs / building wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy your code
COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 9000

# If your FastAPI app object is in main.py as `app`
# and it’s importable as `main:app`, keep as below.
# If your file is src/main/main.py, see note below.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]

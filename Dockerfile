FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# Install requirements (handles CPU-only PyTorch and all dependencies)
RUN pip install -r requirements.txt

COPY . .

# Convert Windows CRLF line endings to Unix LF and make entrypoint.sh executable
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 5000

ENV PYTHONUNBUFFERED=1

CMD ["/app/entrypoint.sh"]
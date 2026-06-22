#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Gunicorn server for health checks..."
# Start Gunicorn in the background
gunicorn --workers 4 --timeout 120 --bind 0.0.0.0:5000 app:app &

echo "Starting AI detection RabbitMQ worker..."
# Execute the AI worker in the foreground to keep container active and stream logs
exec python ai_worker.py

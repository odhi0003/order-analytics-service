
#!/bin/sh
set -e

# Start the RabbitMQ consumer and Flask API
# together in a single Gunicorn worker process.
exec gunicorn \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    'wsgi:app'


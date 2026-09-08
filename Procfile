web: python manage.py collectstatic --noinput && gunicorn dataMarketplace.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
worker: celery -A dataMarketplace worker --loglevel=info
beat: celery -A dataMarketplace beat --loglevel=info
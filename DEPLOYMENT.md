# ASGI deployment

This project exposes its production ASGI application at:

```text
dataMarketplace.asgi:application
```

## Deploy command

The included `Procfile` starts Gunicorn with Uvicorn workers:

```text
gunicorn dataMarketplace.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0:$PORT
```

Set these environment variables on the deployment platform:

- `SECRET_KEY`: a long, random production secret
- `DEBUG=False`
- `ALLOWED_HOSTS`: comma-separated production hostnames
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`: production PostgreSQL settings
- `PAYSTACK_SECRET_KEY` and `PAYSTACK_PUBLIC_KEY`: payment credentials when payments are enabled

Run the release tasks before starting the web process:

```text
python manage.py migrate
python manage.py collectstatic --noinput
```

For a local ASGI smoke test, run:

```text
uvicorn dataMarketplace.asgi:application --reload
```
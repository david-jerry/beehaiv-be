release: pip list; 
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker src:app
worker: REMAP_SIGTERM=SIGQUIT celery -A src.celery_tasks.celery_app worker --loglevel=INFO -E
beat: REMAP_SIGTERM=SIGQUIT celery -A src.celery_tasks.celery_app beat --loglevel=INFO -E

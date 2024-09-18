web: uvicorn src:app --port 8000
worker: REMAP_SIGTERM=SIGQUIT celery -A src.celery_tasks.celery_app worker --loglevel=INFO -E
beat: REMAP_SIGTERM=SIGQUIT celery -A src.celery_tasks.celery_app beat --loglevel=INFO -E
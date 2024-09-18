web: uvicorn src:app --host 0.0.0.0
worker: REMAP_SIGTERM=SIGQUIT celery -A src.celery_tasks.celery_app worker -l INFO -E
beat: REMAP_SIGTERM=SIGQUIT celery -A src.celery_tasks.celery_app beat -l INFO -E
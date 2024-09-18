@echo off

rem Function to check if Redis is running
:check_redis
    if not "%errorlevel%"=="0" (
        echo Redis is not running. Starting Redis...
        start redis-server /wait
    ) else (
        echo Redis is already running.
        call start_celery
    )
goto :eof

rem Function to start Celery
:start_celery
    echo Starting Celery...
    start celery -A src.celery_tasks.celery_app worker -E --loglevel=info /wait
goto :eof

rem Function to start celery flower
:start_celery_flower
    echo Starting Celery flower...
    start celery -A src.celery_tasks.celery_app flower /wait
goto :eof

rem Function to start FastAPI server
:start_fastapi
    echo Starting FastAPI server...
    start pipenv shell /wait
    start pipenv install /wait
    @REM start uvicorn your_app:app --host 0.0.0.0 --port 8000 /wait
    start fastapi dev /wait
goto :eof

rem Function to start Mailpit
:start_mailpit
    echo Starting Mailpit...
    start .\mailpit\mailpit.exe /wait
goto :eof

rem Execute functions
call check_redis
call start_celery
call start_celery_flower
call start_fastapi
call start_mailpit

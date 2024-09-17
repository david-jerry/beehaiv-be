#!/bin/bash

# Function to kill all background processes
cleanup() {
    echo "Terminating all background processes..."
    # Kill all background processes started by this script
    kill $(jobs -p)
    wait
}

# Trap SIGINT (Ctrl+C) and call cleanup function
trap cleanup SIGINT

# Set ENVIRONMENT variable
ENVIRONMENT="${ENVIRONMENT:-'production'}"

# Function to check if a service is running on a specific port
is_service_running() {
    local port=$1
    nc -z localhost "$port" >/dev/null 2>&1
    return $? # Returns 0 if running, non-zero if not
}

# Function to prompt for a new port if the current port is in use
get_available_port() {
    local default_port=$1
    local service_name=$2
    while is_service_running "$default_port"; do
        echo "$service_name is running on port $default_port. Please enter a new port number:"
        read -r new_port
        if [[ ! "$new_port" =~ ^[0-9]+$ ]]; then
            echo "Invalid input. Please enter a valid port number."
        else
            default_port=$new_port
        fi
    done
    echo "$default_port"
}

# Function to start Redis if it's not running
check_and_start_redis() {
    echo "Checking Redis status..."
    if ! is_service_running 6379; then
        echo "Redis is not running. Starting Redis..."
        redis-server &  # Start Redis server
        sleep 5  # Wait for Redis to start
        if is_service_running 6379; then
            echo "Redis started successfully."
        else
            echo "Failed to start Redis. Please check Redis configuration."
            exit 1
        fi
    else
        echo "Redis is already running."
    fi
}

# Function to start Celery
start_celery() {
    echo "Starting Celery..."
    celery -A src.celery_tasks.celery_app worker -l INFO -E &
    sleep 5  # Wait for Celery to start
}

# Function to start Celery Flower
# start_celery_flower() {
#     local default_port=5555
#     local port
#     port=$(get_available_port "$default_port" "Celery Flower")
#     echo "Starting Celery Flower on port $port..."
#     celery -A src.celery_tasks.celery_app flower --port="$port" &
#     sleep 5  # Wait for Celery Flower to start
# }
start_celery_beat() {
    echo "Starting Celery flower..."
    # Replace `your_project_name` with the appropriate path to your Celery app
    celery -A src.celery_tasks.celery_app beat --port=5555 &
    sleep 5  # Wait for Celery Flower to start
}


start_celery_flower() {
    echo "Starting Celery flower..."
    # Replace `your_project_name` with the appropriate path to your Celery app
    celery -A src.celery_tasks.celery_app flower --port=5551 --l INFO -E &
    sleep 5  # Wait for Celery Flower to start
}


# Function to check if PostgreSQL database exists and create it if it does not
check_postgres_db() {
    local db_name=$1
    echo "Checking if PostgreSQL database '$db_name' exists..."
    if psql -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
        echo "Database $db_name exists."
    else
        echo "Database $db_name does not exist. Creating it..."
        createdb "$db_name"
    fi
}


# Function to start FastAPI server
start_fastapi() {
    local default_port=8000
    local port
    port=$(get_available_port "$default_port" "FastAPI")
    echo "Starting FastAPI server on port $port..."
    uvicorn src:app --host 0.0.0.0 --port "$port" --reload &
}

# Function to start Mailpit
start_mailpit() {
    echo "Starting Mailpit..."
    ./mailpit/mailpit.exe --smtp-auth-accept-any &
    sleep 5  # Wait for Mailpit to start
}

# Main function to execute the startup process
main() {
    echo "Activating Pipenv environment..."
    pipenv shell || { echo "Failed to activate Pipenv shell."; }


    check_and_start_redis
    check_postgres_db "beehaiv"
    start_celery
    start_celery_flower
    start_fastapi

    if [[ "$ENVIRONMENT" == "local" ]]; then
        # Start mailpit server if ENVIRONMENT is local
        start_mailpit &
    else
        echo "ENVIRONMENT is in production mode. Skipping Mailpit server start."
    fi
}

# Run the main function
main

# Wait for all background processes to finish
wait

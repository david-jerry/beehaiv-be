#!/bin/bash

if [[ ! -f "Pipfile.lock" ]]; then
    echo "Pipfile.lock not found. Installing dependencies..."
    pipenv install  # Install all dependencies
else
    echo "Pipfile.lock found. Ensuring environment is up-to-date..."
    pipenv sync  # Sync environment with Pipfile.lock
fi

#!/bin/bash

# Script to run the tests for the FastAPI application

# Check if GOOGLE_APPLICATION_CREDENTIALS is set
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    if [ -f .env ]; then
        source .env
    fi
    
    if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo "WARNING: GOOGLE_APPLICATION_CREDENTIALS is not set."
        echo "Tests will run with mocked Firestore client."
    fi
fi

# Run the tests
echo "Running tests..."
pytest -v
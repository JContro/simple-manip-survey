#!/bin/bash

# Script to run the FastAPI application locally

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please update the .env file with your actual values."
    exit 1
fi

# Check if GOOGLE_APPLICATION_CREDENTIALS is set
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    source .env
    if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo "ERROR: GOOGLE_APPLICATION_CREDENTIALS is not set."
        echo "Please set it in your .env file or export it in your shell."
        exit 1
    fi
fi

# Check if the credentials file exists
if [ ! -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "ERROR: Credentials file not found at $GOOGLE_APPLICATION_CREDENTIALS"
    exit 1
fi

# Run the application
echo "Starting FastAPI application..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
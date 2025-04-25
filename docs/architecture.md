# Email Collection Service Architecture

This document outlines the architecture and implementation details for a simple FastAPI application designed to collect emails and store them in Google Cloud Firestore. The application is containerized using Docker, deployed on Google Cloud Run using Terraform for Infrastructure as Code, and utilizes GitHub Actions for CI/CD.

## 1. Project Structure

```
simple-manip-survey/
├── .github/
│   └── workflows/
│       └── ci-cd.yml         # GitHub Actions workflow for CI/CD
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point and API endpoints
│   └── services/
│       └── firestore.py      # Firestore database service for email operations
├── iac/
│   └── terraform/
│       ├── main.tf           # Main Terraform configuration
│       ├── variables.tf      # Terraform variables
│       ├── outputs.tf        # Terraform outputs
│       └── backend.tf        # Terraform backend configuration
├── docs/
│   └── architecture.md       # This architecture document
├── static/                   # Static files (CSS, JS)
├── templates/                # HTML templates
├── tests/                    # Test files
├── .gitignore                # Git ignore file
├── Dockerfile                # Docker configuration for the application
├── docker-compose.yml        # Docker Compose for local development
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

## 2. FastAPI Application Components

### 2.1 Main Application (`app/main.py`)

- FastAPI application setup.
- Serves the main HTML page (`/`).
- Includes endpoints for:
    - Writing and reading test data (`/write_test_data`, `/read_test_data`).
    - Saving emails to Firestore (`/save_email`).
    - Retrieving all saved emails from Firestore (`/emails`).
- Utilizes `app.services.firestore` for database interactions.

### 2.2 Firestore Service (`app/services/firestore.py`)

- Initializes and provides a Firestore client, supporting both production and emulator environments.
- Contains functions for:
    - Saving a new email to the "emails" collection (`save_email`).
    - Checking if an email already exists in the "emails" collection (`email_exists`).
    - Retrieving all documents from the "emails" collection (`get_emails`).
- Includes basic error handling for database operations.

## 3. Docker Configuration

### 3.1 Dockerfile

- Defines the steps to build a Docker image for the FastAPI application.
- Copies application code and dependencies.
- Sets up the necessary environment to run the FastAPI application.

### 3.2 Docker Compose (for local development)

- Configures the FastAPI service.
- Can be extended to include a Firestore emulator for local testing.
- Maps volumes for local code changes to be reflected in the container.

## 4. Terraform Infrastructure as Code

### 4.1 Main Configuration (`iac/terraform/main.tf`)

- Configures the Google Cloud provider.
- Enables necessary GCP APIs (Cloud Run, Artifact Registry, Firestore, Secret Manager).
- Creates a Firestore database instance.
- Defines and configures the Google Cloud Run service for deploying the application container.
- Grants the Cloud Run service account necessary permissions (e.g., Firestore access).

### 4.2 Variables (`iac/terraform/variables.tf`)

- Defines input variables for the Terraform configuration, such as:
    - GCP project ID and region.
    - Firestore location.
    - Cloud Run service name and container image.
    - Service account email.
    - Firestore collection name (defaults to "users", but used for "emails" in the application).

### 4.3 Outputs (`iac/terraform/outputs.tf`)

- Defines output values from the Terraform deployment, such as the Cloud Run service URL.

### 4.4 Backend Configuration (`iac/terraform/backend.tf`)

- Configures the backend for storing Terraform state (e.g., in a GCS bucket).

## 5. CI/CD Pipeline with GitHub Actions

### 5.1 Workflow Configuration (`.github/workflows/ci-cd.yml`)

- Defines the automated workflow triggered by events like pushes to the main branch.
- Includes jobs for:
    - Running application tests.
    - Building and pushing the Docker image to Google Cloud Artifact Registry.
    - Validating and applying the Terraform configuration to provision/update infrastructure.
    - Deploying the new container image to the Cloud Run service.

## 6. Data Storage

- **Firestore**: Used as the primary database to store collected emails in a collection named "emails".

## 7. Deployment

- The application is deployed as a containerized service on Google Cloud Run, managed by Terraform.

## 8. Local Development Environment

- Docker Compose can be used to run the application and potentially a Firestore emulator locally for development and testing.

## 9. API Endpoints

- `GET /`: Serves the main HTML page.
- `POST /write_test_data`: Writes a test document to Firestore.
- `GET /read_test_data`: Reads the test document from Firestore.
- `POST /save_email`: Receives an email and saves it to Firestore.
- `GET /emails`: Retrieves all saved emails from Firestore.

## 10. Architecture Diagram

```mermaid
graph TD
    subgraph "GitHub Repository"
        A[Source Code] --> B[GitHub Actions]
    end

    subgraph "CI/CD Pipeline"
        B --> C[Test]
        C --> D[Build Docker Image]
        D --> E[Push to Artifact Registry]
        E --> F[Terraform Apply]
        F --> G[Deploy to Cloud Run]
    end

    subgraph "Google Cloud Platform"
        G --> H[Cloud Run Service]
        H --> I[Firestore Database]
        J[IAM & Auth] --> H
        J --> I
        K[Artifact Registry] --> H
        L[Cloud Storage] --> M[Terraform State]
    end

    subgraph "Client Applications"
        Q[Web Browser/API Clients] --> H
    end
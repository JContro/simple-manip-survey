# Email Collection Service

A simple FastAPI application with Docker containerization for collecting emails and storing them in Firestore.

## Features

- FastAPI REST API for email collection
- Firestore database integration
- Docker containerization
- Google Cloud Run deployment (configured via Terraform)
- Terraform Infrastructure as Code
- GitHub Actions CI/CD pipeline

## Project Structure

The project follows a modular structure:

- `app/`: Application code
  - `main.py`: FastAPI application entry point and API endpoints
  - `services/firestore.py`: Firestore database service for email operations
- `iac/`: Infrastructure as Code
  - `terraform/`: Terraform configuration for GCP resources
- `docs/`: Documentation
- `static/`: Static files (CSS, JS)
- `templates/`: HTML templates
- `tests/`: Test files

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Google Cloud SDK
- Terraform
- A Google Cloud Platform account with a configured project

## Local Development

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd simple-manip-survey
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables (refer to `.env.example`):

```bash
# Example:
export GCP_PROJECT_ID="your-gcp-project-id"
export FIRESTORE_EMULATOR_HOST="localhost:8080" # For local development with emulator
```

### Running the Application

#### Using Python directly:

```bash
uvicorn app.main:app --reload
```

#### Using Docker Compose:

```bash
docker-compose up --build
```

The application will be available at http://localhost:8000.

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Running Tests

```bash
pytest
```

## Deployment

### Using Terraform

1. Navigate to the Terraform directory:

```bash
cd iac/terraform
```

2. Initialize Terraform:

```bash
terraform init
```

3. Plan the deployment:

```bash
terraform plan
```

4. Apply the changes:

```bash
terraform apply
```

### Using GitHub Actions

The CI/CD pipeline is automatically triggered when changes are pushed to the main branch. It performs the following steps:

1. Run tests
2. Build and push the Docker image to Artifact Registry
3. Apply Terraform changes to provision/update infrastructure
4. Deploy the application to Cloud Run

## API Endpoints

- `GET /`: Serves the main HTML page.
- `POST /write_test_data`: Writes a test document to Firestore.
- `GET /read_test_data`: Reads the test document from Firestore.
- `POST /save_email`: Receives an email and saves it to Firestore.
- `GET /emails`: Retrieves all saved emails from Firestore.

## License

[MIT](LICENSE)
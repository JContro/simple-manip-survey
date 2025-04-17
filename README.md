# User Management API

A FastAPI application with Docker containerization for deployment on Google Cloud Run. The application establishes a connection to Firestore, ensuring proper database and collection initialization. It includes JWT-based authentication, error handling, logging, and monitoring.

## Features

- FastAPI REST API with CRUD operations for user management
- JWT-based authentication
- Firestore database integration
- Docker containerization
- Google Cloud Run deployment
- Terraform Infrastructure as Code
- GitHub Actions CI/CD pipeline
- Comprehensive testing

## Project Structure

The project follows a modular structure:

- `app/`: Application code
  - `core/`: Core functionality (config, security, exceptions)
  - `models/`: Pydantic models
  - `routers/`: API routes
  - `services/`: Business logic and external services
- `iac/`: Infrastructure as Code
  - `terraform/`: Terraform configuration
- `tests/`: Test files
- `docs/`: Documentation

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

3. Set up environment variables:

```bash
export SECRET_KEY="your-secret-key"
export GCP_PROJECT_ID="simple-manip-survey-250416"
export GOOGLE_APPLICATION_CREDENTIALS="./iac/service-account-key.json"
```

### Running the Application

#### Using Python directly:

```bash
uvicorn app.main:app --reload
```

#### Using Docker Compose:

```bash
docker-compose up
```

The API will be available at http://localhost:8000.

API documentation is available at:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Running Tests

```bash
pytest
```

## Deployment

### Manual Deployment

1. Build the Docker image:

```bash
docker build -t gcr.io/simple-manip-survey-250416/user-api:latest .
```

2. Push the image to Google Container Registry:

```bash
docker push gcr.io/simple-manip-survey-250416/user-api:latest
```

3. Deploy to Cloud Run:

```bash
gcloud run deploy user-api \
  --image gcr.io/simple-manip-survey-250416/user-api:latest \
  --platform managed \
  --region europe-west2 \
  --allow-unauthenticated
```

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
2. Build and push the Docker image
3. Apply Terraform changes
4. Deploy to Cloud Run

## API Endpoints

### Authentication

- `POST /api/v1/auth/register`: Register a new user
- `POST /api/v1/auth/login`: Login and get access token
- `GET /api/v1/auth/me`: Get current user information

### Users

- `GET /api/v1/users`: List all users (protected)
- `GET /api/v1/users/{user_id}`: Get a specific user (protected)
- `POST /api/v1/users`: Create a new user
- `PUT /api/v1/users/{user_id}`: Update a user (protected)
- `DELETE /api/v1/users/{user_id}`: Delete a user (protected)

## License

[MIT](LICENSE)
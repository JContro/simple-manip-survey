# Configure the Terraform backend to store state in a GCS bucket
terraform {
  backend "gcs" {
    bucket = "simple-manip-survey-250416-terraform-state"
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }

  required_version = ">= 1.0.0"
}

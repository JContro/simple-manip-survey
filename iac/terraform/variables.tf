# Project variables
variable "project_id" {
  description = "The GCP project ID"
  type        = string
  default     = "simple-manip-survey-250416"
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "europe-west2"
}

variable "firestore_location" {
  description = "The location for the Firestore database"
  type        = string
  default     = "europe-west2"
}

# Service variables
variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "user-api"
}

variable "container_image" {
  description = "The container image to deploy"
  type        = string
  default     = "gcr.io/simple-manip-survey-250416/user-api:latest"
}

variable "service_account_email" {
  description = "The service account email for the Cloud Run service"
  type        = string
  default     = "service-account@simple-manip-survey-250416.iam.gserviceaccount.com"
}

# Application variables
variable "firestore_collection" {
  description = "The Firestore collection name for users"
  type        = string
  default     = "users"
}

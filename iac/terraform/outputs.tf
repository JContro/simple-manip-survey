# Output the URL of the deployed Cloud Run service
output "service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.api.status[0].url
}

# Output the Firestore database details
output "firestore_database" {
  description = "The Firestore database details"
  value       = google_firestore_database.database.name
}

# Output the project ID
output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

# Output the region
output "region" {
  description = "The GCP region"
  value       = var.region
}

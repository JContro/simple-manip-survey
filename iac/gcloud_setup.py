#!/usr/bin/env python3

import os
import subprocess
import argparse
import json
import time
import base64
import requests
import sys
from nacl import encoding, public
from datetime import datetime

def run_command(command, error_msg="Command failed", exit_on_error=True):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(command, shell=True, check=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {error_msg}")
        print(f"Command: {command}")
        print(f"Error details: {e.stderr}")
        if exit_on_error:
            exit(1)
        else:
            return None

def get_billing_accounts():
    """Get list of available billing accounts."""
    print("Fetching available billing accounts...")
    result = run_command(
        "gcloud billing accounts list --format='json'", 
        "Failed to list billing accounts", 
        exit_on_error=False
    )
    
    if not result:
        return []
    
    try:
        accounts = json.loads(result)
        return accounts
    except json.JSONDecodeError:
        print("Failed to parse billing accounts")
        return []

def encrypt(public_key, secret_value):
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def set_github_secret(repo_owner, repo_name, secret_name, secret_value, token):
    """Set a GitHub repository secret."""
    print(f"Setting GitHub secret '{secret_name}'...")
    # Get public key details
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/public-key"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    public_key_data = response.json()
    public_key = public_key_data["key"]
    key_id = public_key_data["key_id"]
    
    # Encrypt the secret
    encrypted_value = encrypt(public_key, secret_value)
    
    # Create or update the secret
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"
    payload = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return response.status_code

def set_github_variable(repo_owner, repo_name, variable_name, variable_value, token):
    """Set a GitHub repository variable."""
    print(f"Setting GitHub variable '{variable_name}'...")
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/variables"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # First check if variable already exists
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    existing_vars = response.json().get("variables", [])
    var_exists = any(var["name"] == variable_name for var in existing_vars)
    
    if var_exists:
        # Update existing variable
        update_url = f"{url}/{variable_name}"
        response = requests.patch(update_url, headers=headers, json={"value": variable_value})
    else:
        # Create new variable
        payload = {
            "name": variable_name,
            "value": variable_value
        }
        response = requests.post(url, headers=headers, json=payload)
    
    response.raise_for_status()
    return response.status_code

def setup_gcp_project():
    """Setup a new GCP project with service account and configure GitHub."""
    parser = argparse.ArgumentParser(description="Set up a new GCP project with a service account and configure GitHub.")
    parser.add_argument("--project-name", required=True, help="Name for the new GCP project")
    parser.add_argument("--service-account-name", default="service-account", 
                        help="Name for the service account (default: service-account)")
    parser.add_argument("--billing-account", help="Billing account ID to link to the project")
    parser.add_argument("--region", default="europe-west2", help="GCP region for resources (default: eu-west2)")
    parser.add_argument("--list-billing-accounts", action="store_true", 
                        help="List available billing accounts and exit")
    parser.add_argument("--github-token", help="GitHub Personal Access Token")
    parser.add_argument("--github-repo", help="GitHub repository in format 'owner/repo'")
    
    args = parser.parse_args()

    # Just list billing accounts if requested
    if args.list_billing_accounts:
        accounts = get_billing_accounts()
        if accounts:
            print("\nAvailable billing accounts:")
            for account in accounts:
                print(f"ID: {account.get('name', '').split('/')[-1]}")
                print(f"  Name: {account.get('displayName', 'N/A')}")
                print(f"  Open: {account.get('open', False)}")
                print()
        else:
            print("No billing accounts found or insufficient permissions.")
        sys.exit(0)

    # Get GitHub token from environment or argument
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN")
    github_repo = args.github_repo or os.environ.get("GITHUB_REPOSITORY")
    
    # Generate a project ID from project name (lowercase with hyphens)
    timestamp = datetime.now().strftime("%y%m%d")
    project_id = f"{args.project_name.lower().replace(' ', '-')}-{timestamp}"
    
    print(f"\n--- Setting up GCP Project: {args.project_name} (ID: {project_id}) ---\n")

    # Check if gcloud is installed and authenticated
    print("Checking gcloud configuration...")
    run_command("gcloud --version | head -n 1", "gcloud CLI not found")
    
    print("Checking authentication...")
    account_info = run_command("gcloud auth list --filter=status:ACTIVE --format='value(account)'", 
                              "No authenticated gcloud account found")
    print(f"Using account: {account_info}")
    
    # Create a new project
    print(f"\nCreating new project: {project_id}...")
    run_command(f"gcloud projects create {project_id} --name=\"{args.project_name}\"",
               f"Failed to create project {project_id}")
    
    # Set as the active project
    print(f"Setting {project_id} as the active project...")
    run_command(f"gcloud config set project {project_id}",
               f"Failed to set {project_id} as active project")
    
    # Handle billing account setup
    billing_account = args.billing_account
    
    if not billing_account:
        accounts = get_billing_accounts()
        if accounts:
            print("\nAvailable billing accounts:")
            for i, account in enumerate(accounts, 1):
                account_id = account.get('name', '').split('/')[-1]
                account_name = account.get('displayName', 'N/A')
                print(f"{i}. {account_name} (ID: {account_id})")
            
            print("\nNOTE: A billing account is required to enable APIs and create resources.")
            choice = input("\nEnter the number of the billing account to use (or press Enter to skip for now): ")
            
            if choice.strip():
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(accounts):
                        billing_account = accounts[index].get('name', '').split('/')[-1]
                        print(f"Selected billing account: {billing_account}")
                    else:
                        print("Invalid selection. Continuing without billing account.")
                except ValueError:
                    print("Invalid input. Continuing without billing account.")
        else:
            print("\nNo billing accounts found or you don't have permission to access them.")
            print("You will need to link a billing account manually after project creation.")
    
    # Set up billing if we have an account
    if billing_account:
        print(f"Linking billing account {billing_account} to project...")
        run_command(f"gcloud billing projects link {project_id} --billing-account={billing_account}",
                   "Failed to link billing account")
    else:
        print("\nWARNING: No billing account linked. Many operations will fail.")
        print("To link a billing account later, run:")
        print(f"gcloud billing projects link {project_id} --billing-account=YOUR_BILLING_ACCOUNT_ID")
        proceed = input("\nDo you want to continue without a billing account? (y/n): ")
        if proceed.lower() != 'y':
            print("Exiting. Please run again with a valid billing account.")
            sys.exit(0)
    
    # Create service account
    sa_name = args.service_account_name
    sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"
    print(f"\nCreating service account: {sa_name}...")
    run_command(f"gcloud iam service-accounts create {sa_name} --display-name=\"{sa_name}\"",
               f"Failed to create service account {sa_name}")
    
    # Wait for service account to be fully created
    print("Waiting for service account to be fully created...")
    time.sleep(5)  # Give GCP a moment to process
    
    # Grant editor role to service account
    print(f"Granting editor role to service account {sa_email}...")
    run_command(f"gcloud projects add-iam-policy-binding {project_id} "
                f"--member=serviceAccount:{sa_email} --role=roles/editor",
                "Failed to grant editor role to service account")
    
    # Grant specific roles for GitHub Actions
    print(f"Granting specific roles to service account {sa_email}...")
    for role in ["roles/artifactregistry.admin", "roles/run.admin", "roles/storage.admin"]:
        run_command(f"gcloud projects add-iam-policy-binding {project_id} "
                    f"--member=serviceAccount:{sa_email} --role={role}",
                    f"Failed to grant {role} to service account")
    
    repository_name = ""
    bucket_name = ""
    
    # Only proceed with API enablement and resource creation if billing is set up
    if billing_account:
        # Enable required APIs
        print("\nEnabling required GCP APIs...")
        required_apis = [
            "artifactregistry.googleapis.com",
            "run.googleapis.com",
            "storage.googleapis.com",
            "containerregistry.googleapis.com",
            "iam.googleapis.com"
        ]
        for api in required_apis:
            print(f"Enabling {api}...")
            run_command(f"gcloud services enable {api} --project={project_id}",
                       f"Failed to enable {api}")
        
        # Create Artifact Registry repository
        repository_name = f"{project_id}-repo"
        print(f"\nCreating Artifact Registry repository: {repository_name}...")
        run_command(f"gcloud artifacts repositories create {repository_name} "
                    f"--repository-format=docker --location={args.region} --project={project_id}",
                    "Failed to create Artifact Registry repository")
        
        # Create GCS bucket for Terraform state
        bucket_name = f"{project_id}-terraform-state"
        print(f"\nCreating GCS bucket for Terraform state: {bucket_name}...")
        run_command(f"gsutil mb -l {args.region} gs://{bucket_name}",
                   f"Failed to create GCS bucket {bucket_name}")
        run_command(f"gsutil versioning set on gs://{bucket_name}",
                   f"Failed to enable versioning on bucket {bucket_name}")
    else:
        print("\nSkipping API enablement and resource creation because no billing account is linked.")
    
    # Create and download key for service account
    key_file = f"{sa_name}-key.json"
    print(f"\nCreating and downloading key for service account to {key_file}...")
    run_command(f"gcloud iam service-accounts keys create {key_file} --iam-account={sa_email}",
               "Failed to create and download service account key")
    
    # Read the service account key content for GitHub setup
    try:
        with open(key_file, 'r') as f:
            sa_key_content = f.read()
    except:
        print(f"Warning: Could not read the service account key file {key_file}")
        sa_key_content = ""
    
    print("\n--- GCP Project Setup Complete! ---")
    print(f"Project ID: {project_id}")
    print(f"Service Account: {sa_email}")
    print(f"Key File: {os.path.abspath(key_file)}")
    
    if billing_account:
        print(f"Artifact Registry: {repository_name}")
        print(f"Terraform State Bucket: {bucket_name}")
    
    # GitHub integration
    if github_token and github_repo:
        print(f"\n--- Setting up GitHub repository: {github_repo} ---")
        
        try:
            repo_owner, repo_name = github_repo.split("/", 1)
            
            # Define the GitHub variables to set
            github_variables = {
                "GCP_PROJECT_ID": project_id,
                "GCP_REGION": args.region
            }
            
            if billing_account and repository_name:
                github_variables["GCP_ARTIFACT_REGISTRY"] = repository_name
            
            if billing_account and bucket_name:
                github_variables["GCP_BUCKET"] = bucket_name
            
            # Set GitHub variables
            for var_name, var_value in github_variables.items():
                try:
                    status = set_github_variable(repo_owner, repo_name, var_name, var_value, github_token)
                    print(f"✅ Variable '{var_name}' set successfully (Status: {status})")
                except Exception as e:
                    print(f"❌ Failed to set variable '{var_name}': {str(e)}")
            
            # Set GitHub secret for service account key
            try:
                if sa_key_content:
                    status = set_github_secret(repo_owner, repo_name, "GCP_SA_KEY", sa_key_content, github_token)
                    print(f"✅ Secret 'GCP_SA_KEY' set successfully (Status: {status})")
                else:
                    print("❌ Could not set 'GCP_SA_KEY' secret: Key file content is empty")
            except Exception as e:
                print(f"❌ Failed to set secret 'GCP_SA_KEY': {str(e)}")
            
            print("\n--- GitHub Repository Setup Complete! ---")
        except ValueError:
            print("❌ Error: GitHub repository must be in format 'owner/repo'")
        except Exception as e:
            print(f"❌ Error setting up GitHub repository: {str(e)}")
    else:
        print("\n--- GITHUB SETUP INFORMATION ---")
        print("To configure your GitHub repository, you need to:")
        print("1. Add these as GitHub repository Variables:")
        print(f"   GCP_PROJECT_ID: {project_id}")
        print(f"   GCP_REGION: {args.region}")
        
        if billing_account and repository_name:
            print(f"   GCP_ARTIFACT_REGISTRY: {repository_name}")
        
        if billing_account and bucket_name:
            print(f"   GCP_BUCKET: {bucket_name}")
        
        print("\n2. Add the downloaded service account key as a GitHub Secret named GCP_SA_KEY")
        print("   You can do this manually in your repository settings or use the provided")
        print("   GitHub setup script with your GitHub token and repository.")
    
    print("\nNEXT STEPS:")
    if not billing_account:
        print("1. Link a billing account to your project:")
        print(f"   gcloud billing projects link {project_id} --billing-account=YOUR_BILLING_ACCOUNT_ID")
        print("2. Enable required APIs:")
        print(f"   gcloud services enable artifactregistry.googleapis.com run.googleapis.com storage.googleapis.com --project={project_id}")
    
    print("\nYour GCP environment is now ready to use!")

if __name__ == "__main__":
    setup_gcp_project()

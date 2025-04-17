#!/usr/bin/env python3

import os
import sys
import base64
import json
import requests
from nacl import encoding, public

def encrypt(public_key, secret_value):
    """Encrypt a Unicode string using the public key."""
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def set_github_secret(repo_owner, repo_name, secret_name, secret_value, token):
    """Set a GitHub repository secret."""
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
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/variables"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "name": variable_name,
        "value": variable_value
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
        response = requests.post(url, headers=headers, json=payload)
    
    response.raise_for_status()
    return response.status_code

def main():
    # Get GitHub token from environment or user input
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        token = input("Enter your GitHub Personal Access Token: ")
    
    # Get repository information
    repo_full_name = input("Enter repository (format: owner/repo): ")
    if "/" not in repo_full_name:
        print("Error: Repository must be in format 'owner/repo'")
        sys.exit(1)
    
    repo_owner, repo_name = repo_full_name.split("/", 1)
    
    # Test values
    test_secret_name = "TEST_SECRET"
    test_secret_value = "this-is-a-test-secret-value"
    test_variable_name = "TEST_VARIABLE"
    test_variable_value = "this-is-a-test-variable-value"
    
    # Set the test secret
    try:
        secret_status = set_github_secret(repo_owner, repo_name, test_secret_name, test_secret_value, token)
        print(f"✅ Secret '{test_secret_name}' set successfully (Status: {secret_status})")
    except Exception as e:
        print(f"❌ Failed to set secret: {str(e)}")
    
    # Set the test variable
    try:
        variable_status = set_github_variable(repo_owner, repo_name, test_variable_name, test_variable_value, token)
        print(f"✅ Variable '{test_variable_name}' set successfully (Status: {variable_status})")
    except Exception as e:
        print(f"❌ Failed to set variable: {str(e)}")

if __name__ == "__main__":
    main()

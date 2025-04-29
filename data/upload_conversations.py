import json
import requests
import os

# Define the API endpoint URL
# Assuming the FastAPI app is running locally on port 8000
# API_URL = "http://localhost:8000/conversations"
API_URL = "https://user-api-274208077023.europe-west2.run.app/conversations"
CONVERSATIONS_FILE = "conversations.json"
ERROR_CONVERSATIONS_FILE = "error_conversations.json"


def upload_conversations():
    """
    Reads conversations from conversations.json, uploads them to the API,
    and saves failed uploads to error_conversations.json.
    """
    failed_conversations = []

    if not os.path.exists(CONVERSATIONS_FILE):
        print(f"Error: {CONVERSATIONS_FILE} not found.")
        return

    with open(CONVERSATIONS_FILE, 'r') as f:
        try:
            conversations = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {CONVERSATIONS_FILE}.")
            return

    print(f"Attempting to upload {len(conversations)} conversations...")

    for i, conversation in enumerate(conversations):

        try:
            response = requests.post(API_URL, json=conversation)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            print(
                f"Successfully uploaded conversation {i+1}/{len(conversations)}")
        except requests.exceptions.RequestException as e:
            print(
                f"Failed to upload conversation {i+1}/{len(conversations)}: {e}")
            failed_conversations.append(conversation)

    if failed_conversations:
        print(
            f"Saving {len(failed_conversations)} failed conversations to {ERROR_CONVERSATIONS_FILE}")
        with open(ERROR_CONVERSATIONS_FILE, 'w') as f:
            json.dump(failed_conversations, f, indent=4)
    else:
        print("All conversations uploaded successfully.")


if __name__ == "__main__":
    upload_conversations()

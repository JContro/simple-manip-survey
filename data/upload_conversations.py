import json
import requests
import datetime

def upload_conversations(file_path="conversations.json", url="http://localhost:8000/conversations"):
    """
    Reads a JSON file and uploads its content via a POST request.

    Args:
        file_path (str): The path to the JSON file.
        url (str): The URL to send the POST request to.
    """
    try:
        with open(file_path, 'r') as f:
            conversations_list = json.load(f)

        headers = {'Content-Type': 'application/json'}
        
        successful_uploads = 0
        error_conversations = []

        for conversation in conversations_list:
            # Convert timestamp string to integer Unix timestamp
            timestamp_str = conversation.get('timestamp')
            if timestamp_str:
                try:
                    # Handle potential variations in timestamp format
                    if '.' in timestamp_str:
                         # Handle timestamps with microseconds
                        dt_object = datetime.datetime.fromisoformat(timestamp_str)
                    else:
                        # Handle timestamps without microseconds
                        dt_object = datetime.datetime.fromisoformat(timestamp_str + ".0") # Add .0 for consistent parsing
                    conversation['timestamp'] = int(dt_object.timestamp())
                except ValueError as e:
                    print(f"Error converting timestamp for conversation with uuid: {conversation.get('uuid', 'N/A')}: {e}")
                    error_conversations.append(conversation)
                    continue # Skip to the next conversation if timestamp conversion fails
            else:
                print(f"Warning: Timestamp missing for conversation with uuid: {conversation.get('uuid', 'N/A')}")
                # Decide how to handle missing timestamps - either skip or assign a default
                # For now, let's add it to error_conversations
                error_conversations.append(conversation)
                continue


            try:
                response = requests.post(url, json=conversation, headers=headers)
                response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
                print(f"Successfully uploaded conversation with uuid: {conversation.get('uuid', 'N/A')}. Status Code: {response.status_code}")
                successful_uploads += 1
            except requests.exceptions.RequestException as e:
                print(f"Error uploading conversation with uuid: {conversation.get('uuid', 'N/A')}: {e}")
                error_conversations.append(conversation)
            except Exception as e:
                print(f"An unexpected error occurred for conversation with uuid: {conversation.get('uuid', 'N/A')}: {e}")
                error_conversations.append(conversation)

        if error_conversations:
            error_file_path = "error_conversations.json"
            with open(error_file_path, 'w') as f:
                json.dump(error_conversations, f, indent=4)
            print(f"Saved {len(error_conversations)} faulty conversations to {error_file_path}")

        print(f"\nOperation complete. Successfully uploaded {successful_uploads} conversations.")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Assuming the script is run from the project root or data directory
    # Adjust the file_path if necessary
    upload_conversations(file_path="conversations.json")
import json

def read_conversations(file_path="conversations.json"):
    """Reads conversation data from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            conversations = json.load(f)
        return conversations
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None

conversation_data = read_conversations()

def process_conversation_data(data):
    """Processes conversation data to add 'prompted_as' key."""
    if not data:
        return None
    
    for item in data:
        if isinstance(item, dict):
            if item.get('manipulation_type') is not None:
                item['prompted_as'] = item['manipulation_type']
            elif item.get('persuasion_strength') is not None:
                item['prompted_as'] = item['persuasion_strength']
            else:
                item['prompted_as'] = 'Unknown'
    return data

def assign_batches(data, batch_size=10):
    """Assigns batch numbers to conversations with equal distribution of prompted_as types."""
    if not data:
        return None

    # Group data by prompted_as type
    grouped_data = {}
    for item in data:
        prompted_as_type = item.get('prompted_as', 'Unknown')
        if prompted_as_type not in grouped_data:
            grouped_data[prompted_as_type] = []
        grouped_data[prompted_as_type].append(item)

    # Determine the number of batches needed
    total_conversations = len(data)
    num_batches = (total_conversations + batch_size - 1) // batch_size

    # Initialize batches
    batches = [[] for _ in range(num_batches)]

    # Distribute conversations into batches
    type_indices = {type: 0 for type in grouped_data.keys()}
    batch_index = 0

    while any(type_indices[type] < len(grouped_data[type]) for type in grouped_data.keys()):
        for type in grouped_data.keys():
            if type_indices[type] < len(grouped_data[type]):
                batches[batch_index].append(grouped_data[type][type_indices[type]])
                grouped_data[type][type_indices[type]]['batch'] = batch_index + 1
                type_indices[type] += 1
                if len(batches[batch_index]) == batch_size:
                    batch_index = (batch_index + 1) % num_batches # Move to the next batch, wrap around if necessary

    # Flatten the batches back into a single list
    batched_data = [item for batch in batches for item in batch]

    return batched_data


def get_batch_statistics(batched_data, num_batches=5):
    """Calculates and prints prompted_as aggregate counts for the first num_batches."""
    if not batched_data:
        print("No batched data available for statistics.")
        return

    batch_stats = {}
    for item in batched_data:
        batch_num = item.get('batch')
        prompted_as_type = item.get('prompted_as', 'Unknown')

        if batch_num is not None and batch_num <= num_batches:
            if batch_num not in batch_stats:
                batch_stats[batch_num] = {}
            if prompted_as_type not in batch_stats[batch_num]:
                batch_stats[batch_num][prompted_as_type] = 0
            batch_stats[batch_num][prompted_as_type] += 1

    for batch_num in sorted(batch_stats.keys()):
        print(f"\nStatistics for Batch {batch_num}:")
        for prompted_as_type, count in batch_stats[batch_num].items():
            print(f"  {prompted_as_type}: {count}")


if conversation_data:
    modified_data_with_prompted_as = process_conversation_data(conversation_data)
    if modified_data_with_prompted_as:
        batched_data = assign_batches(modified_data_with_prompted_as)
        if batched_data:
            get_batch_statistics(batched_data, num_batches=5)
            try:
                with open("conversations.json", 'w') as f:
                    json.dump(batched_data, f, indent=4)
                print("\nModified data with batches saved to conversations.json")
            except IOError:
                print(f"Error: Could not write to data/conversations.json")
        else:
            print("Could not assign batches to data.")
    else:
        print("Could not process conversation data.")
else:
    print("Could not load conversation data.")

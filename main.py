import os
import base64
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load the .env file to get the API key
load_dotenv()

# Retrieve the API_KEY
api_key = os.getenv("API_KEY")

processed_count = 0
total_images = 2

# Function to encode the image to base64
def encode_image(filename):
    with open(filename, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to append a description to a JSON file
def append_to_json_file(description_data, json_file_path):
    try:
        # Load existing data from the file or create a new list if the file doesn't exist
        if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
            with open(json_file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            data = []

        # Append the new data
        data.append(description_data)

        # Save the updated data back to the file
        with open(json_file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)  # Added indentation for better readability

        print("Description appended to JSON file.")
    except json.JSONDecodeError as e:
        # Handle empty file or file with invalid JSON by starting fresh
        print(f"JSON decode error - starting a new file: {e}")
        with open(json_file_path, 'w') as json_file:
            json.dump([description_data], json_file, indent=4)  # Start with the first entry
    except Exception as e:
        print(f"An error occurred while writing to JSON file: {e}")

# Function to send the image to the OpenAI API and get the description
def get_image_description(base64_image, image_name, json_file_path):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Format the base64 string as a data URI
    data_uri = f"data:image/png;base64,{base64_image}"

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Give a detailed description of the info from this textbook page. Format it as well."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_uri
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1024
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    
    # Debug: Print the status and content of the response
    print(f"Status Code: {response.status_code}")
    print(f"Response Content: {response.text}")
    
    description_text(response.json(), image_name, json_file_path)

def description_text(response_data, image_name, json_file_path):
    global processed_count
    # Extracts and appends the description to the JSON file
    if 'choices' in response_data and response_data['choices']:
        processed_count += 1
        first_choice = response_data['choices'][0]      
        if 'message' in first_choice and 'content' in first_choice['message']:
            content_text = first_choice['message']['content']
            description_data = {"image": image_name, "description": content_text}
            append_to_json_file(description_data, json_file_path)
        else:
            print("The 'message' or 'content' key is missing in the first choice.")
    else:
        print("The 'choices' key is missing in the response or is empty.")
        processed_count += 1
    if processed_count == total_images:
        print(f"All {total_images} descriptions have been added. Starting cleanse process.")
        cleanse_descriptions(api_key, json_file_path)
        
# Iterate over each image file in the specified directory and process them
def process_images_in_folder(folder_path, json_file_path):
    for image_file in Path(folder_path).glob('*.png'):  # Adjust the file type if needed
        print(f"Processing image: {image_file.name}")
        base64_image = encode_image(image_file)
        get_image_description(base64_image, image_file.name, json_file_path)

# Function to clean and rewrite descriptions in the JSON file
def cleanse_descriptions(api_key, json_file_path):
    try:
        # Load the descriptions from the JSON file
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

        # Go through each description, clean it, and update in place
        for entry in data:
            cleansed_description = clean_text(api_key, entry["description"])
            entry["description"] = cleansed_description

        # Write the cleansed data back to the JSON file
        with open(json_file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        print("Descriptions cleansed and JSON file rewritten.")
    except Exception as e:
        print(f"An error occurred during cleansing: {e}")

def clean_text(description):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    prompt = f"Rewrite the following text to clean it up and improve readability:\n\n{description}"

    payload = {
        "model": "text-davinci-003",
        "prompt": prompt,
        "max_tokens": 1024
    }

    response = requests.post("https://api.openai.com/v1/engines/text-davinci-003/completions", headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()['choices'][0]['text'].strip()
    else:
        raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")





# Specify the folder path and the JSON file path
folder_path = './chapter5'
json_file_path = './descriptions.json'  # Adjust to save in the data folder
process_images_in_folder(folder_path, json_file_path)

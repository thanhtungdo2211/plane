import requests
import json

# API endpoint
workspace_slug = "workspacetdt"
url = f"http://localhost:8000/api/workspaces/{workspace_slug}/add-member/"

# Member data
data = {
    "email": "newuser10@example.com",
    "role": 20
}

# Headers with API key
headers = {
    "Content-Type": "application/json",
    "x-api-key": "plane_api_55017c632ac040c993f6ab73e74eb736"
}

# Make POST request
try:
    response = requests.post(url, headers=headers, json=data)
    
    # Check if request was successful
    if response.status_code in [200, 201]:
        print("Member added successfully!")
        print("Response:", response.json())
    else:
        print(f"Failed to add member. Status code: {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")
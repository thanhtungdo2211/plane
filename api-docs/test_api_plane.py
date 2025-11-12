import requests

url = "http://localhost:8000/api/v1/users/"

headers = {
    "Content-Type": "application/json",
    "x-api-key": "plane_api_2cf250630291427c883bd66f8b5adf10"
}

data = {
    "email": "test@example.com",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User"
}

response = requests.post(url, json=data, headers=headers)
print(response.status_code)
print(response.json())
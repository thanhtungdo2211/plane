import requests

workspace_slug = "workspace-mq"
url = f"http://localhost:8000/api/v1/workspaces/{workspace_slug}/projects/"

headers = {"x-api-key": "plane_api_fe15a1874a304088b027ce4bbe8afc23"}

response = requests.get(url, headers=headers)

print(response.json())
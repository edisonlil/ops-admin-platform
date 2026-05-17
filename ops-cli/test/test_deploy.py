import requests

# Test login
url = "http://192.168.20.121:8000/api/identity-access/user/login"
data = {"account": "admin", "password": "edc3000"}

try:
    response = requests.post(url, json=data, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test frontend
try:
    response = requests.get("http://192.168.20.121:8000/", timeout=10)
    print(f"\nFrontend Status: {response.status_code}")
    print(f"Frontend size: {len(response.text)} bytes")
except Exception as e:
    print(f"Frontend Error: {e}")
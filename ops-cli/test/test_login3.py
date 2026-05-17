import requests

# Test login with form data (application/x-www-form-urlencoded)
url = "http://192.168.20.121:8000/api/auth/token"

# Try form data
try:
    r = requests.post(url, data={"username": "admin", "password": "edc3000"}, timeout=10)
    print(f"Form Login Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Form Login Error: {e}")

# Try with correct content type
try:
    r = requests.post(url, json={"username": "admin", "password": "edc3000"}, headers={"Content-Type": "application/json"}, timeout=10)
    print(f"\nJSON Login Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"JSON Login Error: {e}")
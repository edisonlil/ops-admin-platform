import requests

# Test login with correct field name
url = "http://192.168.20.121:8000/api/auth/token"
data = {"username": "admin", "password": "edc3000"}

try:
    r = requests.post(url, json=data, timeout=10)
    print(f"Login Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
    
    if r.status_code == 200:
        print("\n✅ Login successful!")
        token = r.json().get('data', {}).get('token')
        print(f"Token: {token[:50]}..." if token else "No token")
except Exception as e:
    print(f"Login Error: {e}")

# Test frontend with full path
print("\n--- Frontend Test ---")
try:
    r = requests.get("http://192.168.20.121:8000/", timeout=10)
    print(f"Root: {r.status_code}, size: {len(r.text)}")
    if r.status_code == 200:
        print(f"Content preview: {r.text[:200]}")
except Exception as e:
    print(f"Root Error: {e}")

# Try different frontend paths
for path in ["/index.html", "/app.config.js"]:
    try:
        r = requests.get(f"http://192.168.20.121:8000{path}", timeout=10)
        print(f"{path}: {r.status_code}, size: {len(r.text)}")
    except Exception as e:
        print(f"{path}: Error - {e}")
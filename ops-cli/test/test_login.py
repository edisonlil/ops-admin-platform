import requests

# Test login endpoints
endpoints = [
    "/api/login",
    "/api/auth/token",
    "/api/tenant/users",
]

for ep in endpoints:
    try:
        # Try GET first
        r = requests.get(f"http://192.168.20.121:8000{ep}", timeout=5)
        print(f"GET {ep}: {r.status_code}")
    except Exception as e:
        print(f"GET {ep}: Error - {e}")
    
    try:
        # Try POST
        r = requests.post(f"http://192.168.20.121:8000{ep}", json={"account": "admin", "password": "edc3000"}, timeout=5)
        print(f"POST {ep}: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"POST {ep}: Error - {e}")
    print()

# Test frontend
try:
    r = requests.get("http://192.168.20.121:8000/", timeout=10)
    print(f"Frontend: {r.status_code}, size: {len(r.text)}")
except Exception as e:
    print(f"Frontend Error: {e}")
import urllib.request
import json

BASE_URL = "http://localhost:8000/api/v1"

def make_request(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    
    if data:
        json_data = json.dumps(data).encode("utf-8")
        req.data = json_data
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = json.loads(response.read().decode("utf-8"))
            return status, body
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return e.code, body
    except Exception as e:
        return None, str(e)

def test_health():
    print("Testing health check...")
    status, body = make_request(f"{BASE_URL}/health")
    print(f"Status Code: {status}")
    print(f"Response: {body}")
    return status == 200

def test_signup():
    print("\nTesting signup...")
    payload = {
        "fullName": "Manual Test",
        "email": "manual@test.com",
        "password": "Password123!",
        "company": "Manual Corp",
        "plan": "basic"
    }
    status, body = make_request(f"{BASE_URL}/auth/signup", method="POST", data=payload)
    print(f"Status Code: {status}")
    print(f"Response: {body}")
    return status == 201 or (status == 400 and body.get("detail") == "User with this email already exists")

def test_login():
    print("\nTesting login...")
    payload = {
        "email": "manual@test.com",
        "password": "Password123!"
    }
    status, body = make_request(f"{BASE_URL}/auth/login", method="POST", data=payload)
    print(f"Status Code: {status}")
    print(f"Response: {body}")
    return status == 200

if __name__ == "__main__":
    if test_health():
        signup_ok = test_signup()
        login_ok = test_login()
        
        if signup_ok and login_ok:
            print("\n✅ Backend API verification successful!")
        else:
            print("\n❌ Backend API verification failed.")
    else:
        print("\n❌ Health check failed. Is the server running?")

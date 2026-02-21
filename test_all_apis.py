import urllib.request
import json
import time

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = None
TENANT_ID = None
USER_ID = None

def make_request(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    
    if data:
        json_data = json.dumps(data).encode("utf-8")
        req.data = json_data
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            res_content = response.read().decode("utf-8")
            body = json.loads(res_content) if res_content else {}
            return status, body
    except urllib.error.HTTPError as e:
        res_content = e.read().decode("utf-8")
        body = json.loads(res_content) if res_content else {"detail": str(e)}
        return e.code, body
    except Exception as e:
        return None, str(e)

def test_module(name, path, create_body, update_body):
    print(f"\n--- Testing {name} ---")
    
    # 1. Create
    print(f"Creating {name}...")
    create_body["tenantId"] = TENANT_ID
    status, body = make_request(f"{BASE_URL}/{path}", method="POST", data=create_body)
    if status != 201:
        print(f"❌ Create failed: {status} {body}")
        return None
    obj_id = body["id"]
    print(f"✅ Created with ID: {obj_id}")

    # 2. Get List
    print(f"Getting {name} list...")
    status, body = make_request(f"{BASE_URL}/{path}?tenantId={TENANT_ID}")
    if status != 200:
        print(f"❌ List failed: {status} {body}")
    else:
        print(f"✅ List success (found {len(body)} items)")

    # 3. Get Single
    print(f"Getting single {name}...")
    status, body = make_request(f"{BASE_URL}/{path}/{obj_id}")
    if status != 200:
        print(f"❌ Get failed: {status} {body}")
    else:
        print(f"✅ Get success")

    # 4. Update
    print(f"Updating {name}...")
    update_body["tenantId"] = TENANT_ID
    status, body = make_request(f"{BASE_URL}/{path}/{obj_id}", method="PUT", data=update_body)
    if status != 200:
        print(f"❌ Update failed: {status} {body}")
    else:
        print(f"✅ Update success")

    return obj_id

def delete_module(name, path, obj_id):
    if not obj_id: return
    print(f"Deleting {name} ({obj_id})...")
    status, body = make_request(f"{BASE_URL}/{path}/{obj_id}", method="DELETE")
    if status == 204:
        print(f"✅ Delete success")
    else:
        print(f"❌ Delete failed: {status} {body}")

def run_all_tests():
    global TOKEN, TENANT_ID, USER_ID
    
    # Health
    print("Testing health check...")
    status, body = make_request(f"{BASE_URL}/health")
    if status != 200:
        print("❌ Health check failed. Ensure server is running.")
        return

    # Auth (using existing manual test user)
    print("\n--- Auth Flow ---")
    payload = {"email": "manual@test.com", "password": "Password123!"}
    status, body = make_request(f"{BASE_URL}/auth/login", method="POST", data=payload)
    if status != 200:
        print(f"❌ Login failed: {status} {body}. Attempting signup...")
        signup_payload = {
            "fullName": "Manual Test",
            "email": "manual@test.com",
            "password": "Password123!",
            "company": "Manual Corp",
            "plan": "basic"
        }
        status, body = make_request(f"{BASE_URL}/auth/signup", method="POST", data=signup_payload)
        if status != 201:
            print(f"❌ Signup failed: {status} {body}")
            return
    
    TOKEN = body["accessToken"]
    TENANT_ID = body["user"]["tenantId"]
    USER_ID = body["user"]["id"]
    print(f"✅ Auth successful. Tenant: {TENANT_ID}")

    # Objects
    ids = {}

    # Accounts
    ids['account'] = test_module("Accounts", "accounts", 
        {"name": "Test Account", "industry": "Tech"}, 
        {"name": "Updated Account", "industry": "Finance"})

    # Contacts
    ids['contact'] = test_module("Contacts", "contacts",
        {"firstName": "John", "lastName": "Doe", "accountId": ids['account']},
        {"firstName": "Jane", "lastName": "Doe", "accountId": ids['account']})

    # Leads
    ids['lead'] = test_module("Leads", "leads",
        {"name": "Target Lead", "email": "lead@test.com"},
        {"name": "Qualified Lead", "status": "qualified"})

    # Products
    ids['product'] = test_module("Products", "products",
        {"name": "Premium Tool", "price": 99.99},
        {"name": "Discounted Tool", "price": 79.99})

    # Deals
    ids['deal'] = test_module("Deals", "deals",
        {"title": "Big Deal", "accountId": ids['account'], "contactId": ids['contact'], "value": 5000},
        {"title": "Bigger Deal", "value": 10000})

    # Quotes
    ids['quote'] = test_module("Quotes", "quotes",
        {"number": "QT-001", "dealId": ids['deal'], "amount": 9500, "items": [{"name": "Service", "qty": 1, "price": 9500}]},
        {"number": "QT-001-REV", "amount": 9000})

    # Invoices
    ids['invoice'] = test_module("Invoices", "invoices",
        {"number": "INV-100", "quoteId": ids['quote'], "total": 9000},
        {"number": "INV-100-PAID", "status": "paid"})

    # Orders
    ids['order'] = test_module("Orders", "orders",
        {"number": "ORD-500", "contactId": ids['contact'], "total": 9000},
        {"number": "ORD-500-U", "status": "done"})

    # Tasks
    ids['task'] = test_module("Tasks", "tasks",
        {"title": "Follow up", "priority": "high"},
        {"title": "Followed up", "status": "done"})

    # Campaigns
    ids['campaign'] = test_module("Campaigns", "campaigns",
        {"name": "Spring Sale", "type": "Email"},
        {"name": "Summer Sale", "status": "active"})

    # Plans (Read-only module usually, but check list)
    print("\n--- Testing Plans list ---")
    status, body = make_request(f"{BASE_URL}/plans")
    if status == 200: print(f"✅ Plans List success ({len(body)} plans)")
    else: print(f"❌ Plans List failed: {status}")

    # Users
    print("\n--- Testing Users list ---")
    status, body = make_request(f"{BASE_URL}/users?tenantId={TENANT_ID}")
    if status == 200: print(f"✅ Users List success ({len(body)} users)")
    else: print(f"❌ Users List failed: {status}")

    # Cleanup
    print("\n--- Cleaning up created data ---")
    delete_module("Campaign", "campaigns", ids.get('campaign'))
    delete_module("Task", "tasks", ids.get('task'))
    delete_module("Order", "orders", ids.get('order'))
    delete_module("Invoice", "invoices", ids.get('invoice'))
    delete_module("Quote", "quotes", ids.get('quote'))
    delete_module("Deal", "deals", ids.get('deal'))
    delete_module("Product", "products", ids.get('product'))
    delete_module("Lead", "leads", ids.get('lead'))
    delete_module("Contact", "contacts", ids.get('contact'))
    delete_module("Account", "accounts", ids.get('account'))

    print("\n✅ Exhaustive API verification completed!")

if __name__ == "__main__":
    run_all_tests()

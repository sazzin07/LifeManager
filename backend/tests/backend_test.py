"""Backend API tests for Life Manager."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

if not BASE_URL:
    BASE_URL = "http://localhost:8000"

OWNER_EMAIL = "sa@lifemanager.app"
OWNER_PASSWORD = os.environ.get("ADMIN_PASSWORD", "lifemanager123")
TAG = f"TEST_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and data["user"]["email"] == OWNER_EMAIL
    return data["token"]


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# --- Auth ---
class TestAuth:
    def test_login_ok(self, token):
        assert token and isinstance(token, str)

    def test_login_bad(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": OWNER_EMAIL, "password": "wrong"}, timeout=10)
        assert r.status_code == 401

    def test_me(self, client):
        r = client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == OWNER_EMAIL

    def test_me_unauth(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 401


# --- Basic list endpoints ---
class TestListEndpoints:
    def test_accounts(self, client):
        r = client.get(f"{BASE_URL}/api/accounts")
        assert r.status_code == 200
        accs = r.json()
        ids = {a["id"] for a in accs}
        assert "cash" in ids and "revolut" in ids
        for a in accs:
            assert "balance" in a

    def test_categories(self, client):
        r = client.get(f"{BASE_URL}/api/categories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_people(self, client):
        r = client.get(f"{BASE_URL}/api/people")
        assert r.status_code == 200

    def test_transactions(self, client):
        r = client.get(f"{BASE_URL}/api/transactions")
        assert r.status_code == 200

    def test_analytics(self, client):
        r = client.get(f"{BASE_URL}/api/analytics/summary")
        assert r.status_code == 200
        for k in ["cash", "revolut", "total_available", "gross", "personal",
                  "reimbursable", "owed_to_me", "i_owe", "by_category", "by_day", "months"]:
            assert k in r.json()

    def test_tasks(self, client):
        assert client.get(f"{BASE_URL}/api/tasks").status_code == 200

    def test_weight(self, client):
        assert client.get(f"{BASE_URL}/api/weight").status_code == 200

    def test_groceries(self, client):
        assert client.get(f"{BASE_URL}/api/groceries").status_code == 200

    def test_meals(self, client):
        assert client.get(f"{BASE_URL}/api/meals").status_code == 200


# --- CRUD flows ---
class TestPeopleCRUD:
    def test_create_delete_person(self, client):
        name = f"{TAG}_alice"
        r = client.post(f"{BASE_URL}/api/people", json={"name": name})
        assert r.status_code == 200
        pid = r.json()["id"]
        r2 = client.get(f"{BASE_URL}/api/people")
        assert any(p["id"] == pid for p in r2.json())
        r3 = client.get(f"{BASE_URL}/api/people/{pid}")
        assert r3.status_code == 200
        assert r3.json()["person"]["name"] == name
        assert client.delete(f"{BASE_URL}/api/people/{pid}").status_code == 200


class TestTasks:
    def test_task_lifecycle(self, client):
        title = f"{TAG}_task"
        r = client.post(f"{BASE_URL}/api/tasks", json={"title": title})
        assert r.status_code == 200
        tid = r.json()["id"]
        r2 = client.put(f"{BASE_URL}/api/tasks/{tid}", json={"title": title, "done": True})
        assert r2.status_code == 200
        assert r2.json()["done"] is True
        assert client.delete(f"{BASE_URL}/api/tasks/{tid}").status_code == 200


class TestWeight:
    def test_add_delete_weight(self, client):
        r = client.post(f"{BASE_URL}/api/weight", json={"weight": 82.5, "note": TAG})
        assert r.status_code == 200
        wid = r.json()["id"]
        listing = client.get(f"{BASE_URL}/api/weight").json()
        assert any(w["id"] == wid for w in listing)
        assert client.delete(f"{BASE_URL}/api/weight/{wid}").status_code == 200


class TestGroceries:
    def test_add_delete_grocery(self, client):
        name = f"{TAG}_apple"
        r = client.post(f"{BASE_URL}/api/groceries",
                        json={"name": name, "quantity": 2, "price": 1.5})
        assert r.status_code == 200
        gid = r.json()["id"]
        assert client.delete(f"{BASE_URL}/api/groceries/{gid}").status_code == 200


class TestMeals:
    def test_add_delete_meal(self, client):
        r = client.post(f"{BASE_URL}/api/meals",
                        json={"description": f"{TAG} meal", "calories": 400, "protein": 30})
        assert r.status_code == 200
        mid = r.json()["id"]
        assert client.delete(f"{BASE_URL}/api/meals/{mid}").status_code == 200


# --- Finance: expenses, splits, balances ---
class TestFinance:
    def test_personal_expense_updates_balance(self, client):
        before = client.get(f"{BASE_URL}/api/accounts").json()
        cash_before = next(a["balance"] for a in before if a["id"] == "cash")

        r = client.post(f"{BASE_URL}/api/transactions/expense", json={
            "amount": 12.34, "merchant": f"{TAG}_shop", "category": "Other",
            "account": "cash", "participants": ["Me"], "split_mode": "equal",
        })
        assert r.status_code == 200
        txn = r.json()["transaction"]
        tid = txn["id"]
        assert txn["gross_amount"] == 12.34
        assert txn["personal_amount"] == 12.34
        assert txn["reimbursable_amount"] == 0.0

        after = client.get(f"{BASE_URL}/api/accounts").json()
        cash_after = next(a["balance"] for a in after if a["id"] == "cash")
        assert round(cash_before - cash_after, 2) == 12.34

        txns = client.get(f"{BASE_URL}/api/transactions").json()
        assert any(t["id"] == tid for t in txns)
        client.delete(f"{BASE_URL}/api/transactions/{tid}")

    def test_shared_item_split_and_balance(self, client):
        n1 = f"{TAG}_bob"
        n2 = f"{TAG}_carol"
        p1 = client.post(f"{BASE_URL}/api/people", json={"name": n1}).json()
        p2 = client.post(f"{BASE_URL}/api/people", json={"name": n2}).json()

        payload = {
            "amount": 30.0, "merchant": f"{TAG}_dinner", "category": "Eating Out",
            "account": "revolut",
            "participants": ["Me", n1, n2],
            "split_mode": "items",
            "items": [
                {"name": "Pizza", "price": 20.0, "assigned": ["Me", n1]},
                {"name": "Soda", "price": 10.0, "assigned": [n2]},
            ],
            "paid_by": "Me",
        }
        r = client.post(f"{BASE_URL}/api/transactions/expense", json=payload)
        assert r.status_code == 200, r.text
        txn = r.json()["transaction"]
        shares = {s["person_name"]: s["amount"] for s in txn["splits"]}
        assert shares.get("Me") == 10.0
        assert shares.get(n1) == 10.0
        assert shares.get(n2) == 10.0
        assert txn["personal_amount"] == 10.0
        assert txn["reimbursable_amount"] == 20.0

        people = client.get(f"{BASE_URL}/api/people").json()
        bob = next(p for p in people if p["id"] == p1["id"])
        carol = next(p for p in people if p["id"] == p2["id"])
        assert bob["owes_me"] == 10.0
        assert carol["owes_me"] == 10.0

        s = client.post(f"{BASE_URL}/api/settlements", json={
            "person": n1, "amount": 10.0, "method": "Revolut",
            "account": "revolut", "direction": "in",
        })
        assert s.status_code == 200
        people2 = client.get(f"{BASE_URL}/api/people").json()
        bob2 = next(p for p in people2 if p["id"] == p1["id"])
        assert bob2["owes_me"] == 0.0

        client.delete(f"{BASE_URL}/api/transactions/{txn['id']}")
        client.delete(f"{BASE_URL}/api/people/{p1['id']}")
        client.delete(f"{BASE_URL}/api/people/{p2['id']}")


# --- AI (budget expected to fail without keys) ---
class TestAI:
    def test_ai_history(self, client):
        r = client.get(f"{BASE_URL}/api/ai/history", params={"session_id": "nonexistent"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ai_actions(self, client):
        r = client.get(f"{BASE_URL}/api/ai/actions")
        assert r.status_code == 200

    def test_ai_chat_attempted(self, client):
        r = client.post(f"{BASE_URL}/api/ai/chat", json={"message": "hello"}, timeout=60)
        assert r.status_code in (200, 400, 402, 429, 500, 503), f"unexpected {r.status_code}: {r.text[:200]}"

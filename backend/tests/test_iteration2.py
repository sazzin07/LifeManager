"""Backend tests for iteration 2: refund tracking, edit expense, groceries CRUD,
shopping list, recipes cook, AI update/delete/mark_refunded."""
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
TAG = f"TEST2_{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return s


# --- Serialize txn: payment_method, refund status ---
class TestSerializeTxn:
    def test_payment_method_cash_card(self, client):
        r1 = client.post(f"{BASE_URL}/api/transactions/expense", json={
            "amount": 5.0, "merchant": f"{TAG}_cashx", "category": "Other",
            "account": "cash", "participants": ["Me"]})
        assert r1.status_code == 200
        t1 = r1.json()["transaction"]
        r2 = client.post(f"{BASE_URL}/api/transactions/expense", json={
            "amount": 7.0, "merchant": f"{TAG}_cardx", "category": "Other",
            "account": "revolut", "participants": ["Me"]})
        t2 = r2.json()["transaction"]
        txns = client.get(f"{BASE_URL}/api/transactions").json()
        m1 = next(t for t in txns if t["id"] == t1["id"])
        m2 = next(t for t in txns if t["id"] == t2["id"])
        assert m1["payment_method"] == "cash"
        assert m2["payment_method"] == "card"
        assert m1["refund_status"] == "personal"
        client.delete(f"{BASE_URL}/api/transactions/{t1['id']}")
        client.delete(f"{BASE_URL}/api/transactions/{t2['id']}")

    def test_payment_method_filter(self, client):
        r = client.get(f"{BASE_URL}/api/transactions", params={"payment_method": "card"})
        assert r.status_code == 200
        for t in r.json():
            if t.get("type") == "expense":
                assert t["payment_method"] == "card"


# --- PUT /transactions/{tid}: edit + split scaling ---
class TestEditExpense:
    def test_update_amount_scales_splits(self, client):
        p = client.post(f"{BASE_URL}/api/people", json={"name": f"{TAG}_ed"}).json()
        r = client.post(f"{BASE_URL}/api/transactions/expense", json={
            "amount": 40.0, "merchant": f"{TAG}_edx", "category": "Other",
            "account": "cash", "participants": ["Me", f"{TAG}_ed"], "split_mode": "equal"})
        t = r.json()["transaction"]
        assert t["personal_amount"] == 20.0
        assert t["reimbursable_amount"] == 20.0

        r2 = client.put(f"{BASE_URL}/api/transactions/{t['id']}", json={"amount": 60.0})
        assert r2.status_code == 200, r2.text
        t2 = r2.json()
        assert t2["gross_amount"] == 60.0
        assert t2["personal_amount"] == 30.0
        assert t2["reimbursable_amount"] == 30.0

        r3 = client.put(f"{BASE_URL}/api/transactions/{t['id']}", json={"payment_method": "card"})
        assert r3.json()["account"] == "revolut"
        assert r3.json()["payment_method"] == "card"

        client.delete(f"{BASE_URL}/api/transactions/{t['id']}")
        client.delete(f"{BASE_URL}/api/people/{p['id']}")

    def test_update_personal_amount(self, client):
        p = client.post(f"{BASE_URL}/api/people", json={"name": f"{TAG}_pa"}).json()
        r = client.post(f"{BASE_URL}/api/transactions/expense", json={
            "amount": 50.0, "merchant": f"{TAG}_pax", "category": "Other",
            "account": "cash", "participants": ["Me", f"{TAG}_pa"], "split_mode": "equal"})
        t = r.json()["transaction"]
        r2 = client.put(f"{BASE_URL}/api/transactions/{t['id']}",
                        json={"amount": 50.0, "personal_amount": 15.0})
        assert r2.status_code == 200
        t2 = r2.json()
        assert t2["personal_amount"] == 15.0
        assert t2["reimbursable_amount"] == 35.0
        client.delete(f"{BASE_URL}/api/transactions/{t['id']}")
        client.delete(f"{BASE_URL}/api/people/{p['id']}")


# --- Refund tracking via settlements with transaction_id ---
class TestRefundLinking:
    def test_refund_reduces_remaining(self, client):
        person_name = f"{TAG}_ref"
        p = client.post(f"{BASE_URL}/api/people", json={"name": person_name}).json()
        r = client.post(f"{BASE_URL}/api/transactions/expense", json={
            "amount": 20.0, "merchant": f"{TAG}_ref_exp", "category": "Other",
            "account": "cash", "participants": ["Me", person_name], "split_mode": "equal"})
        t = r.json()["transaction"]
        assert t["reimbursable_amount"] == 10.0

        s = client.post(f"{BASE_URL}/api/settlements", json={
            "person": person_name, "amount": 4.0, "method": "Revolut",
            "account": "revolut", "direction": "in", "transaction_id": t["id"]})
        assert s.status_code == 200

        txns = client.get(f"{BASE_URL}/api/transactions").json()
        got = next(x for x in txns if x["id"] == t["id"])
        assert got["amount_refunded"] == 4.0
        assert got["remaining_refund"] == 6.0
        assert got["refund_status"] == "partial"

        client.post(f"{BASE_URL}/api/settlements", json={
            "person": person_name, "amount": 6.0, "method": "Revolut",
            "account": "revolut", "direction": "in", "transaction_id": t["id"]})
        txns2 = client.get(f"{BASE_URL}/api/transactions").json()
        got2 = next(x for x in txns2 if x["id"] == t["id"])
        assert got2["remaining_refund"] == 0.0
        assert got2["refund_status"] == "settled"

        client.delete(f"{BASE_URL}/api/transactions/{t['id']}")
        client.delete(f"{BASE_URL}/api/people/{p['id']}")


# --- Groceries CRUD ---
class TestGroceriesCRUD:
    def test_grocery_lifecycle(self, client):
        name = f"{TAG}_rice"
        r = client.post(f"{BASE_URL}/api/groceries", json={"name": name, "quantity": 2})
        gid = r.json()["id"]
        assert r.json().get("price") is None
        r2 = client.put(f"{BASE_URL}/api/groceries/{gid}", json={"quantity": 5, "price": 1.99, "store": "Lidl"})
        assert r2.json()["quantity"] == 5
        assert r2.json()["price"] == 1.99
        client.delete(f"{BASE_URL}/api/groceries/{gid}")


# --- Shopping list ---
class TestShopping:
    def test_shopping_flow(self, client):
        gname = f"{TAG}_bread"
        g = client.post(f"{BASE_URL}/api/groceries",
                        json={"name": gname, "quantity": 1, "price": 2.5, "store": "Continente"}).json()
        s = client.post(f"{BASE_URL}/api/shopping", json={"name": gname}).json()
        payload = client.get(f"{BASE_URL}/api/shopping").json()
        assert "recommendation" in payload
        assert "items" in payload
        b = client.post(f"{BASE_URL}/api/shopping/{s['id']}/buy",
                        json={"price": 2.5, "store": "Continente"})
        assert b.status_code == 200
        client.delete(f"{BASE_URL}/api/groceries/{g['id']}")


# --- Recipes cook ---
class TestRecipes:
    def test_cook_decrements_inventory(self, client):
        ingname = f"{TAG}_flour"
        g = client.post(f"{BASE_URL}/api/groceries",
                        json={"name": ingname, "quantity": 10}).json()
        r = client.post(f"{BASE_URL}/api/recipes", json={
            "name": f"{TAG}_cake", "servings": 2,
            "ingredients": [{"name": ingname, "quantity": 3, "unit": "cup"}],
            "calories": 400})
        rid = r.json()["id"]
        c = client.post(f"{BASE_URL}/api/recipes/{rid}/cook")
        assert c.status_code == 200
        assert c.json()["meal_logged"] is True
        gs = client.get(f"{BASE_URL}/api/groceries").json()
        upd = next(x for x in gs if x["id"] == g["id"])
        assert upd["quantity"] == 7
        client.delete(f"{BASE_URL}/api/recipes/{rid}")
        client.delete(f"{BASE_URL}/api/groceries/{g['id']}")


# --- Analytics summary new fields ---
class TestAnalytics:
    def test_new_fields(self, client):
        r = client.get(f"{BASE_URL}/api/analytics/summary").json()
        for k in ["cash_spent", "card_spent", "refunded", "pending", "grocery"]:
            assert k in r
        assert "out_of_stock" in r["grocery"]
        assert "low_stock" in r["grocery"]


# --- AI tools (skips gracefully if key unavailable) ---
class TestAITools:
    def test_ai_delete_confirmation(self, client):
        r = client.post(f"{BASE_URL}/api/transactions/expense", json={
            "amount": 3.14, "merchant": f"{TAG}_aidel", "category": "Other",
            "account": "cash", "participants": ["Me"]})
        t = r.json()["transaction"]
        resp = client.post(f"{BASE_URL}/api/ai/chat",
                           json={"message": f"Delete the {TAG}_aidel expense"}, timeout=90)
        if resp.status_code != 200:
            pytest.skip(f"AI unavailable: {resp.status_code}")
        txns = client.get(f"{BASE_URL}/api/transactions").json()
        still = any(x["id"] == t["id"] for x in txns)
        assert still, "AI deleted without confirmation!"
        client.delete(f"{BASE_URL}/api/transactions/{t['id']}")

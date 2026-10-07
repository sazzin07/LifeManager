from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import json
import logging
import tempfile
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

import jwt
import bcrypt
import httpx
from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends, UploadFile, File, Header, Query, Response
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal, engine
from models import (
    Base, User, Person, Category, Account, Transaction, Split, Settlement,
    Task, WeightEntry, Workout, Photo, Grocery, PriceRecord, ShoppingItem,
    Meal, Recipe, AIAction, AIMessage,
)

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
OWNER_NAME = os.environ.get('OWNER_NAME', 'Sá')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '').strip() or None
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '').strip() or None

UPLOAD_DIR = ROOT_DIR / "uploads"
PHOTOS_DIR = UPLOAD_DIR / "photos"

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_upload_dirs()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed()
    logger.info("Life Manager ready.")
    yield
    await engine.dispose()


app = FastAPI(title="Life Manager", lifespan=lifespan)
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lifemanager")


# ---------------------------------------------------------------------------
# DB session helpers
# ---------------------------------------------------------------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def session_scope():
    """Context manager for helper functions that need their own session."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Local filesystem storage for progress photos
# ---------------------------------------------------------------------------
def ensure_upload_dirs():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return str(uuid.uuid4())


def month_of(date_str: str) -> str:
    return date_str[:7]


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=30), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(request: Request, db=Depends(get_db)) -> dict:
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class LoginBody(BaseModel):
    email: str
    password: str


class PersonBody(BaseModel):
    name: str
    photo: Optional[str] = None
    notes: Optional[str] = ""
    payment_preference: Optional[str] = ""


class CategoryBody(BaseModel):
    name: str
    icon: str = "circle"
    color: str = "#64748B"


class ItemBody(BaseModel):
    name: str
    price: float
    assigned: List[str] = ["Me"]


class ExpenseBody(BaseModel):
    amount: Optional[float] = None
    description: str = ""
    category: str = "Other"
    account: str = "cash"
    merchant: str = ""
    date: Optional[str] = None
    notes: str = ""
    participants: List[str] = ["Me"]
    split_mode: str = "equal"
    items: List[ItemBody] = []
    exact_shares: Dict[str, float] = {}
    paid_by: str = "Me"
    add_to_inventory: bool = False


class SettlementBody(BaseModel):
    person: str
    amount: float
    method: str = "Revolut"
    account: str = "revolut"
    direction: str = "in"
    date: Optional[str] = None
    transaction_id: Optional[str] = None


class TransferBody(BaseModel):
    from_account: str
    to_account: str
    amount: float
    date: Optional[str] = None
    notes: str = ""


class IncomeBody(BaseModel):
    account: str
    amount: float
    description: str = ""
    date: Optional[str] = None


class TaskBody(BaseModel):
    title: str
    priority: str = "normal"
    due: Optional[str] = None
    recurring: Optional[str] = None
    done: bool = False


class WeightBody(BaseModel):
    weight: float
    date: Optional[str] = None
    note: str = ""


class GroceryBody(BaseModel):
    name: str
    quantity: float = 1
    unit: str = "unit"
    category: str = "Other"
    price: Optional[float] = None
    store: Optional[str] = None
    low_threshold: float = 0
    notes: str = ""
    expiration: Optional[str] = None


class GroceryUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    store: Optional[str] = None
    low_threshold: Optional[float] = None
    notes: Optional[str] = None
    expiration: Optional[str] = None


class TxnUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    account: Optional[str] = None
    payment_method: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None
    amount: Optional[float] = None
    personal_amount: Optional[float] = None


class MealBody(BaseModel):
    description: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    date: Optional[str] = None


class ShoppingBody(BaseModel):
    name: str
    quantity: float = 1
    unit: str = "unit"
    note: str = ""


class BuyBody(BaseModel):
    price: Optional[float] = None
    store: Optional[str] = None


class RecipeIngredient(BaseModel):
    name: str
    quantity: float = 1
    unit: str = "unit"


class RecipeBody(BaseModel):
    name: str
    servings: int = 1
    ingredients: List[RecipeIngredient] = []
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    notes: str = ""


class AIChatBody(BaseModel):
    message: Optional[str] = ""
    session_id: Optional[str] = None
    image_base64: Optional[str] = None
    confirm_token: Optional[str] = None


class WorkoutSet(BaseModel):
    reps: Optional[int] = None
    weight: Optional[float] = None


class WorkoutExercise(BaseModel):
    name: str
    is_isometric: bool = False
    sets: List[WorkoutSet] = []
    duration: Optional[int] = None
    note: str = ""


class WorkoutBody(BaseModel):
    type: str = "Push"
    date: Optional[str] = None
    exercises: List[WorkoutExercise] = []
    notes: str = ""


class PhotoNote(BaseModel):
    note: str = ""


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def person_to_dict(p: Person) -> dict:
    return {
        "id": p.id, "name": p.name, "name_lower": p.name_lower,
        "photo": p.photo, "notes": p.notes or "",
        "payment_preference": p.payment_preference or "", "created_at": p.created_at,
    }


def split_to_dict(s: Split) -> dict:
    return {
        "person_id": s.person_id, "person_name": s.person_name,
        "amount": round(s.amount, 2), "is_me": s.is_me,
    }


def txn_to_dict(t: Transaction, with_splits: bool = True) -> dict:
    items = t.items or []
    d = {
        "id": t.id, "type": t.type,
        "gross_amount": round(t.gross_amount, 2),
        "personal_amount": round(t.personal_amount, 2),
        "reimbursable_amount": round(t.reimbursable_amount, 2),
        "description": t.description or "",
        "category": t.category or "",
        "account": t.account or "",
        "merchant": t.merchant or "",
        "date": t.date, "month": t.month,
        "notes": t.notes or "",
        "paid_by": t.paid_by or "",
        "items": items,
        "created_at": t.created_at,
    }
    if with_splits:
        d["splits"] = [split_to_dict(s) for s in (t.splits or [])]
    # preserve transfer/income fields from items for frontend compatibility
    if isinstance(items, dict):
        if items.get("from_account"):
            d["from_account"] = items["from_account"]
        if items.get("to_account"):
            d["to_account"] = items["to_account"]
    return d


# ---------------------------------------------------------------------------
# Finance core
# ---------------------------------------------------------------------------
async def resolve_person(name: str, db) -> dict:
    if name.strip().lower() in ("me", "eu", "sá", "sa"):
        return {"id": "me", "name": "Me"}
    nl = name.strip().lower()
    result = await db.execute(select(Person).where(Person.name_lower == nl))
    p = result.scalar_one_or_none()
    if not p:
        p = Person(
            id=new_id(), name=name.strip(), name_lower=nl,
            photo=None, notes="", payment_preference="", created_at=now_iso())
        db.add(p)
        await db.commit()
        await db.refresh(p)
    return {"id": p.id, "name": p.name}


def compute_shares(gross: float, participants: List[str], items, split_mode, exact_shares):
    names = [n if n.strip().lower() not in ("me", "eu", "sá", "sa") else "Me" for n in participants]
    if "Me" not in names:
        names = ["Me"] + names
    shares = {n: 0.0 for n in names}
    if split_mode == "items" and items:
        for it in items:
            assigned = it.get("assigned") or ["Me"]
            assigned = [a if a.strip().lower() not in ("me", "eu", "sá", "sa") else "Me" for a in assigned]
            for a in assigned:
                shares.setdefault(a, 0.0)
                shares[a] += float(it["price"]) / len(assigned)
    elif split_mode == "exact" and exact_shares:
        for k, v in exact_shares.items():
            key = k if k.strip().lower() not in ("me", "eu", "sá", "sa") else "Me"
            shares[key] = float(v)
    else:
        each = gross / len(names) if names else gross
        for n in names:
            shares[n] = each
    shares = {k: round(v, 2) for k, v in shares.items() if v > 0 or k == "Me"}
    return shares


async def create_expense_record(body: ExpenseBody, db) -> dict:
    date = body.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    gross = body.amount
    if gross is None and body.items:
        gross = round(sum(float(i.price) for i in body.items), 2)
    if gross is None:
        gross = 0.0
    items = [i.model_dump() for i in body.items] if body.items else []
    shares = compute_shares(gross, body.participants, items, body.split_mode, body.exact_shares)

    split_list = []
    for name, amt in shares.items():
        person = await resolve_person(name, db)
        split_list.append({"person_id": person["id"], "person_name": person["name"],
                           "amount": round(amt, 2), "is_me": person["id"] == "me"})

    personal = round(next((s["amount"] for s in split_list if s["is_me"]), 0.0), 2)
    reimbursable = round(gross - personal, 2)

    paid_by = "me" if body.paid_by.strip().lower() in ("me", "eu", "sá", "sa") else (await resolve_person(body.paid_by, db))["id"]

    txn = Transaction(
        id=new_id(),
        type="expense",
        gross_amount=round(gross, 2),
        personal_amount=personal,
        reimbursable_amount=reimbursable,
        description=body.description or body.merchant,
        category=body.category,
        account=body.account,
        merchant=body.merchant,
        date=date,
        month=month_of(date),
        notes=body.notes,
        paid_by=paid_by,
        items=items,
        created_at=now_iso(),
    )
    db.add(txn)
    await db.flush()

    for s in split_list:
        db.add(Split(
            id=new_id(), transaction_id=txn.id, person_id=s["person_id"],
            person_name=s["person_name"], amount=s["amount"], is_me=s["is_me"],
            created_at=now_iso()))

    inventory_added = []
    if body.add_to_inventory and items:
        for it in items:
            g = Grocery(
                id=new_id(), name=it["name"], name_lower=it["name"].lower(),
                quantity=1, unit="unit", category="Other",
                price=it["price"], store=body.merchant, low_threshold=0,
                notes="", expiration=None,
                created_at=now_iso(), updated_at=now_iso())
            db.add(g)
            inventory_added.append(it["name"])

    await db.commit()
    await db.refresh(txn)
    return {"transaction": txn_to_dict(txn), "inventory_added": inventory_added}


async def compute_account_balance(account: str, db) -> float:
    result = await db.execute(select(Account).where(Account.id == account))
    acc = result.scalar_one_or_none()
    bal = acc.opening_balance if acc else 0.0

    result = await db.execute(select(Transaction))
    transactions = result.scalars().all()
    for t in transactions:
        if t.type == "expense" and (t.paid_by or "") == "me" and t.account == account:
            bal -= t.gross_amount
        elif t.type == "income" and t.account == account:
            bal += t.gross_amount
        elif t.type == "transfer":
            items = t.items or {}
            if isinstance(items, dict):
                if items.get("from_account") == account:
                    bal -= t.gross_amount
                if items.get("to_account") == account:
                    bal += t.gross_amount

    result = await db.execute(select(Settlement))
    settlements = result.scalars().all()
    for s in settlements:
        if s.account == account:
            bal += s.amount if s.direction == "in" else -s.amount
    return round(bal, 2)


async def people_balances(db) -> List[dict]:
    result = await db.execute(select(Person))
    people = result.scalars().all()

    result = await db.execute(select(Transaction).where(Transaction.type == "expense").options(selectinload(Transaction.splits)))
    transactions = result.scalars().all()

    result = await db.execute(select(Settlement))
    settlements = result.scalars().all()

    result = []
    for p in people:
        owed = 0.0
        i_owe = 0.0
        for t in transactions:
            for s in t.splits:
                if s.person_id == p.id:
                    if (t.paid_by or "") == "me":
                        owed += s.amount
            if (t.paid_by or "") == p.id:
                mine = next((s.amount for s in t.splits if s.is_me), 0.0)
                i_owe += mine
        for s in settlements:
            if s.person_id == p.id:
                if s.direction == "in":
                    owed -= s.amount
                else:
                    i_owe -= s.amount
        net = round(owed - i_owe, 2)
        result.append({**person_to_dict(p), "owes_me": round(owed, 2), "i_owe": round(i_owe, 2), "net": net})
    return result


# ---------------------------------------------------------------------------
# Price intelligence + shopping helpers
# ---------------------------------------------------------------------------
async def record_price(name: str, store: Optional[str], price: Optional[float], unit: str, db):
    if not store or price is None:
        return
    pr = PriceRecord(
        id=new_id(), name=name, name_lower=name.lower(), store=store,
        price=round(float(price), 2), unit=unit,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"), created_at=now_iso())
    db.add(pr)
    await db.commit()


async def latest_prices(name_lower: str, db) -> dict:
    result = await db.execute(
        select(PriceRecord).where(PriceRecord.name_lower == name_lower).order_by(desc(PriceRecord.date)))
    recs = result.scalars().all()
    per_store = {}
    for r in recs:
        if r.store and r.store not in per_store:
            per_store[r.store] = {"price": r.price, "date": r.date}
    return per_store


def cheapest_store(per_store: dict):
    if not per_store:
        return None
    s, v = min(per_store.items(), key=lambda kv: kv[1]["price"])
    return {"store": s, "price": v["price"], "date": v["date"]}


async def shopping_payload(db) -> dict:
    result = await db.execute(select(ShoppingItem).order_by(asc(ShoppingItem.created_at)))
    items = result.scalars().all()
    enriched = []
    store_baskets = {}
    split_total = 0.0
    unknown = []
    for it in items:
        per_store = await latest_prices(it.name_lower, db)
        ch = cheapest_store(per_store)
        if ch:
            split_total += ch["price"]
            for store, v in per_store.items():
                b = store_baskets.setdefault(store, {"total": 0.0, "items": []})
                b["total"] = round(b["total"] + v["price"], 2)
                b["items"].append(it.name)
        else:
            unknown.append(it.name)
        enriched.append({**{"id": it.id, "name": it.name, "name_lower": it.name_lower,
                           "quantity": it.quantity, "unit": it.unit, "note": it.note,
                           "bought": it.bought, "created_at": it.created_at},
                         "per_store": per_store, "best": ch, "known": ch is not None})

    priced_count = len(items) - len(unknown)
    stores = [{"store": s, "total": round(b["total"], 2), "covers": len(b["items"]), "items": b["items"]}
              for s, b in store_baskets.items()]
    stores_sorted = sorted(stores, key=lambda s: (-s["covers"], s["total"]))
    best_single = stores_sorted[0] if stores_sorted else None

    recommendation = ""
    if best_single and priced_count:
        if best_single["covers"] >= priced_count:
            saving = round(best_single["total"] - round(split_total, 2), 2)
            recommendation = (f"{best_single['store']} covers all {priced_count} priced items for about "
                              f"€{best_single['total']:.2f}. Splitting across stores would cost about "
                              f"€{split_total:.2f} — a saving of only €{max(saving,0):.2f}, so one stop is usually enough.")
        else:
            recommendation = (f"{best_single['store']} is your best single stop, covering {best_single['covers']} of "
                              f"{priced_count} priced items (~€{best_single['total']:.2f}).")
    if unknown:
        recommendation += f" No known price yet for: {', '.join(unknown)}."

    return {
        "items": enriched,
        "stores": stores_sorted,
        "best_single": best_single,
        "split_total": round(split_total, 2),
        "unknown": unknown,
        "recommendation": recommendation.strip(),
    }


async def add_shopping_item_doc(name: str, quantity: float, unit: str, note: str, db) -> dict:
    result = await db.execute(
        select(ShoppingItem).where(ShoppingItem.name_lower == name.lower(), ShoppingItem.bought == False))
    existing = result.scalar_one_or_none()
    if existing:
        return {"id": existing.id, "name": existing.name, "name_lower": existing.name_lower,
                "quantity": existing.quantity, "unit": existing.unit, "note": existing.note,
                "bought": existing.bought, "created_at": existing.created_at}
    doc = ShoppingItem(
        id=new_id(), name=name, name_lower=name.lower(), quantity=quantity,
        unit=unit, note=note, bought=False, created_at=now_iso())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"id": doc.id, "name": doc.name, "name_lower": doc.name_lower,
            "quantity": doc.quantity, "unit": doc.unit, "note": doc.note,
            "bought": doc.bought, "created_at": doc.created_at}


async def generate_shopping_doc(days: int, db) -> dict:
    result = await db.execute(select(Grocery))
    groceries = result.scalars().all()
    stock = {g.name_lower: g for g in groceries}
    added = []
    for g in groceries:
        if g.low_threshold and g.quantity <= g.low_threshold:
            await add_shopping_item_doc(g.name, max(1, round(days / 2)), g.unit or "unit", "Running low", db)
            added.append(g.name)
    result = await db.execute(select(PriceRecord.name).distinct())
    known_names = [r[0] for r in result.all()]
    for name in known_names:
        nl = name.lower()
        if nl not in stock or stock[nl].quantity <= 0:
            doc = await add_shopping_item_doc(name, 1, "unit", "From your usual buys", db)
            if doc["name"] not in added:
                added.append(doc["name"])
    payload = await shopping_payload(db)
    payload["added"] = added
    return payload


async def cook_recipe_doc(recipe: dict, db) -> dict:
    changes = []
    for ing in recipe.get("ingredients", []):
        result = await db.execute(select(Grocery).where(Grocery.name_lower == ing["name"].lower()))
        g = result.scalar_one_or_none()
        if g:
            newq = max(0, round(g.quantity - (ing.get("quantity") or 0), 2))
            g.quantity = newq
            g.updated_at = now_iso()
            changes.append(f"{ing['name']} −{ing.get('quantity', 0)}{ing.get('unit', '')} (now {newq})")
        else:
            changes.append(f"{ing['name']} (not in inventory)")
    servings = recipe.get("servings") or 1
    meal = None
    if recipe.get("calories"):
        meal = Meal(
            id=new_id(), description=f"{recipe['name']} (1 serving)",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            calories=round((recipe.get("calories") or 0) / servings, 1),
            protein=round((recipe.get("protein") or 0) / servings, 1),
            carbs=round((recipe.get("carbs") or 0) / servings, 1),
            fat=round((recipe.get("fat") or 0) / servings, 1),
            created_at=now_iso())
        db.add(meal)
    await db.commit()
    return {"recipe": recipe["name"], "inventory_changes": changes, "meal_logged": meal is not None}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api_router.post("/auth/login")
async def login(body: LoginBody, db=Depends(get_db)):
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.id, email)
    return {"token": token, "user": {"id": user.id, "email": email, "name": user.name or OWNER_NAME}}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"], "name": user.get("name", OWNER_NAME)}


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------
@api_router.get("/people")
async def get_people(user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await people_balances(db)


@api_router.post("/people")
async def create_person(body: PersonBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    p = Person(
        id=new_id(), name=body.name, name_lower=body.name.lower(),
        photo=body.photo, notes=body.notes or "",
        payment_preference=body.payment_preference or "", created_at=now_iso())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return person_to_dict(p)


@api_router.delete("/people/{pid}")
async def delete_person(pid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Person).where(Person.id == pid))
    p = result.scalar_one_or_none()
    if p:
        await db.delete(p)
        await db.commit()
    return {"ok": True}


@api_router.get("/people/{pid}")
async def person_detail(pid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    people = await people_balances(db)
    person = next((p for p in people if p["id"] == pid), None)
    if not person:
        raise HTTPException(404, "Person not found")

    result = await db.execute(
        select(Transaction).where(Transaction.type == "expense").options(selectinload(Transaction.splits)).order_by(desc(Transaction.date)))
    txns = []
    for t in result.scalars().all():
        for s in t.splits:
            if s.person_id == pid:
                txns.append({"id": t.id, "date": t.date, "merchant": t.merchant or t.description,
                             "amount": s.amount, "gross": t.gross_amount})

    result = await db.execute(select(Settlement).where(Settlement.person_id == pid).order_by(desc(Settlement.date)))
    settlements = result.scalars().all()
    return {"person": person, "transactions": txns,
            "settlements": [{"id": s.id, "person_id": s.person_id, "person_name": s.person_name,
                             "amount": s.amount, "method": s.method, "account": s.account,
                             "direction": s.direction, "date": s.date, "transaction_id": s.transaction_id,
                             "created_at": s.created_at} for s in settlements]}


# ---------------------------------------------------------------------------
# Categories & Accounts
# ---------------------------------------------------------------------------
@api_router.get("/categories")
async def get_categories(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Category).order_by(asc(Category.created_at)))
    return [{"id": c.id, "name": c.name, "icon": c.icon, "color": c.color, "created_at": c.created_at}
            for c in result.scalars().all()]


@api_router.post("/categories")
async def create_category(body: CategoryBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    c = Category(id=new_id(), name=body.name, icon=body.icon, color=body.color, created_at=now_iso())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": c.id, "name": c.name, "icon": c.icon, "color": c.color, "created_at": c.created_at}


@api_router.delete("/categories/{cid}")
async def delete_category(cid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == cid))
    c = result.scalar_one_or_none()
    if c:
        await db.delete(c)
        await db.commit()
    return {"ok": True}


@api_router.get("/accounts")
async def get_accounts(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Account).order_by(asc(Account.created_at)))
    accs = result.scalars().all()
    out = []
    for a in accs:
        out.append({"id": a.id, "name": a.name, "type": a.type,
                    "opening_balance": a.opening_balance,
                    "balance": await compute_account_balance(a.id, db),
                    "created_at": a.created_at})
    return out


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
async def refund_map(db) -> dict:
    result = await db.execute(
        select(Settlement.transaction_id, func.sum(Settlement.amount))
        .where(Settlement.direction == "in", Settlement.transaction_id.isnot(None))
        .group_by(Settlement.transaction_id))
    m = {}
    for tid, amt in result.all():
        m[tid] = round(amt or 0, 2)
    return m


def serialize_txn(t: Transaction, rmap: dict) -> dict:
    d = txn_to_dict(t)
    if d.get("type") != "expense":
        d["payment_method"] = "cash" if d.get("account") == "cash" else "card"
        return d
    reimb = d.get("reimbursable_amount", 0) or 0
    refunded = min(rmap.get(t.id, 0.0), reimb)
    remaining = round(max(reimb - refunded, 0), 2)
    if reimb <= 0.005:
        status = "personal"
    elif remaining <= 0.005:
        status = "settled"
    elif refunded > 0.005:
        status = "partial"
    else:
        status = "pending"
    responsible = [s["person_name"] for s in d.get("splits", []) if not s["is_me"] and s["amount"] > 0.005]
    d["amount_refunded"] = round(refunded, 2)
    d["remaining_refund"] = remaining
    d["refund_status"] = status
    d["responsible"] = responsible
    d["payment_method"] = "cash" if d.get("account") == "cash" else "card"
    return d


def _date_filters(month, start, end):
    filters = []
    if month:
        filters.append(Transaction.month == month)
    if start:
        filters.append(Transaction.date >= start)
    if end:
        filters.append(Transaction.date <= end)
    return filters


@api_router.get("/transactions")
async def get_transactions(month: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
                           payment_method: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    filters = _date_filters(month, start, end)
    stmt = select(Transaction).options(selectinload(Transaction.splits)).order_by(desc(Transaction.date))
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    rmap = await refund_map(db)
    out = [serialize_txn(t, rmap) for t in rows]
    if payment_method in ("cash", "card"):
        out = [t for t in out if t.get("payment_method") == payment_method]
    return out


@api_router.post("/transactions/expense")
async def add_expense(body: ExpenseBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await create_expense_record(body, db)


@api_router.put("/transactions/{tid}")
async def update_transaction(tid: str, body: TxnUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == tid).options(selectinload(Transaction.splits)))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Transaction not found")

    if body.description is not None:
        t.description = body.description
        t.merchant = body.description if not t.merchant else t.merchant
    if body.category is not None:
        t.category = body.category
    if body.notes is not None:
        t.notes = body.notes
    if body.payment_method in ("cash", "card"):
        t.account = "cash" if body.payment_method == "cash" else "revolut"
    if body.account in ("cash", "revolut"):
        t.account = body.account
    if body.date:
        t.date = body.date
        t.month = month_of(body.date)

    if body.amount is not None and t.type == "expense":
        new_gross = round(float(body.amount), 2)
        old_gross = t.gross_amount or 0
        splits = t.splits
        if body.personal_amount is not None:
            personal = round(min(float(body.personal_amount), new_gross), 2)
            new_splits = [{"person_id": "me", "person_name": "Me", "amount": personal, "is_me": True}]
            others = round(new_gross - personal, 2)
            existing_others = [s for s in splits if not s.is_me]
            if existing_others and others > 0:
                each = round(others / len(existing_others), 2)
                for s in existing_others:
                    new_splits.append({"person_id": s.person_id, "person_name": s.person_name,
                                       "amount": each, "is_me": False})
            t.personal_amount = personal
            # replace splits
            for s in splits:
                await db.delete(s)
            for s in new_splits:
                db.add(Split(id=new_id(), transaction_id=t.id, person_id=s["person_id"],
                             person_name=s["person_name"], amount=s["amount"], is_me=s["is_me"],
                             created_at=now_iso()))
            await db.flush()
        elif len(splits) > 1 and old_gross > 0:
            factor = new_gross / old_gross
            for s in splits:
                s.amount = round(s.amount * factor, 2)
            t.personal_amount = round(next((s.amount for s in splits if s.is_me), 0), 2)
        else:
            for s in splits:
                await db.delete(s)
            db.add(Split(id=new_id(), transaction_id=t.id, person_id="me",
                         person_name="Me", amount=new_gross, is_me=True,
                         created_at=now_iso()))
            t.personal_amount = new_gross
            await db.flush()
        t.gross_amount = new_gross
        t.reimbursable_amount = round(new_gross - t.personal_amount, 2)
    elif body.personal_amount is not None and t.type == "expense":
        gross = t.gross_amount or 0
        personal = round(min(float(body.personal_amount), gross), 2)
        t.personal_amount = personal
        t.reimbursable_amount = round(gross - personal, 2)

    await db.commit()
    await db.refresh(t)
    rmap = await refund_map(db)
    return serialize_txn(t, rmap)


@api_router.delete("/transactions/{tid}")
async def delete_transaction(tid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == tid))
    t = result.scalar_one_or_none()
    if t:
        await db.delete(t)
    result = await db.execute(select(Settlement).where(Settlement.transaction_id == tid))
    for s in result.scalars().all():
        await db.delete(s)
    await db.commit()
    return {"ok": True}


@api_router.post("/transactions/transfer")
async def add_transfer(body: TransferBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    date = body.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    t = Transaction(
        id=new_id(), type="transfer",
        gross_amount=round(body.amount, 2),
        personal_amount=0.0, reimbursable_amount=0.0,
        description=body.notes or "Transfer",
        category="Transfer", account=body.from_account,
        merchant="", date=date, month=month_of(date),
        notes=body.notes,
        items={"from_account": body.from_account, "to_account": body.to_account},
        created_at=now_iso())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return txn_to_dict(t, with_splits=False)


@api_router.post("/transactions/income")
async def add_income(body: IncomeBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    date = body.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    t = Transaction(
        id=new_id(), type="income", account=body.account,
        gross_amount=round(body.amount, 2),
        personal_amount=0.0, reimbursable_amount=0.0,
        description=body.description or "Income",
        category="Income", merchant="", date=date, month=month_of(date),
        notes="", items=[], created_at=now_iso())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return txn_to_dict(t, with_splits=False)


# ---------------------------------------------------------------------------
# Settlements
# ---------------------------------------------------------------------------
@api_router.post("/settlements")
async def add_settlement(body: SettlementBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    person = await resolve_person(body.person, db)
    date = body.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s = Settlement(
        id=new_id(), person_id=person["id"], person_name=person["name"],
        amount=round(body.amount, 2), method=body.method, account=body.account,
        direction=body.direction, date=date, transaction_id=body.transaction_id,
        created_at=now_iso())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return {"id": s.id, "person_id": s.person_id, "person_name": s.person_name,
            "amount": s.amount, "method": s.method, "account": s.account,
            "direction": s.direction, "date": s.date, "transaction_id": s.transaction_id,
            "created_at": s.created_at}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@api_router.get("/analytics/summary")
async def analytics_summary(month: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None,
                            user: dict = Depends(get_current_user), db=Depends(get_db)):
    accounts = await get_accounts(user, db)
    cash = next((a["balance"] for a in accounts if a["id"] == "cash"), 0)
    revolut = next((a["balance"] for a in accounts if a["id"] == "revolut"), 0)

    filters = [Transaction.type == "expense", *_date_filters(month, start, end)]
    result = await db.execute(select(Transaction).options(selectinload(Transaction.splits)).where(*filters))
    gross = personal = cash_spent = card_spent = reimbursable = 0.0
    by_cat = {}
    by_day = {}
    for t in result.scalars().all():
        gross += t.gross_amount
        personal += t.personal_amount
        reimbursable += t.reimbursable_amount
        if t.account == "cash":
            cash_spent += t.gross_amount
        else:
            card_spent += t.gross_amount
        by_cat[t.category] = by_cat.get(t.category, 0) + t.gross_amount
        by_day[t.date] = by_day.get(t.date, 0) + t.gross_amount

    s_filters = [Settlement.direction == "in"]
    if start:
        s_filters.append(Settlement.date >= start)
    if end:
        s_filters.append(Settlement.date <= end)
    result = await db.execute(select(Settlement).where(*s_filters))
    refunded = 0.0
    for s in result.scalars().all():
        if month and not str(s.date or "").startswith(month):
            continue
        refunded += s.amount

    people = await people_balances(db)
    owed_to_me = round(sum(p["owes_me"] for p in people), 2)
    i_owe = round(sum(p["i_owe"] for p in people), 2)
    outstanding = round(sum(max(p["net"], 0) for p in people), 2)

    result = await db.execute(select(Grocery).order_by(asc(Grocery.name)))
    groceries = result.scalars().all()
    out_of_stock = [g.name for g in groceries if (g.quantity or 0) <= 0]
    low_stock = [g.name for g in groceries if (g.quantity or 0) > 0 and g.low_threshold and g.quantity <= g.low_threshold]
    unknown_price = [g.name for g in groceries if g.price is None]

    result = await db.execute(select(Transaction.month).distinct())
    months = sorted([r[0] for r in result.all() if r[0]], reverse=True)

    return {
        "cash": cash, "revolut": revolut, "total_available": round(cash + revolut, 2),
        "gross": round(gross, 2), "personal": round(personal, 2),
        "reimbursable": round(reimbursable, 2),
        "cash_spent": round(cash_spent, 2), "card_spent": round(card_spent, 2),
        "refunded": round(refunded, 2), "pending": outstanding,
        "owed_to_me": owed_to_me, "i_owe": i_owe, "outstanding": outstanding,
        "by_category": [{"name": k, "value": round(v, 2)} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])],
        "by_day": [{"date": k, "value": round(v, 2)} for k, v in sorted(by_day.items())],
        "grocery": {"total": len(groceries), "out_of_stock": out_of_stock, "low_stock": low_stock, "unknown_price": unknown_price},
        "months": months,
    }


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
@api_router.get("/tasks")
async def get_tasks(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Task).order_by(desc(Task.created_at)))
    return [{"id": t.id, "title": t.title, "priority": t.priority, "due": t.due,
             "recurring": t.recurring, "done": t.done, "created_at": t.created_at}
            for t in result.scalars().all()]


@api_router.post("/tasks")
async def create_task(body: TaskBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    t = Task(id=new_id(), title=body.title, priority=body.priority, due=body.due,
             recurring=body.recurring, done=body.done, created_at=now_iso())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": t.id, "title": t.title, "priority": t.priority, "due": t.due,
            "recurring": t.recurring, "done": t.done, "created_at": t.created_at}


@api_router.put("/tasks/{tid}")
async def update_task(tid: str, body: TaskBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == tid))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Task not found")
    t.title = body.title
    t.priority = body.priority
    t.due = body.due
    t.recurring = body.recurring
    t.done = body.done
    await db.commit()
    await db.refresh(t)
    return {"id": t.id, "title": t.title, "priority": t.priority, "due": t.due,
            "recurring": t.recurring, "done": t.done, "created_at": t.created_at}


@api_router.delete("/tasks/{tid}")
async def delete_task(tid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == tid))
    t = result.scalar_one_or_none()
    if t:
        await db.delete(t)
        await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Body / Weight
# ---------------------------------------------------------------------------
@api_router.get("/weight")
async def get_weight(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(WeightEntry).order_by(asc(WeightEntry.date)))
    return [{"id": w.id, "weight": w.weight, "date": w.date, "note": w.note or "", "created_at": w.created_at}
            for w in result.scalars().all()]


@api_router.post("/weight")
async def add_weight(body: WeightBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    date = body.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    w = WeightEntry(id=new_id(), weight=body.weight, date=date, note=body.note, created_at=now_iso())
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return {"id": w.id, "weight": w.weight, "date": w.date, "note": w.note or "", "created_at": w.created_at}


@api_router.delete("/weight/{wid}")
async def delete_weight(wid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(WeightEntry).where(WeightEntry.id == wid))
    w = result.scalar_one_or_none()
    if w:
        await db.delete(w)
        await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Workouts
# ---------------------------------------------------------------------------
@api_router.get("/workouts")
async def get_workouts(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Workout).order_by(desc(Workout.date)))
    return [{"id": w.id, "type": w.type, "date": w.date, "notes": w.notes or "",
             "exercises": w.exercises or [], "created_at": w.created_at}
            for w in result.scalars().all()]


async def create_workout(body: WorkoutBody, db) -> dict:
    date = body.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    w = Workout(
        id=new_id(), type=body.type, date=date, notes=body.notes,
        exercises=[e.model_dump() for e in body.exercises], created_at=now_iso())
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return {"id": w.id, "type": w.type, "date": w.date, "notes": w.notes or "",
            "exercises": w.exercises or [], "created_at": w.created_at}


@api_router.post("/workouts")
async def post_workout(body: WorkoutBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await create_workout(body, db)


@api_router.delete("/workouts/{wid}")
async def delete_workout(wid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Workout).where(Workout.id == wid))
    w = result.scalar_one_or_none()
    if w:
        await db.delete(w)
        await db.commit()
    return {"ok": True}


@api_router.get("/workouts/prs")
async def workout_prs(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Workout))
    prs = {}
    for w in result.scalars().all():
        for e in w.exercises or []:
            name = e["name"]
            p = prs.setdefault(name, {"name": name, "best_weight": 0, "best_reps": 0, "best_duration": 0, "is_isometric": e.get("is_isometric", False)})
            if e.get("duration"):
                p["best_duration"] = max(p["best_duration"], e["duration"])
                p["is_isometric"] = True
            for s in e.get("sets", []):
                if s.get("weight"):
                    p["best_weight"] = max(p["best_weight"], s["weight"])
                if s.get("reps"):
                    p["best_reps"] = max(p["best_reps"], s["reps"])
    return list(prs.values())


# ---------------------------------------------------------------------------
# Progress photos (local filesystem)
# ---------------------------------------------------------------------------
@api_router.post("/photos")
async def upload_photo(file: UploadFile = File(...), note: str = Query(""), user: dict = Depends(get_current_user), db=Depends(get_db)):
    ensure_upload_dirs()
    ext = (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg").lower()
    uid = user["id"]
    user_dir = PHOTOS_DIR / uid
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{new_id()}.{ext}"
    storage_path = f"photos/{uid}/{filename}"
    file_path = UPLOAD_DIR / storage_path
    data = await file.read()
    ct = file.content_type or {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    with open(file_path, "wb") as f:
        f.write(data)
    doc = Photo(
        id=new_id(), storage_path=storage_path, content_type=ct, note=note,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"), is_deleted=False, created_at=now_iso())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"id": doc.id, "storage_path": doc.storage_path, "content_type": doc.content_type,
            "note": doc.note or "", "date": doc.date, "is_deleted": doc.is_deleted,
            "created_at": doc.created_at}


@api_router.get("/photos")
async def list_photos(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Photo).where(Photo.is_deleted == False).order_by(desc(Photo.date)))
    rows = result.scalars().all()
    return [{"id": r.id, "storage_path": r.storage_path, "content_type": r.content_type,
             "note": r.note or "", "date": r.date, "is_deleted": r.is_deleted,
             "created_at": r.created_at, "url": f"/api/photos/file/{r.storage_path}"}
            for r in rows]


@api_router.delete("/photos/{pid}")
async def delete_photo(pid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Photo).where(Photo.id == pid))
    p = result.scalar_one_or_none()
    if p:
        p.is_deleted = True
        await db.commit()
    return {"ok": True}


@api_router.get("/photos/file/{path:path}")
async def serve_photo(path: str, auth: str = Query(None), authorization: str = Header(None)):
    token = auth or (authorization[7:] if authorization and authorization.startswith("Bearer ") else None)
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(401, "Not authenticated")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Photo).where(Photo.storage_path == path, Photo.is_deleted == False))
        record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Not found")
    file_path = UPLOAD_DIR / path
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    with open(file_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type=record.content_type)


# ---------------------------------------------------------------------------
# Groceries
# ---------------------------------------------------------------------------
@api_router.get("/groceries")
async def get_groceries(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Grocery).order_by(asc(Grocery.name)))
    return [{"id": g.id, "name": g.name, "name_lower": g.name_lower, "quantity": g.quantity,
             "unit": g.unit, "category": g.category, "price": g.price, "store": g.store,
             "low_threshold": g.low_threshold, "notes": g.notes or "", "expiration": g.expiration,
             "created_at": g.created_at, "updated_at": g.updated_at}
            for g in result.scalars().all()]


@api_router.post("/groceries")
async def add_grocery(body: GroceryBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await record_price(body.name, body.store, body.price, body.unit, db)
    result = await db.execute(select(Grocery).where(Grocery.name_lower == body.name.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        existing.quantity += body.quantity
        if body.price is not None:
            existing.price = body.price
        if body.store:
            existing.store = body.store
        existing.updated_at = now_iso()
        await db.commit()
        await db.refresh(existing)
        return {"id": existing.id, "name": existing.name, "name_lower": existing.name_lower,
                "quantity": existing.quantity, "unit": existing.unit, "category": existing.category,
                "price": existing.price, "store": existing.store, "low_threshold": existing.low_threshold,
                "notes": existing.notes or "", "expiration": existing.expiration,
                "created_at": existing.created_at, "updated_at": existing.updated_at}
    g = Grocery(
        id=new_id(), name=body.name, name_lower=body.name.lower(),
        quantity=body.quantity, unit=body.unit, category=body.category,
        price=body.price, store=body.store, low_threshold=body.low_threshold,
        notes=body.notes or "", expiration=body.expiration,
        created_at=now_iso(), updated_at=now_iso())
    db.add(g)
    await db.commit()
    await db.refresh(g)
    return {"id": g.id, "name": g.name, "name_lower": g.name_lower, "quantity": g.quantity,
            "unit": g.unit, "category": g.category, "price": g.price, "store": g.store,
            "low_threshold": g.low_threshold, "notes": g.notes or "", "expiration": g.expiration,
            "created_at": g.created_at, "updated_at": g.updated_at}


@api_router.put("/groceries/{gid}")
async def update_grocery(gid: str, body: GroceryUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Grocery).where(Grocery.id == gid))
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Item not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "name" in updates:
        updates["name_lower"] = updates["name"].lower()
    if updates.get("price") is not None:
        await record_price(updates.get("name", g.name), updates.get("store", g.store), updates["price"], updates.get("unit", g.unit or "unit"), db)
    for k, v in updates.items():
        setattr(g, k, v)
    g.updated_at = now_iso()
    await db.commit()
    await db.refresh(g)
    return {"id": g.id, "name": g.name, "name_lower": g.name_lower, "quantity": g.quantity,
            "unit": g.unit, "category": g.category, "price": g.price, "store": g.store,
            "low_threshold": g.low_threshold, "notes": g.notes or "", "expiration": g.expiration,
            "created_at": g.created_at, "updated_at": g.updated_at}


@api_router.delete("/groceries/{gid}")
async def delete_grocery(gid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Grocery).where(Grocery.id == gid))
    g = result.scalar_one_or_none()
    if g:
        await db.delete(g)
        await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Meals / Nutrition
# ---------------------------------------------------------------------------
@api_router.get("/meals")
async def get_meals(date: Optional[str] = None, user: dict = Depends(get_current_user), db=Depends(get_db)):
    filters = []
    if date:
        filters.append(Meal.date == date)
    stmt = select(Meal).order_by(desc(Meal.created_at))
    if filters:
        stmt = stmt.where(*filters)
    result = await db.execute(stmt)
    return [{"id": m.id, "description": m.description, "date": m.date,
             "calories": m.calories, "protein": m.protein, "carbs": m.carbs,
             "fat": m.fat, "created_at": m.created_at}
            for m in result.scalars().all()]


@api_router.post("/meals")
async def add_meal(body: MealBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    date = body.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    m = Meal(
        id=new_id(), description=body.description, date=date,
        calories=body.calories, protein=body.protein, carbs=body.carbs,
        fat=body.fat, created_at=now_iso())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return {"id": m.id, "description": m.description, "date": m.date,
            "calories": m.calories, "protein": m.protein, "carbs": m.carbs,
            "fat": m.fat, "created_at": m.created_at}


@api_router.delete("/meals/{mid}")
async def delete_meal(mid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Meal).where(Meal.id == mid))
    m = result.scalar_one_or_none()
    if m:
        await db.delete(m)
        await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Shopping list + price intelligence
# ---------------------------------------------------------------------------
@api_router.get("/shopping")
async def get_shopping(user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await shopping_payload(db)


@api_router.post("/shopping")
async def post_shopping(body: ShoppingBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await add_shopping_item_doc(body.name, body.quantity, body.unit, body.note, db)


@api_router.post("/shopping/generate")
async def gen_shopping(days: int = 7, user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await generate_shopping_doc(days, db)


@api_router.delete("/shopping/{sid}")
async def del_shopping(sid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(ShoppingItem).where(ShoppingItem.id == sid))
    it = result.scalar_one_or_none()
    if it:
        await db.delete(it)
        await db.commit()
    return {"ok": True}


@api_router.post("/shopping/{sid}/buy")
async def buy_shopping(sid: str, body: BuyBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(ShoppingItem).where(ShoppingItem.id == sid))
    it = result.scalar_one_or_none()
    if not it:
        raise HTTPException(404, "Item not found")
    await add_grocery(GroceryBody(name=it.name, quantity=it.quantity or 1, unit=it.unit or "unit",
                                  price=body.price, store=body.store), user, db)
    await db.delete(it)
    await db.commit()
    return {"ok": True}


@api_router.get("/prices/{name}")
async def get_prices(name: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    per_store = await latest_prices(name.lower(), db)
    result = await db.execute(
        select(PriceRecord).where(PriceRecord.name_lower == name.lower()).order_by(desc(PriceRecord.date)))
    history = [{"id": r.id, "name": r.name, "name_lower": r.name_lower, "store": r.store,
                "price": r.price, "unit": r.unit, "date": r.date, "created_at": r.created_at}
               for r in result.scalars().all()]
    return {"name": name, "per_store": per_store, "cheapest": cheapest_store(per_store), "history": history}


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------
@api_router.get("/recipes")
async def get_recipes(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Recipe).order_by(asc(Recipe.name)))
    return [{"id": r.id, "name": r.name, "servings": r.servings,
             "ingredients": r.ingredients or [], "calories": r.calories,
             "protein": r.protein, "carbs": r.carbs, "fat": r.fat,
             "notes": r.notes or "", "created_at": r.created_at}
            for r in result.scalars().all()]


@api_router.post("/recipes")
async def create_recipe(body: RecipeBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    r = Recipe(
        id=new_id(), name=body.name, servings=body.servings,
        ingredients=[i.model_dump() for i in body.ingredients],
        calories=body.calories, protein=body.protein, carbs=body.carbs,
        fat=body.fat, notes=body.notes, created_at=now_iso())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return {"id": r.id, "name": r.name, "servings": r.servings,
            "ingredients": r.ingredients or [], "calories": r.calories,
            "protein": r.protein, "carbs": r.carbs, "fat": r.fat,
            "notes": r.notes or "", "created_at": r.created_at}


@api_router.delete("/recipes/{rid}")
async def delete_recipe(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Recipe).where(Recipe.id == rid))
    r = result.scalar_one_or_none()
    if r:
        await db.delete(r)
        await db.commit()
    return {"ok": True}


@api_router.post("/recipes/{rid}/cook")
async def cook_recipe(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(Recipe).where(Recipe.id == rid))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Recipe not found")
    return await cook_recipe_doc({"id": r.id, "name": r.name, "servings": r.servings,
                                   "ingredients": r.ingredients or [], "calories": r.calories,
                                   "protein": r.protein, "carbs": r.carbs, "fat": r.fat,
                                   "notes": r.notes}, db)


# ---------------------------------------------------------------------------
# AI Actions log
# ---------------------------------------------------------------------------
@api_router.get("/ai/actions")
async def ai_actions(user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(AIAction).order_by(desc(AIAction.created_at)).limit(100))
    return [{"id": a.id, "label": a.label, "tools": a.tools or [], "created": a.created or [],
             "undoable": a.undoable, "undone": a.undone, "created_at": a.created_at}
            for a in result.scalars().all()]


@api_router.post("/ai/actions/{aid}/undo")
async def ai_undo(aid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(AIAction).where(AIAction.id == aid))
    action = result.scalar_one_or_none()
    if not action or action.undone:
        raise HTTPException(404, "Nothing to undo")
    for ref in action.created or []:
        model_map = {
            "transactions": Transaction, "settlements": Settlement, "groceries": Grocery,
            "meals": Meal, "tasks": Task, "weight": WeightEntry, "workouts": Workout,
            "recipes": Recipe, "shopping_items": ShoppingItem,
        }
        model = model_map.get(ref.get("collection"))
        if model:
            res = await db.execute(select(model).where(model.id == ref.get("id")))
            obj = res.scalar_one_or_none()
            if obj:
                await db.delete(obj)
    action.undone = True
    await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Speech to text
# ---------------------------------------------------------------------------
@api_router.post("/ai/transcribe")
async def transcribe(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not OPENAI_API_KEY:
        raise HTTPException(503, "OpenAI API key not configured")
    data = await file.read()
    suffix = os.path.splitext(file.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            with open(tmp_path, "rb") as f:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    files={"file": (file.filename or f"audio{suffix}", f, "audio/webm")},
                    data={"model": "whisper-1", "response_format": "json"})
            if resp.status_code != 200:
                raise HTTPException(resp.status_code, f"Whisper error: {resp.text}")
            return {"text": resp.json().get("text", "")}
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Receipt parsing (extract only, no save)
# ---------------------------------------------------------------------------
@api_router.post("/ai/receipt")
async def parse_receipt(body: AIChatBody, user: dict = Depends(get_current_user)):
    if not GOOGLE_API_KEY:
        raise HTTPException(503, "Google API key not configured")
    if not body.image_base64:
        raise HTTPException(400, "No image provided")
    b64 = body.image_base64.split(",")[-1]
    mime = "image/jpeg"
    if body.image_base64.startswith("data:image/png"):
        mime = "image/png"
    elif body.image_base64.startswith("data:image/webp"):
        mime = "image/webp"
    prompt = ('Extract this receipt as JSON with this exact shape: '
              '{"merchant": string, "date": "YYYY-MM-DD" or null, "total": number, '
              '"items": [{"name": string, "price": number}]}. '
              'Only include line items and prices you can actually read. NEVER invent prices or a store name. '
              'If the image is not clearly a receipt, or you cannot read it, return {"merchant": "", "items": []} — do NOT guess. '
              'Respond with JSON only.')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}, {"inlineData": {"mimeType": mime, "data": b64}}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise HTTPException(resp.status_code, f"Gemini error: {resp.text}")
            data = resp.json()
            text = ""
            for cand in data.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    text += part.get("text", "")
            m = re.search(r"\{.*\}", text, re.S)
            parsed = json.loads(m.group(0)) if m else {"items": []}
    except Exception as e:
        logger.exception("receipt parse failed")
        raise HTTPException(500, f"Could not read receipt: {e}")
    parsed.setdefault("items", [])
    parsed.setdefault("merchant", "")
    return parsed


# ---------------------------------------------------------------------------
# AI Assistant with tools
# ---------------------------------------------------------------------------
AI_TOOLS = [
    {"type": "function", "function": {
        "name": "create_expense",
        "description": "Create an expense/purchase. Handles shared expenses and item-level splitting. Always compute gross total. For shared expenses, list all participants (use 'Me' for the owner Sá).",
        "parameters": {"type": "object", "properties": {
            "amount": {"type": "number", "description": "Total gross amount paid"},
            "merchant": {"type": "string"},
            "description": {"type": "string"},
            "category": {"type": "string", "description": "One of the finance categories e.g. Groceries, Eating Out, Transport"},
            "account": {"type": "string", "enum": ["cash", "revolut"]},
            "date": {"type": "string", "description": "yyyy-mm-dd, default today"},
            "participants": {"type": "array", "items": {"type": "string"}, "description": "All people sharing this expense including 'Me'"},
            "split_mode": {"type": "string", "enum": ["equal", "items", "exact"]},
            "items": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "price": {"type": "number"},
                "assigned": {"type": "array", "items": {"type": "string"}}}}},
            "exact_shares": {"type": "object", "description": "map of person name -> amount they owe"},
            "add_to_inventory": {"type": "boolean"},
        }, "required": ["amount"]},
    }},
    {"type": "function", "function": {
        "name": "record_payment",
        "description": "Record a reimbursement/settlement. direction 'in' = a person paid Sá back; 'out' = Sá paid someone.",
        "parameters": {"type": "object", "properties": {
            "person": {"type": "string"}, "amount": {"type": "number"},
            "method": {"type": "string", "enum": ["MB WAY", "Revolut", "Cash"]},
            "account": {"type": "string", "enum": ["cash", "revolut"]},
            "direction": {"type": "string", "enum": ["in", "out"]},
        }, "required": ["person", "amount"]},
    }},
    {"type": "function", "function": {
        "name": "create_person",
        "description": "Add a new person/contact.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "add_grocery",
        "description": "Add a grocery item to inventory with optional price and store.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "quantity": {"type": "number"}, "unit": {"type": "string"},
            "category": {"type": "string"}, "price": {"type": "number"}, "store": {"type": "string"}},
            "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "log_meal",
        "description": "Log a meal with estimated nutrition. Estimate calories/macros from the foods and quantities described.",
        "parameters": {"type": "object", "properties": {
            "description": {"type": "string"}, "calories": {"type": "number"},
            "protein": {"type": "number"}, "carbs": {"type": "number"}, "fat": {"type": "number"}},
            "required": ["description"]},
    }},
    {"type": "function", "function": {
        "name": "record_weight",
        "description": "Record a body weight measurement in kg.",
        "parameters": {"type": "object", "properties": {
            "weight": {"type": "number"}, "date": {"type": "string"}}, "required": ["weight"]},
    }},
    {"type": "function", "function": {
        "name": "create_task",
        "description": "Create a to-do task.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"}, "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            "due": {"type": "string"}}, "required": ["title"]},
    }},
    {"type": "function", "function": {
        "name": "get_financial_summary",
        "description": "Get current balances, monthly spending, reimbursements and who owes what.",
        "parameters": {"type": "object", "properties": {"month": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "get_people_balances",
        "description": "Get how much each person owes Sá and how much Sá owes them.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "update_expense",
        "description": "Modify an existing expense. Identify it by a text 'match' on its merchant/description. You can change amount, personal_amount, category, payment_method (cash or card), date or notes.",
        "parameters": {"type": "object", "properties": {
            "match": {"type": "string", "description": "Text to find the expense, e.g. 'restaurant' or 'Lidl'"},
            "amount": {"type": "number"}, "personal_amount": {"type": "number"},
            "category": {"type": "string"}, "payment_method": {"type": "string", "enum": ["cash", "card"]},
            "date": {"type": "string"}, "notes": {"type": "string"}, "description": {"type": "string"}},
            "required": ["match"]},
    }},
    {"type": "function", "function": {
        "name": "delete_expense",
        "description": "Delete an expense identified by a text 'match'. This is destructive: call first WITHOUT confirm to preview, then only call again with confirm=true after the user explicitly agrees.",
        "parameters": {"type": "object", "properties": {
            "match": {"type": "string"}, "confirm": {"type": "boolean"}}, "required": ["match"]},
    }},
    {"type": "function", "function": {
        "name": "mark_refunded",
        "description": "Record that a person refunded part or all of an expense. Links the refund to the matched expense so its remaining refund updates. direction is always 'in'.",
        "parameters": {"type": "object", "properties": {
            "match": {"type": "string", "description": "Text to find the expense being refunded"},
            "person": {"type": "string"}, "amount": {"type": "number"},
            "method": {"type": "string", "enum": ["MB WAY", "Revolut", "Cash"]},
            "account": {"type": "string", "enum": ["cash", "revolut"]}}, "required": ["person", "amount"]},
    }},
    {"type": "function", "function": {
        "name": "update_grocery",
        "description": "Update a grocery inventory item by name: change quantity/stock, price, unit, category, low_threshold or notes.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "quantity": {"type": "number"}, "price": {"type": "number"},
            "unit": {"type": "string"}, "category": {"type": "string"}, "low_threshold": {"type": "number"},
            "notes": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "generate_shopping_list",
        "description": "Build a shopping list from current inventory (low/out of stock) and the owner's usual buys, then return price intelligence and the cheaper store recommendation.",
        "parameters": {"type": "object", "properties": {"days": {"type": "number"}}},
    }},
    {"type": "function", "function": {
        "name": "create_recipe",
        "description": "Create a recipe with ingredients (name, quantity, unit) and optional nutrition per whole recipe.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "servings": {"type": "number"},
            "ingredients": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "quantity": {"type": "number"}, "unit": {"type": "string"}}}},
            "calories": {"type": "number"}, "protein": {"type": "number"}, "carbs": {"type": "number"}, "fat": {"type": "number"}},
            "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "cook_recipe",
        "description": "Cook a recipe by name: subtract its ingredients from grocery inventory and log a meal.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "log_workout",
        "description": "Log a completed workout session. type is Push/Pull/Legs or custom. Each exercise has a name, optional is_isometric, a duration in seconds (for isometrics like dead hang) and/or a list of sets with reps and weight (kg, 0 for bodyweight).",
        "parameters": {"type": "object", "properties": {
            "type": {"type": "string"}, "date": {"type": "string"},
            "exercises": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "is_isometric": {"type": "boolean"},
                "duration": {"type": "number"},
                "sets": {"type": "array", "items": {"type": "object", "properties": {
                    "reps": {"type": "number"}, "weight": {"type": "number"}}}}}}},
            "notes": {"type": "string"}}, "required": ["type"]},
    }},
]

AI_SYSTEM = f"""You are the intelligence layer of Life Manager, a private personal life-management app for its owner, {OWNER_NAME}.
You turn raw natural language into structured, connected data by calling tools. You handle money/expenses, shared expenses and reimbursements, groceries, meals/nutrition, workouts, weight and tasks.

Rules:
- When the owner refers to themselves, use the participant name "Me".
- Payment methods are "cash" and "card" (card = Revolut). When creating expenses, map card->account "revolut", cash->account "cash".
- For shared expenses, figure out each person's share. If items are assigned to specific people, use split_mode "items" with the items array. If the split is equal, use split_mode "equal". Never fabricate amounts you weren't given.
- To change an existing expense use update_expense; to remove one use delete_expense (preview first, then confirm). To record a refund use mark_refunded (or record_payment for a general person payment).
- NEVER invent expenses, refunds, prices, grocery prices, or totals. If you don't have a value, say it is unknown and ask.
- If something is genuinely ambiguous and financially important (who to split with, or an amount), ASK a short clarifying question instead of guessing.
- For destructive actions (delete, large bulk changes) always confirm with the user first.
- For nutrition you MAY estimate calories/macros from typical food values, but say they are estimates.
- After performing actions, give a concise summary of exactly what changed (amounts, shares, refunds, remaining owed, inventory). Be warm but brief. Use € for currency.
- Today's date is {{today}}.
"""


async def find_expense(match: str, db) -> Optional[Transaction]:
    match = (match or "").strip()
    if not match:
        result = await db.execute(select(Transaction).where(Transaction.type == "expense").order_by(desc(Transaction.date)).limit(1))
        return result.scalar_one_or_none()
    result = await db.execute(
        select(Transaction)
        .where(Transaction.type == "expense",
               (Transaction.merchant.ilike(f"%{match}%")) |
               (Transaction.description.ilike(f"%{match}%")) |
               (Transaction.category.ilike(f"%{match}%")))
        .order_by(desc(Transaction.date))
        .limit(1))
    return result.scalar_one_or_none()


async def dispatch_tool(name: str, args: dict, created: list, db) -> dict:
    try:
        if name == "create_expense":
            body = ExpenseBody(
                amount=args.get("amount"), merchant=args.get("merchant", ""),
                description=args.get("description", "") or args.get("merchant", ""),
                category=args.get("category", "Other"), account=args.get("account", "cash"),
                date=args.get("date"), participants=args.get("participants", ["Me"]),
                split_mode=args.get("split_mode", "equal"),
                items=[ItemBody(**i) for i in args.get("items", [])],
                exact_shares=args.get("exact_shares", {}) or {},
                add_to_inventory=args.get("add_to_inventory", False),
            )
            res = await create_expense_record(body, db)
            created.append({"collection": "transactions", "id": res["transaction"]["id"]})
            return res
        if name == "record_payment":
            s = await add_settlement(SettlementBody(
                person=args["person"], amount=args["amount"], method=args.get("method", "Revolut"),
                account=args.get("account", "revolut"), direction=args.get("direction", "in")), {"id": "ai"}, db)
            created.append({"collection": "settlements", "id": s["id"]})
            return s
        if name == "create_person":
            p = await resolve_person(args["name"], db)
            return p
        if name == "add_grocery":
            g = await add_grocery(GroceryBody(**{k: v for k, v in args.items() if k in GroceryBody.model_fields}), {"id": "ai"}, db)
            if g.get("id"):
                created.append({"collection": "groceries", "id": g["id"]})
            return g
        if name == "log_meal":
            m = await add_meal(MealBody(**{k: v for k, v in args.items() if k in MealBody.model_fields}), {"id": "ai"}, db)
            created.append({"collection": "meals", "id": m["id"]})
            return m
        if name == "record_weight":
            w = await add_weight(WeightBody(weight=args["weight"], date=args.get("date")), {"id": "ai"}, db)
            created.append({"collection": "weight", "id": w["id"]})
            return w
        if name == "create_task":
            t = await create_task(TaskBody(title=args["title"], priority=args.get("priority", "normal"), due=args.get("due")), {"id": "ai"}, db)
            created.append({"collection": "tasks", "id": t["id"]})
            return t
        if name == "get_financial_summary":
            return await analytics_summary(month=args.get("month"), user={"id": "ai"}, db=db)
        if name == "get_people_balances":
            return await people_balances(db)
        if name == "update_expense":
            t = await find_expense(args.get("match", ""), db)
            if not t:
                return {"error": f"No expense found matching '{args.get('match')}'"}
            upd = TxnUpdate(amount=args.get("amount"), personal_amount=args.get("personal_amount"),
                            category=args.get("category"), payment_method=args.get("payment_method"),
                            date=args.get("date"), notes=args.get("notes"), description=args.get("description"))
            res = await update_transaction(t.id, upd, {"id": "ai"}, db)
            return {"updated": res}
        if name == "delete_expense":
            t = await find_expense(args.get("match", ""), db)
            if not t:
                return {"error": f"No expense found matching '{args.get('match')}'"}
            if not args.get("confirm"):
                return {"needs_confirmation": True,
                        "message": f"This will permanently delete '{t.merchant or t.description}' (€{t.gross_amount}) from {t.date}. Ask the user to confirm before deleting."}
            await delete_transaction(t.id, {"id": "ai"}, db)
            return {"deleted": t.merchant or t.description, "amount": t.gross_amount}
        if name == "mark_refunded":
            tid = None
            if args.get("match"):
                t = await find_expense(args["match"], db)
                tid = t.id if t else None
            s = await add_settlement(SettlementBody(
                person=args["person"], amount=args["amount"], method=args.get("method", "Revolut"),
                account=args.get("account", "revolut"), direction="in", transaction_id=tid), {"id": "ai"}, db)
            created.append({"collection": "settlements", "id": s["id"]})
            return {"settlement": s, "linked_to_expense": tid is not None}
        if name == "update_grocery":
            result = await db.execute(select(Grocery).where(Grocery.name_lower == args["name"].lower()))
            g = result.scalar_one_or_none()
            if not g:
                return {"error": f"No grocery item named '{args['name']}'"}
            upd = GroceryUpdate(**{k: v for k, v in args.items() if k in GroceryUpdate.model_fields and k != "name"})
            res = await update_grocery(g.id, upd, {"id": "ai"}, db)
            return {"updated": res}
        if name == "generate_shopping_list":
            return await generate_shopping_doc(int(args.get("days", 7)), db)
        if name == "create_recipe":
            body = RecipeBody(name=args["name"], servings=int(args.get("servings", 1)),
                              ingredients=[RecipeIngredient(**i) for i in args.get("ingredients", [])],
                              calories=args.get("calories"), protein=args.get("protein"),
                              carbs=args.get("carbs"), fat=args.get("fat"))
            r = await create_recipe(body, {"id": "ai"}, db)
            created.append({"collection": "recipes", "id": r["id"]})
            return r
        if name == "cook_recipe":
            result = await db.execute(
                select(Recipe).where(func.lower(Recipe.name) == args["name"].lower()))
            r = result.scalar_one_or_none()
            if not r:
                return {"error": f"No recipe named '{args['name']}'"}
            return await cook_recipe_doc({"id": r.id, "name": r.name, "servings": r.servings,
                                           "ingredients": r.ingredients or [], "calories": r.calories,
                                           "protein": r.protein, "carbs": r.carbs, "fat": r.fat,
                                           "notes": r.notes}, db)
        if name == "log_workout":
            body = WorkoutBody(
                type=args.get("type", "Push"), date=args.get("date"), notes=args.get("notes", ""),
                exercises=[WorkoutExercise(name=e["name"], is_isometric=e.get("is_isometric", False),
                                           duration=e.get("duration"),
                                           sets=[WorkoutSet(**s) for s in e.get("sets", [])]) for e in args.get("exercises", [])])
            w = await create_workout(body, db)
            created.append({"collection": "workouts", "id": w["id"]})
            return w
    except Exception as e:
        logger.exception("tool error")
        return {"error": str(e)}
    return {"error": "unknown tool"}


def _to_gemini_tools(tools):
    decls = []
    for t in tools:
        fn = t.get("function", t) if isinstance(t, dict) else t
        if "function" in t:
            fn = t["function"]
        decls.append({"name": fn["name"], "description": fn["description"], "parameters": fn["parameters"]})
    return [{"functionDeclarations": decls}]


def _build_contents(session_id, history, user_msg, image_b64=None):
    contents = []
    for h in history:
        role = "user" if h["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h["text"]}]})
    parts = [{"text": user_msg}]
    if image_b64:
        b64 = image_b64.split(",")[-1]
        mime = "image/jpeg"
        if image_b64.startswith("data:image/png"):
            mime = "image/png"
        elif image_b64.startswith("data:image/webp"):
            mime = "image/webp"
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})
    contents.append({"role": "user", "parts": parts})
    return contents


@api_router.post("/ai/chat")
async def ai_chat(body: AIChatBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    if not GOOGLE_API_KEY:
        raise HTTPException(503, "Google API key not configured")

    session_id = body.session_id or new_id()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d (%A)")
    system = AI_SYSTEM.replace("{today}", today)

    result = await db.execute(select(AIMessage).where(AIMessage.session_id == session_id).order_by(asc(AIMessage.created_at)))
    history = [{"role": m.role, "text": m.text} for m in result.scalars().all()]

    user_msg = body.message
    if history:
        convo = "\n".join(f"{h['role']}: {h['text']}" for h in history[-12:])
        user_msg = f"Recent conversation so far:\n{convo}\n\nNew message from {OWNER_NAME}: {body.message}"

    contents = _build_contents(session_id, history, user_msg, body.image_base64)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_API_KEY}"

    created = []
    tool_summary = []
    reply = ""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            payload = {"systemInstruction": {"parts": [{"text": system}]},
                       "contents": contents, "tools": _to_gemini_tools(AI_TOOLS),
                       "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}}}
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise HTTPException(response.status_code, f"Gemini error: {response.text}")
            data = response.json()
            guard = 0
            while guard < 6:
                guard += 1
                candidate = data.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                tool_calls = [p["functionCall"] for p in parts if p.get("functionCall")]
                text_parts = [p.get("text", "") for p in parts if p.get("text")]
                reply = "\n".join(text_parts).strip()
                if not tool_calls:
                    break
                # append model function calls
                contents.append({"role": "model", "parts": [{"functionCall": tc} for tc in tool_calls]})
                # append user function responses
                for tc in tool_calls:
                    args = tc.get("args", {})
                    result = await dispatch_tool(tc["name"], args, created, db)
                    tool_summary.append({"tool": tc["name"], "args": args})
                    contents.append({"role": "user", "parts": [{"functionResponse": {"name": tc["name"], "response": result}}]})
                response = await client.post(url, json={"systemInstruction": {"parts": [{"text": system}]},
                                                          "contents": contents, "tools": _to_gemini_tools(AI_TOOLS),
                                                          "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}}})
                if response.status_code != 200:
                    raise HTTPException(response.status_code, f"Gemini error: {response.text}")
                data = response.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("ai chat failed")
        raise HTTPException(500, f"AI request failed: {e}")

    db.add(AIMessage(id=new_id(), session_id=session_id, role="user", text=body.message, created_at=now_iso()))
    db.add(AIMessage(id=new_id(), session_id=session_id, role="assistant", text=reply or "", created_at=now_iso()))

    if tool_summary:
        label = reply[:140] if reply else (tool_summary[0]["tool"].replace("_", " ").title())
        db.add(AIAction(
            id=new_id(), label=label,
            tools=[t["tool"] for t in tool_summary], created=created,
            undoable=len(created) > 0, undone=False, created_at=now_iso()))

    await db.commit()
    return {"reply": reply, "session_id": session_id, "actions": tool_summary, "changed": len(created) > 0 or len(tool_summary) > 0}


@api_router.get("/ai/history")
async def ai_history(session_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(AIMessage).where(AIMessage.session_id == session_id).order_by(asc(AIMessage.created_at)))
    return [{"id": m.id, "session_id": m.session_id, "role": m.role, "text": m.text, "created_at": m.created_at}
            for m in result.scalars().all()]


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------
async def seed():
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == admin_email))
        user = result.scalar_one_or_none()
        if not user:
            db.add(User(id=new_id(), email=admin_email, password_hash=hash_password(admin_pw),
                        name=OWNER_NAME, role="owner", created_at=now_iso()))
        elif not verify_password(admin_pw, user.password_hash):
            user.password_hash = hash_password(admin_pw)
        await db.commit()

        result = await db.execute(select(func.count()).select_from(Category))
        if result.scalar() == 0:
            cats = [
                ("Groceries", "shopping-cart", "#10B981"), ("Eating Out", "utensils", "#F59E0B"),
                ("Transport", "bus", "#6366F1"), ("Shopping", "shopping-bag", "#EC4899"),
                ("Entertainment", "clapperboard", "#8B5CF6"), ("Work", "briefcase", "#0EA5E9"),
                ("Fitness", "dumbbell", "#059669"), ("Health", "heart-pulse", "#EF4444"),
                ("Travel", "plane", "#14B8A6"), ("Subscriptions", "repeat", "#F97316"),
                ("Bills", "receipt", "#64748B"), ("Other", "circle", "#94A3B8"),
            ]
            for n, i, c in cats:
                db.add(Category(id=new_id(), name=n, icon=i, color=c, created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(Account))
        if result.scalar() == 0:
            db.add(Account(id="cash", name="Cash", type="cash", opening_balance=120.0, created_at=now_iso()))
            db.add(Account(id="revolut", name="Revolut", type="revolut", opening_balance=640.0, created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(Person))
        if result.scalar() == 0:
            for n in ["Ferreira", "Broca", "Sebas", "Mariana", "Faia"]:
                db.add(Person(id=new_id(), name=n, name_lower=n.lower(),
                              photo=None, notes="", payment_preference="", created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(Transaction))
        if result.scalar() == 0:
            await seed_transactions(db)

        result = await db.execute(select(func.count()).select_from(Task))
        if result.scalar() == 0:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            for title, pr in [("Record weekly weight", "high"), ("Pull workout", "normal"),
                              ("Ask Ferreira for payment", "normal"), ("Buy eggs and milk", "low")]:
                db.add(Task(id=new_id(), title=title, priority=pr, due=today,
                            recurring=None, done=False, created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(WeightEntry))
        if result.scalar() == 0:
            base = datetime.now(timezone.utc) - timedelta(weeks=6)
            weights = [81.2, 81.6, 82.0, 82.3, 82.7, 83.0]
            for i, w in enumerate(weights):
                d = (base + timedelta(weeks=i)).strftime("%Y-%m-%d")
                db.add(WeightEntry(id=new_id(), weight=w, date=d, note="Weekly check-in", created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(Grocery))
        if result.scalar() == 0:
            gs = [("Eggs", 3, "unit", "Eggs", 3.49, "Lidl", 6), ("Milk", 1, "L", "Dairy", 0.89, "Mercadona", 2),
                  ("Chicken breast", 600, "g", "Meat", 5.20, "Mercadona", 200), ("Tuna", 4, "can", "Fish", 3.29, "Supeco", 2),
                  ("Gouda", 200, "g", "Dairy", 4.98, "Lidl", 100), ("Rice", 1000, "g", "Carbohydrates", None, None, 300),
                  ("Bread", 1, "unit", "Carbohydrates", 0.95, "Lidl", 1)]
            for n, q, u, c, p, s, lt in gs:
                db.add(Grocery(id=new_id(), name=n, name_lower=n.lower(), quantity=q,
                               unit=u, category=c, price=p, store=s, low_threshold=lt,
                               notes="", expiration=None,
                               created_at=now_iso(), updated_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(PriceRecord))
        if result.scalar() == 0:
            pr = [
                ("Eggs", "Lidl", 3.49, "2025-09-25"), ("Eggs", "Mercadona", 3.89, "2025-09-17"), ("Eggs", "Supeco", 3.29, "2025-09-10"),
                ("Milk", "Mercadona", 0.89, "2025-09-17"), ("Milk", "Lidl", 0.95, "2025-09-25"),
                ("Chicken breast", "Mercadona", 5.20, "2025-10-08"), ("Chicken breast", "Lidl", 5.60, "2025-11-04"),
                ("Tuna", "Supeco", 3.29, "2025-09-10"), ("Tuna", "Lidl", 2.99, "2025-11-04"), ("Tuna", "Mercadona", 3.49, "2025-10-08"),
                ("Gouda", "Lidl", 4.98, "2025-09-25"), ("Gouda", "Mercadona", 5.20, "2025-10-08"),
                ("Bread", "Lidl", 0.95, "2025-11-04"), ("Bread", "Mercadona", 1.10, "2025-10-08"),
            ]
            for n, s, p, d in pr:
                db.add(PriceRecord(id=new_id(), name=n, name_lower=n.lower(), store=s,
                                   price=p, unit="unit", date=d, created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(Recipe))
        if result.scalar() == 0:
            db.add(Recipe(id=new_id(), name="Protein scramble", servings=1,
                          ingredients=[{"name": "Eggs", "quantity": 3, "unit": "unit"},
                                       {"name": "Gouda", "quantity": 30, "unit": "g"},
                                       {"name": "Bread", "quantity": 1, "unit": "unit"}],
                          calories=520, protein=34, carbs=30, fat=28,
                          notes="Quick high-protein breakfast.", created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(Meal))
        if result.scalar() == 0:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            db.add(Meal(id=new_id(), description="Oats, whey & banana", date=today, calories=520, protein=38, carbs=68, fat=12, created_at=now_iso()))
            db.add(Meal(id=new_id(), description="200g alcatra, 3 eggs, 300ml milk", date=today, calories=690, protein=62, carbs=14, fat=42, created_at=now_iso()))
            await db.commit()

        result = await db.execute(select(func.count()).select_from(Workout))
        if result.scalar() == 0:
            now = datetime.now(timezone.utc)
            db.add(Workout(id=new_id(), type="Pull", date=(now - timedelta(days=3)).strftime("%Y-%m-%d"), notes="",
                           exercises=[
                               {"name": "Pull-ups", "is_isometric": False, "duration": None, "note": "", "sets": [{"reps": 8, "weight": 0}, {"reps": 7, "weight": 0}, {"reps": 6, "weight": 0}]},
                               {"name": "Rows", "is_isometric": False, "duration": None, "note": "", "sets": [{"reps": 10, "weight": 20}, {"reps": 10, "weight": 20}, {"reps": 9, "weight": 20}]},
                               {"name": "Dead hang", "is_isometric": True, "duration": 45, "note": "", "sets": []},
                           ], created_at=now_iso()))
            db.add(Workout(id=new_id(), type="Push", date=(now - timedelta(days=1)).strftime("%Y-%m-%d"), notes="",
                           exercises=[
                               {"name": "Dips", "is_isometric": False, "duration": None, "note": "", "sets": [{"reps": 12, "weight": 0}, {"reps": 11, "weight": 0}, {"reps": 10, "weight": 0}]},
                               {"name": "Push-ups", "is_isometric": False, "duration": None, "note": "", "sets": [{"reps": 15, "weight": 0}, {"reps": 15, "weight": 0}]},
                           ], created_at=now_iso()))
            await db.commit()

    # write test credentials
    try:
        cred_path = Path("/app/memory/test_credentials.md")
        cred_path.parent.mkdir(parents=True, exist_ok=True)
        cred_path.write_text(
            f"# Test Credentials\n\n## Owner account (JWT email+password)\n"
            f"- Email: {admin_email}\n- Password: {admin_pw}\n- Name: {OWNER_NAME}\n\n"
            f"## Auth endpoints\n- POST /api/auth/login (body: email, password) -> returns token\n"
            f"- GET /api/auth/me (Authorization: Bearer <token>)\n\n"
            f"Token is returned in login response body and sent as `Authorization: Bearer <token>`.\n")
    except Exception:
        pass


async def seed_transactions(db):
    result = await db.execute(select(Person))
    people = result.scalars().all()
    pmap = {p.name: p for p in people}

    async def exp(amount, merchant, cat, account, date, participants=None, items=None, split_mode="equal", desc=""):
        body = ExpenseBody(amount=amount, merchant=merchant, description=desc or merchant, category=cat,
                           account=account, date=date, participants=participants or ["Me"],
                           items=[ItemBody(**i) for i in items] if items else [],
                           split_mode=split_mode)
        await create_expense_record(body, db)

    await exp(26.10, "Lidl", "Groceries", "revolut", "2025-09-25",
              participants=["Me", "Ferreira", "Broca", "Sebas", "Mariana"], split_mode="items",
              items=[{"name": "Potatoes", "price": 3.58, "assigned": ["Me", "Ferreira", "Broca", "Sebas", "Mariana"]},
                     {"name": "Onion", "price": 1.69, "assigned": ["Me", "Ferreira", "Broca", "Sebas", "Mariana"]},
                     {"name": "Bread", "price": 1.20, "assigned": ["Me", "Ferreira", "Broca", "Sebas", "Mariana"]},
                     {"name": "Big escalopín", "price": 6.90, "assigned": ["Me", "Ferreira", "Broca", "Sebas", "Mariana"]},
                     {"name": "Juice", "price": 1.13, "assigned": ["Broca"]},
                     {"name": "Powdered cheese", "price": 0.95, "assigned": ["Me"]},
                     {"name": "Gouda", "price": 4.98, "assigned": ["Me"]},
                     {"name": "Small escalopín", "price": 3.18, "assigned": ["Me"]},
                     {"name": "Chow Mein", "price": 0.49, "assigned": ["Me"]}])
    await exp(14.00, "McDonald's", "Eating Out", "cash", "2025-09-12")
    await exp(38.90, "Mercadona", "Groceries", "revolut", "2025-09-17")
    await exp(9.50, "Selecta", "Eating Out", "cash", "2025-09-20", participants=["Me", "Sebas"], split_mode="equal")
    await exp(22.40, "Supeco", "Groceries", "revolut", "2025-09-10")

    await exp(11.80, "Popeyes", "Eating Out", "cash", "2025-10-03", participants=["Me", "Faia"], split_mode="equal")
    await exp(41.20, "Mercadona", "Groceries", "revolut", "2025-10-08")
    await exp(6.30, "MAS", "Groceries", "cash", "2025-10-11")
    await exp(19.99, "Netflix & Spotify", "Subscriptions", "revolut", "2025-10-01")
    await exp(15.50, "Uber", "Transport", "revolut", "2025-10-15", participants=["Me", "Broca", "Mariana"], split_mode="equal")

    await exp(27.60, "Lidl", "Groceries", "revolut", "2025-11-04")
    await exp(13.20, "McDonald's", "Eating Out", "cash", "2025-11-09", participants=["Me", "Ferreira"], split_mode="equal")
    await exp(52.00, "Decathlon", "Fitness", "revolut", "2025-11-12")

    now = datetime.now(timezone.utc)
    d0 = now.strftime("%Y-%m-%d")
    d2 = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    d5 = (now - timedelta(days=5)).strftime("%Y-%m-%d")
    await exp(8.60, "Mercadona", "Groceries", "cash", d0)
    await exp(23.40, "Lidl", "Groceries", "revolut", d2, participants=["Me", "Broca"], split_mode="equal")
    await exp(6.90, "McDonald's", "Eating Out", "cash", d5)

    ferreira = pmap.get("Ferreira")
    if ferreira:
        db.add(Settlement(id=new_id(), person_id=ferreira.id, person_name="Ferreira",
                          amount=5.00, method="Revolut", account="revolut",
                          direction="in", date="2025-10-20", transaction_id=None, created_at=now_iso()))
        await db.commit()


@api_router.get("/")
async def root():
    return {"app": "Life Manager", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

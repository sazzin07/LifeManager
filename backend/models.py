from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(String(50), nullable=False)


class Person(Base):
    __tablename__ = "people"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False, index=True)
    photo = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    payment_preference = Column(String(100), nullable=True)
    created_at = Column(String(50), nullable=False)


class Category(Base):
    __tablename__ = "categories"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    icon = Column(String(100), nullable=False)
    color = Column(String(20), nullable=False)
    created_at = Column(String(50), nullable=False)


class Account(Base):
    __tablename__ = "accounts"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    opening_balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(String(50), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False, index=True)
    gross_amount = Column(Float, nullable=False, default=0.0)
    personal_amount = Column(Float, nullable=False, default=0.0)
    reimbursable_amount = Column(Float, nullable=False, default=0.0)
    description = Column(Text, nullable=True)
    category = Column(String(255), nullable=True)
    account = Column(String(100), nullable=True, index=True)
    merchant = Column(Text, nullable=True)
    date = Column(String(10), nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    paid_by = Column(String(36), nullable=True, index=True)
    items = Column(JSON, nullable=True)
    created_at = Column(String(50), nullable=False)

    splits = relationship("Split", back_populates="transaction", cascade="all, delete-orphan", lazy="selectin")


class Split(Base):
    __tablename__ = "splits"
    id = Column(String(36), primary_key=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(String(36), nullable=False, index=True)
    person_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    is_me = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(50), nullable=False)

    transaction = relationship("Transaction", back_populates="splits")


class Settlement(Base):
    __tablename__ = "settlements"
    id = Column(String(36), primary_key=True)
    person_id = Column(String(36), nullable=False, index=True)
    person_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    method = Column(String(100), nullable=False)
    account = Column(String(100), nullable=False)
    direction = Column(String(10), nullable=False)
    date = Column(String(10), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(String(50), nullable=False)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False)
    priority = Column(String(50), nullable=False, default="normal")
    due = Column(String(10), nullable=True)
    recurring = Column(String(100), nullable=True)
    done = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(50), nullable=False)


class WeightEntry(Base):
    __tablename__ = "weight_entries"
    id = Column(String(36), primary_key=True)
    weight = Column(Float, nullable=False)
    date = Column(String(10), nullable=False, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False)


class Workout(Base):
    __tablename__ = "workouts"
    id = Column(String(36), primary_key=True)
    type = Column(String(100), nullable=False)
    date = Column(String(10), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    exercises = Column(JSON, nullable=True)
    created_at = Column(String(50), nullable=False)


class Photo(Base):
    __tablename__ = "photos"
    id = Column(String(36), primary_key=True)
    storage_path = Column(String(500), nullable=False, unique=True, index=True)
    content_type = Column(String(100), nullable=False)
    note = Column(Text, nullable=True)
    date = Column(String(10), nullable=False, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(50), nullable=False)


class Grocery(Base):
    __tablename__ = "groceries"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String(50), nullable=False, default="unit")
    category = Column(String(255), nullable=True)
    price = Column(Float, nullable=True)
    store = Column(String(255), nullable=True)
    low_threshold = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    expiration = Column(String(10), nullable=True)
    created_at = Column(String(50), nullable=False)
    updated_at = Column(String(50), nullable=False)


class PriceRecord(Base):
    __tablename__ = "price_records"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False, index=True)
    store = Column(String(255), nullable=True)
    price = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False, default="unit")
    date = Column(String(10), nullable=False, index=True)
    created_at = Column(String(50), nullable=False)


class ShoppingItem(Base):
    __tablename__ = "shopping_items"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_lower = Column(String(255), nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=1.0)
    unit = Column(String(50), nullable=False, default="unit")
    note = Column(Text, nullable=True)
    bought = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(50), nullable=False)


class Meal(Base):
    __tablename__ = "meals"
    id = Column(String(36), primary_key=True)
    description = Column(Text, nullable=False)
    date = Column(String(10), nullable=False, index=True)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    created_at = Column(String(50), nullable=False)


class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    servings = Column(Integer, nullable=False, default=1)
    ingredients = Column(JSON, nullable=True)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False)


class AIAction(Base):
    __tablename__ = "ai_actions"
    id = Column(String(36), primary_key=True)
    label = Column(String(500), nullable=False)
    tools = Column(JSON, nullable=True)
    created = Column(JSON, nullable=True)
    undoable = Column(Boolean, nullable=False, default=False)
    undone = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(50), nullable=False)


class AIMessage(Base):
    __tablename__ = "ai_messages"
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(String(50), nullable=False)

    __table_args__ = (Index("ix_ai_messages_session_created", "session_id", "created_at"),)

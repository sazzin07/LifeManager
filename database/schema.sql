-- LifeManager MySQL schema
-- Run this against your MySQL 8.0 instance before starting the backend,
-- or let SQLAlchemy create the tables automatically on startup.

CREATE DATABASE IF NOT EXISTS lifemanager
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE lifemanager;

CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS people (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_lower VARCHAR(255) NOT NULL,
    photo TEXT,
    notes TEXT,
    payment_preference VARCHAR(100),
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_people_name_lower (name_lower)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS categories (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(100) NOT NULL,
    color VARCHAR(20) NOT NULL,
    created_at VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS accounts (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    opening_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transactions (
    id CHAR(36) PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    gross_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    personal_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    reimbursable_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    description TEXT,
    category VARCHAR(255),
    account VARCHAR(100),
    merchant TEXT,
    date CHAR(10) NOT NULL,
    month CHAR(7) NOT NULL,
    notes TEXT,
    paid_by CHAR(36),
    items JSON,
    from_account VARCHAR(100),
    to_account VARCHAR(100),
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_transactions_type (type),
    INDEX ix_transactions_account (account),
    INDEX ix_transactions_date (date),
    INDEX ix_transactions_month (month),
    INDEX ix_transactions_paid_by (paid_by),
    INDEX ix_transactions_from_account (from_account),
    INDEX ix_transactions_to_account (to_account)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS splits (
    id CHAR(36) PRIMARY KEY,
    transaction_id CHAR(36) NOT NULL,
    person_id CHAR(36) NOT NULL,
    person_name VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    is_me BOOLEAN NOT NULL DEFAULT FALSE,
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_splits_transaction_id (transaction_id),
    INDEX ix_splits_person_id (person_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS settlements (
    id CHAR(36) PRIMARY KEY,
    person_id CHAR(36) NOT NULL,
    person_name VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    method VARCHAR(100) NOT NULL,
    account VARCHAR(100) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    date CHAR(10) NOT NULL,
    transaction_id CHAR(36),
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_settlements_person_id (person_id),
    INDEX ix_settlements_date (date),
    INDEX ix_settlements_transaction_id (transaction_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tasks (
    id CHAR(36) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    priority VARCHAR(50) NOT NULL DEFAULT 'normal',
    due CHAR(10),
    recurring VARCHAR(100),
    done BOOLEAN NOT NULL DEFAULT FALSE,
    created_at VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS weight_entries (
    id CHAR(36) PRIMARY KEY,
    weight DECIMAL(6,2) NOT NULL,
    date CHAR(10) NOT NULL,
    note TEXT,
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_weight_entries_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workouts (
    id CHAR(36) PRIMARY KEY,
    type VARCHAR(100) NOT NULL,
    date CHAR(10) NOT NULL,
    notes TEXT,
    exercises JSON,
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_workouts_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS photos (
    id CHAR(36) PRIMARY KEY,
    storage_path VARCHAR(500) NOT NULL UNIQUE,
    content_type VARCHAR(100) NOT NULL,
    note TEXT,
    date CHAR(10) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_photos_storage_path (storage_path),
    INDEX ix_photos_date (date),
    INDEX ix_photos_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS groceries (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_lower VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    unit VARCHAR(50) NOT NULL DEFAULT 'unit',
    category VARCHAR(255),
    price DECIMAL(10,2),
    store VARCHAR(255),
    low_threshold DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    notes TEXT,
    expiration CHAR(10),
    created_at VARCHAR(50) NOT NULL,
    updated_at VARCHAR(50) NOT NULL,
    INDEX ix_groceries_name_lower (name_lower)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS price_records (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_lower VARCHAR(255) NOT NULL,
    store VARCHAR(255),
    price DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50) NOT NULL DEFAULT 'unit',
    date CHAR(10) NOT NULL,
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_price_records_name_lower (name_lower),
    INDEX ix_price_records_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS shopping_items (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    name_lower VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL DEFAULT 1.00,
    unit VARCHAR(50) NOT NULL DEFAULT 'unit',
    note TEXT,
    bought BOOLEAN NOT NULL DEFAULT FALSE,
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_shopping_items_name_lower (name_lower)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS meals (
    id CHAR(36) PRIMARY KEY,
    description TEXT NOT NULL,
    date CHAR(10) NOT NULL,
    calories DECIMAL(8,2),
    protein DECIMAL(8,2),
    carbs DECIMAL(8,2),
    fat DECIMAL(8,2),
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_meals_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recipes (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    servings INT NOT NULL DEFAULT 1,
    ingredients JSON,
    calories DECIMAL(8,2),
    protein DECIMAL(8,2),
    carbs DECIMAL(8,2),
    fat DECIMAL(8,2),
    notes TEXT,
    created_at VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_actions (
    id CHAR(36) PRIMARY KEY,
    label VARCHAR(500) NOT NULL,
    tools JSON,
    created JSON,
    undoable BOOLEAN NOT NULL DEFAULT FALSE,
    undone BOOLEAN NOT NULL DEFAULT FALSE,
    created_at VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_messages (
    id CHAR(36) PRIMARY KEY,
    session_id CHAR(36) NOT NULL,
    role VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    created_at VARCHAR(50) NOT NULL,
    INDEX ix_ai_messages_session_id (session_id),
    INDEX ix_ai_messages_session_created (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

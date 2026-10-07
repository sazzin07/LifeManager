# LifeManager

A private, single-user personal life-management application — forked and migrated from **LifeRecord** to run completely independently of Emergent, with **MySQL** as the primary database and **phpMyAdmin** for database management.

> **Migration, not redesign.** LifeManager preserves the original LifeRecord UI/UX, routes, components, and business logic while replacing the MongoDB/Emergent backend with a self-contained FastAPI + MySQL stack.

---

## Requirements

- **Node.js** 18+ (tested with Node 24 / npm 10)
- **Yarn** 1.22+ (or npm)
- **Python** 3.11+
- **MySQL** 8.0+ (local install, or Docker on a machine with Docker available)
- **phpMyAdmin** (included in `docker-compose.yml`, or installable standalone with PHP)

---

## Installation

### 1. Clone / locate the project

```bash
cd C:\Projects\LifeManager
```

### 2. Configure environment variables

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `.env` and `backend/.env` with real credentials:

- `MYSQL_PASSWORD` — a strong MySQL user password
- `JWT_SECRET` — a long random string for signing tokens
- `ADMIN_PASSWORD` — password for the seeded owner account (`sa@lifemanager.app`)
- `GOOGLE_API_KEY` (optional) — for AI assistant / receipt scan
- `OPENAI_API_KEY` (optional) — for voice transcription

### 3. Start MySQL + phpMyAdmin

If you have Docker:

```bash
docker-compose up -d
```

Otherwise install MySQL locally and create the database:

```sql
CREATE DATABASE lifemanager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'lifemanager'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON lifemanager.* TO 'lifemanager'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Import the schema

```bash
mysql -u lifemanager -p lifemanager < database/schema.sql
```

Or import `database/schema.sql` through phpMyAdmin (http://localhost:8080).

### 5. Install backend dependencies

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 6. Install frontend dependencies

```bash
cd ..\frontend
yarn install
```

---

## Running the application

### Database + phpMyAdmin (Docker)

```bash
docker-compose up -d
```

- phpMyAdmin: http://localhost:8080
- MySQL: `localhost:3306`

### Database + phpMyAdmin (without Docker)

If Docker is unavailable, you can run MySQL and phpMyAdmin directly:

1. Install and start MySQL 8.0+ locally.
2. Create the database and user (see Installation step 3).
3. Install PHP 8.2+ and download [phpMyAdmin](https://www.phpmyadmin.net/downloads/).
4. Place phpMyAdmin in a `phpmyadmin/` folder at the project root and create a minimal `phpmyadmin/config.inc.php`:

```php
<?php
$cfg['blowfish_secret'] = 'your_random_secret_here';
$i = 1;
$cfg['Servers'][$i]['auth_type'] = 'cookie';
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['port'] = '3306';
```

5. Start the PHP built-in server:

```bash
cd phpmyadmin
php -S 0.0.0.0:8080
```

phpMyAdmin will be available at http://localhost:8080.

### Backend

```bash
cd backend
.venv\Scripts\activate
uvicorn server:app --reload --port 8000
```

The API is available at http://localhost:8000/api.

### Frontend

```bash
cd frontend
yarn start
```

The app opens at http://localhost:3000.

Default owner credentials:

- Email: `sa@lifemanager.app`
- Password: the value you set in `ADMIN_PASSWORD`

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `MYSQL_HOST` | MySQL host (default `localhost`) |
| `MYSQL_PORT` | MySQL port (default `3306`) |
| `MYSQL_DATABASE` | Database name (`lifemanager`) |
| `MYSQL_USER` | MySQL user |
| `MYSQL_PASSWORD` | MySQL password |
| `JWT_SECRET` | Secret for JWT token signing |
| `ADMIN_EMAIL` | Seeded owner email |
| `ADMIN_PASSWORD` | Seeded owner password |
| `OWNER_NAME` | Display name for the owner (default `Sá`) |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `GOOGLE_API_KEY` | Optional. Required for AI chat / receipt parsing |
| `OPENAI_API_KEY` | Optional. Required for voice transcription |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `REACT_APP_BACKEND_URL` | Backend URL (default `http://localhost:8000`) |

---

## Database

- **Database name:** `lifemanager`
- **Schema file:** `database/schema.sql`
- **Management:** phpMyAdmin at http://localhost:8080 (Docker) or your local MySQL client

The backend auto-seeds required reference data on startup (owner user, default categories, Cash/Revolut accounts, sample people, transactions, tasks, weight, groceries, recipes, meals, workouts) when tables are empty.

---

## Testing

### Backend tests

With the backend running:

```bash
cd backend
pytest tests/
```

### Frontend build verification

```bash
cd frontend
yarn build
```

---

## Architecture

```
React Frontend (localhost:3000)
    │  Bearer JWT + JSON over HTTP
    ▼
FastAPI Backend (localhost:8000/api)
    │  SQLAlchemy async + aiomysql
    ▼
MySQL Database (localhost:3306 / lifemanager)
```

### Optional external services

- **Google Gemini API** — powers the AI assistant and receipt scanning
- **OpenAI Whisper API** — powers voice-to-text
- **phpMyAdmin** — local database management UI

If AI keys are not provided, the rest of the application works normally; AI endpoints return a clear `503` error explaining the missing key.

---

## What changed from LifeRecord

### Removed

- `emergentintegrations` Python package and all Emergent LLM proxy usage
- Emergent object storage for progress photos (replaced with local filesystem storage)
- MongoDB / Motor / BSON (replaced with MySQL + SQLAlchemy)
- `@emergentbase/overlay` and `@emergentbase/visual-edits` frontend dev plugins
- Emergent runtime scripts and PostHog analytics from `index.html`

### Replaced

| Original | Replacement |
|----------|-------------|
| MongoDB collections | MySQL tables (`database/schema.sql`) |
| Emergent object storage | Local `backend/uploads/photos` directory |
| `emergentintegrations` Gemini/Whisper | Direct HTTP calls to Google Gemini / OpenAI Whisper APIs |

### Preserved

- All React pages, components, routes, forms, and visual design
- All backend API endpoints, request/response contracts, and business logic
- Authentication flow (JWT in `localStorage`)
- Tailwind CSS + shadcn/ui styling
- Seed/sample data

---

## Troubleshooting

### `Module not found` for backend packages

Make sure the virtual environment is activated and dependencies are installed:

```bash
cd backend
.venv\Scripts\activate
pip install -r requirements.txt
```

### MySQL connection refused

- Verify MySQL is running.
- Check `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` in `backend/.env`.
- Ensure the `lifemanager` database exists.

### phpMyAdmin cannot connect

- Make sure the `db` service is healthy: `docker-compose ps`
- Default phpMyAdmin login uses the same `MYSQL_USER` / `MYSQL_PASSWORD` values.

### AI assistant returns error

The AI assistant requires a `GOOGLE_API_KEY` (and `OPENAI_API_KEY` for voice). If missing, the endpoints return `503`. Add keys to `backend/.env` and restart.

### Frontend shows "Could not sign in"

- Verify the backend is running and `REACT_APP_BACKEND_URL` is correct.
- Check that the database was imported and the owner user was seeded.

---

## GitHub

Source code is hosted at **https://github.com/sazzin07/LifeManager**.

To clone:

```bash
git clone https://github.com/sazzin07/LifeManager.git
cd LifeManager
```

---

## License

Private project for personal use.

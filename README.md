# Zaria ServiceConnect — Phase 1: Backend API

## Overview

This is the FastAPI backend for **Zaria ServiceConnect**, a platform that connects residents in Zaria with verified home-service providers.

---

## Project Structure

```
backend/
├── main.py                    # App entry point — run this
├── requirements.txt           # Python dependencies
├── zaria_serviceconnect.db    # SQLite database (auto-created on first run)
├── uploads/
│   └── documents/             # Uploaded provider ID documents stored here
└── app/
    ├── core/
    │   ├── config.py          # App settings (secret key, DB URL, etc.)
    │   ├── database.py        # SQLAlchemy engine and session setup
    │   ├── security.py        # Password hashing and JWT token functions
    │   └── dependencies.py    # Reusable auth dependencies (get_current_user etc.)
    ├── models/
    │   └── models.py          # Database table definitions (SQLAlchemy ORM)
    ├── schemas/
    │   └── schemas.py         # Pydantic models for request/response validation
    ├── routers/
    │   ├── auth.py            # Registration and login endpoints
    │   ├── categories.py      # Service categories
    │   ├── providers.py       # Provider browsing + admin management
    │   ├── bookings.py        # Booking creation and status management
    │   ├── reviews.py         # Ratings and reviews
    │   ├── complaints.py      # Complaint submission and management
    │   └── users.py           # Admin user management
    └── utils/
        └── seed.py            # Seeds DB with initial categories and admin account
```

---

## Setup Instructions

### Step 1 — Install Python
Make sure Python 3.9 or higher is installed:
```bash
python3 --version
```

### Step 2 — Create Virtual Environment
```bash
cd backend
python3 -m venv venv

# Activate it:
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Run the Server
```bash
uvicorn main:app --reload
```

The server will start at: **http://localhost:8000**

On first startup, it automatically:
- Creates all database tables in `zaria_serviceconnect.db`
- Seeds the 5 service categories
- Creates the admin account

---

### Firebase Push Notifications on Railway

The backend supports three Firebase credential options. For Railway, the simplest is:

1. Open Firebase Console > Project settings > Service accounts.
2. Generate a new private key and download the JSON file.
3. In Railway, open your backend service > Variables.
4. Add `FIREBASE_SERVICE_ACCOUNT_JSON`.
5. Paste the entire JSON file contents as the value.
6. Redeploy the backend service.

Alternative options:

- `FIREBASE_SERVICE_ACCOUNT_BASE64`: base64 encode the full service-account JSON and paste the encoded string.
- `FIREBASE_SERVICE_ACCOUNT_PATH`: set this to a file path only when the JSON file exists on the server filesystem.

---

## Default Admin Account

| Field    | Value                              |
|----------|------------------------------------|
| Email    | admin@zariaserviceconnect.com      |
| Password | admin123                           |

> ⚠️ Change this password before deploying to production!

---

## Interactive API Documentation

Once the server is running, open your browser and visit:

- **Swagger UI** (interactive): http://localhost:8000/docs
- **ReDoc** (readable): http://localhost:8000/redoc

You can test all endpoints directly in the browser using Swagger UI.

---

## API Endpoints Reference

### Authentication — `/auth`

| Method | Endpoint                  | Description                         | Auth Required |
|--------|---------------------------|-------------------------------------|---------------|
| POST   | `/auth/register/resident` | Register new resident               | No            |
| POST   | `/auth/register/provider` | Register new provider (with ID doc) | No            |
| POST   | `/auth/login`             | Login (all roles)                   | No            |
| GET    | `/auth/me`                | Get my profile                      | Yes           |

**Example: Register Resident**
```json
POST /auth/register/resident
{
  "name": "Aminu Musa",
  "email": "aminu@example.com",
  "phone": "+2348012345678",
  "password": "mypassword",
  "location": "Sabon Gari, Zaria"
}
```

**Example: Login**
```json
POST /auth/login
{
  "email": "aminu@example.com",
  "password": "mypassword"
}
```
Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbG...",
  "token_type": "bearer",
  "role": "resident",
  "user_id": 1,
  "name": "Aminu Musa"
}
```

---

### Categories — `/categories`

| Method | Endpoint             | Description           | Auth Required |
|--------|----------------------|-----------------------|---------------|
| GET    | `/categories/`       | List all categories   | No            |
| GET    | `/categories/{id}`   | Get single category   | No            |
| POST   | `/categories/`       | Create category       | Admin         |
| DELETE | `/categories/{id}`   | Delete category       | Admin         |

---

### Providers — `/providers`

| Method | Endpoint                       | Description                          | Auth Required |
|--------|--------------------------------|--------------------------------------|---------------|
| GET    | `/providers/`                  | Browse approved providers            | No            |
| GET    | `/providers/?category_id=1`    | Filter by category                   | No            |
| GET    | `/providers/{id}`              | Get provider profile                 | No            |
| GET    | `/providers/me/profile`        | Provider views own profile           | Provider      |
| GET    | `/providers/admin/all`         | Admin: view all providers            | Admin         |
| PATCH  | `/providers/{id}/status`       | Admin: approve/reject/suspend        | Admin         |

**Example: Approve a Provider**
```json
PATCH /providers/1/status
Authorization: Bearer <admin_token>

{
  "status": "approved"
}
```

---

### Bookings — `/bookings`

| Method | Endpoint                    | Description                         | Auth Required |
|--------|-----------------------------|-------------------------------------|---------------|
| POST   | `/bookings/`                | Create booking request              | Resident      |
| GET    | `/bookings/my/resident`     | My booking history (resident)       | Resident      |
| GET    | `/bookings/my/provider`     | My job requests (provider)          | Provider      |
| PATCH  | `/bookings/{id}/status`     | Accept/decline/complete/cancel      | Provider/Res  |
| GET    | `/bookings/admin/all`       | Admin: all bookings                 | Admin         |
| GET    | `/bookings/{id}`            | Get booking details                 | Auth          |

**Booking Status Flow:**
```
pending → accepted (by provider)
pending → declined (by provider)
pending → cancelled (by resident)
accepted → completed (by provider)
```

**Example: Create Booking**
```json
POST /bookings/
Authorization: Bearer <resident_token>

{
  "provider_id": 1,
  "service_description": "Fix leaking pipe in kitchen",
  "scheduled_date": "2024-06-15",
  "scheduled_time": "10:00 AM",
  "notes": "The leak is under the sink"
}
```

---

### Reviews — `/reviews`

| Method | Endpoint                       | Description                   | Auth Required |
|--------|--------------------------------|-------------------------------|---------------|
| POST   | `/reviews/`                    | Leave a review                | Resident      |
| GET    | `/reviews/provider/{id}`       | Get all reviews for provider  | No            |

**Example: Leave Review**
```json
POST /reviews/
Authorization: Bearer <resident_token>

{
  "booking_id": 1,
  "rating": 5,
  "comment": "Excellent work, very professional!"
}
```

---

### Complaints — `/complaints`

| Method | Endpoint                                  | Description                    | Auth Required |
|--------|-------------------------------------------|--------------------------------|---------------|
| POST   | `/complaints/`                            | Submit complaint               | Resident      |
| GET    | `/complaints/my`                          | My complaints                  | Resident      |
| GET    | `/complaints/admin/all`                   | All complaints                 | Admin         |
| PATCH  | `/complaints/{id}`                        | Admin: update status           | Admin         |
| POST   | `/complaints/{id}/suspend-provider`       | Admin: suspend provider        | Admin         |

---

### Users — `/users`

| Method | Endpoint                        | Description             | Auth Required |
|--------|---------------------------------|-------------------------|---------------|
| GET    | `/users/admin/all`              | All users               | Admin         |
| GET    | `/users/admin/{id}`             | Single user             | Admin         |
| PATCH  | `/users/admin/{id}/deactivate`  | Deactivate user         | Admin         |
| PATCH  | `/users/admin/{id}/activate`    | Reactivate user         | Admin         |

---

## Using Authentication in API Calls

1. Login via `POST /auth/login` to get a token
2. Copy the `access_token` value
3. In Swagger UI: click **Authorize** (lock icon) and paste: `Bearer <your_token>`
4. In code: add header `Authorization: Bearer <your_token>`

---

## Testing the API Step by Step

### Quick Test Flow

```bash
# 1. Check server is running
curl http://localhost:8000/

# 2. Register a resident
curl -X POST http://localhost:8000/auth/register/resident \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Resident","email":"resident@test.com","phone":"08012345678","password":"test123","location":"Zaria"}'

# 3. Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@zariaserviceconnect.com","password":"admin123"}'

# 4. Browse categories (no auth needed)
curl http://localhost:8000/categories/

# 5. Browse approved providers (no auth needed)
curl http://localhost:8000/providers/
```

---

## Database Tables

| Table       | Description                              |
|-------------|------------------------------------------|
| users       | All users (residents, providers, admins) |
| providers   | Provider profiles linked to users        |
| categories  | Service categories (Plumbing, etc.)      |
| bookings    | Service booking requests                 |
| reviews     | Ratings and reviews from residents       |
| complaints  | Complaints from residents                |

---

## What Happens Next

- **Phase 2**: Flutter mobile app (Android) for residents and providers
- **Phase 3**: React admin web dashboard
- **Phase 4**: Integration and full system testing

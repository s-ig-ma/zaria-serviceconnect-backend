# Zaria ServiceConnect — Backend API

> A FastAPI backend powering **Zaria ServiceConnect**, a platform that connects residents in Zaria with verified, local home-service providers.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Default Admin Account](#default-admin-account)
- [API Reference](#api-reference)
  - [Authentication](#authentication)
  - [Categories](#categories)
  - [Providers](#providers)
  - [Bookings](#bookings)
  - [Reviews](#reviews)
  - [Complaints](#complaints)
  - [Messages](#messages)
  - [Notifications](#notifications)
  - [Users (Admin)](#users-admin)
- [Booking Status Flow](#booking-status-flow)
- [Database Schema](#database-schema)
- [Firebase Push Notifications](#firebase-push-notifications)
- [Running on Railway](#running-on-railway)
- [Roadmap](#roadmap)

---

## Overview

Zaria ServiceConnect is a three-sided platform for:

- **Residents** — browse and book verified service providers
- **Providers** — receive and manage job requests, set availability
- **Admins** — approve providers, resolve complaints, manage all users

The backend is the central brain of the system. The web admin dashboard, Android app, and any future frontend all communicate exclusively through this API. It handles authentication, enforces business rules (such as provider approval before visibility), stores data in SQLite, and dispatches push notifications via Firebase.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111 |
| Server | Uvicorn (ASGI) |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (file: `zaria_serviceconnect.db`) |
| Auth | JWT via `python-jose`, passwords hashed with `passlib[bcrypt]` |
| Validation | Pydantic v2 |
| Push Notifications | Firebase Admin SDK |
| File Uploads | `python-multipart`, `aiofiles` |
| Python Version | 3.9+ (see `runtime.txt`) |

---

## Project Structure

```
zaria-serviceconnect-backend/
├── main.py                          # App entry point — registers all routers
├── requirements.txt                 # Python dependencies
├── runtime.txt                      # Python version for deployment platforms
├── zaria_serviceconnect.db          # SQLite database (auto-created on first run)
├── uploads/
│   └── documents/                   # Uploaded provider verification files
├── migrate_availability.py          # DB migration: provider availability field
├── migrate_communication_notifications.py
├── migrate_device_tokens.py         # DB migration: Firebase device token table
├── migrate_flexible_service.py      # DB migration: custom service name support
├── migrate_location.py              # DB migration: provider location fields
├── migrate_product_fixes.py
└── app/
    ├── core/
    │   ├── config.py                # App settings (secret key, DB URL, etc.)
    │   ├── database.py              # SQLAlchemy engine and session factory
    │   ├── security.py              # Password hashing and JWT utilities
    │   └── dependencies.py          # Auth dependencies (get_current_user, require_admin)
    ├── models/
    │   └── models.py                # All SQLAlchemy ORM table definitions
    ├── schemas/
    │   └── schemas.py               # Pydantic request/response models
    ├── routers/
    │   ├── auth.py                  # Registration and login
    │   ├── categories.py            # Service categories
    │   ├── providers.py             # Provider browse + admin management
    │   ├── bookings.py              # Booking lifecycle
    │   ├── reviews.py               # Ratings and reviews
    │   ├── complaints.py            # Complaint submission and resolution
    │   ├── messages.py              # Complaint conversation messages
    │   ├── notifications.py         # User notifications + device token registration
    │   └── users.py                 # Admin user management
    └── utils/
        └── seed.py                  # Seeds service categories and default admin account
```

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- `pip`

### 1 — Clone the repository

```bash
git clone https://github.com/s-ig-ma/zaria-serviceconnect-backend.git
cd zaria-serviceconnect-backend
```

### 2 — Create and activate a virtual environment

```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure environment variables

Copy `.env` and fill in your values (see [Environment Variables](#environment-variables) below).

### 5 — Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0
```

The server starts at **http://localhost:8000**.

On first startup, the app automatically:
- Creates all database tables in `zaria_serviceconnect.db`
- Seeds the five default service categories
- Creates the default admin account

### 6 — Explore the API docs

| Interface | URL |
|---|---|
| Swagger UI (interactive) | http://localhost:8000/docs |
| ReDoc (readable reference) | http://localhost:8000/redoc |

---

## Environment Variables

The `.env` file is read by `app/core/config.py`. Key variables:

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | JWT signing secret (keep private) | `your-secret-key` |
| `DATABASE_URL` | SQLAlchemy DB connection string | `sqlite:///./zaria_serviceconnect.db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | `10080` (7 days) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firebase credentials JSON (for Railway) | *(paste full JSON value)* |
| `FIREBASE_SERVICE_ACCOUNT_BASE64` | Base64-encoded Firebase JSON (alternative) | *(base64 string)* |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to Firebase JSON file (local dev) | `./firebase-key.json` |

> ⚠️ **Never commit your real `.env` to version control.** Add it to `.gitignore`.

---

## Default Admin Account

| Field | Value |
|---|---|
| Email | `admin@zariaserviceconnect.com` |
| Password | `admin123` |

> ⚠️ Change this password before any public or production deployment.

---

## API Reference

All protected endpoints require the header:

```
Authorization: Bearer <access_token>
```

Obtain `access_token` by logging in via `POST /auth/login`.

---

### Authentication

Base path: `/auth`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/auth/register/resident` | Register a new resident | No |
| `POST` | `/auth/register/provider` | Register a provider with verification documents | No |
| `POST` | `/auth/login` | Login (all roles) | No |
| `GET` | `/auth/me` | Get current user profile | ✅ Any |

**Register Resident**
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

**Register Provider** — multipart/form-data

Fields: `name`, `email`, `phone`, `password`, `location`, `category_id` (or `custom_service_name`), `description`, `hourly_rate`, and file fields: `passport_photo`, `id_document`, `skill_proof`.

> Newly registered providers have status `pending` and are not visible to residents until approved by an admin.

**Login**
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
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGci...",
  "token_type": "bearer",
  "role": "resident",
  "user_id": 1,
  "name": "Aminu Musa"
}
```

---

### Categories

Base path: `/categories`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/categories/` | List all categories | No |
| `GET` | `/categories/{id}` | Get single category | No |
| `POST` | `/categories/` | Create a category | 🔒 Admin |
| `DELETE` | `/categories/{id}` | Delete a category | 🔒 Admin |

Default seeded categories: Plumbing, Electrical, Cleaning, Carpentry, Painting.

---

### Providers

Base path: `/providers`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/providers/` | Browse approved providers (filter by `category_id`, sort by distance) | No |
| `GET` | `/providers/search?q=electrician` | Search approved providers by name, category, or location | No |
| `GET` | `/providers/{id}` | Get one provider's public profile | No |
| `GET` | `/providers/me/profile` | Provider views their own profile | 🔒 Provider |
| `PATCH` | `/providers/me/profile` | Provider updates their own profile | 🔒 Provider |
| `PATCH` | `/providers/provider/availability` | Set availability (`available`, `busy`, `offline`) | 🔒 Provider |
| `GET` | `/providers/admin/all` | Admin: all providers (all statuses) | 🔒 Admin |
| `PATCH` | `/providers/{id}/status` | Admin: approve / reject / suspend / reset to pending | 🔒 Admin |

**Location-aware search** — pass `latitude` and `longitude` query parameters to get results sorted by distance from the user.

**Admin: Update Provider Status**
```json
PATCH /providers/1/status
{
  "status": "approved"
}
```
Valid statuses: `pending`, `approved`, `rejected`, `suspended`.

---

### Bookings

Base path: `/bookings`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/bookings/` | Create a booking request | 🔒 Resident |
| `GET` | `/bookings/my/resident` | My booking history | 🔒 Resident |
| `GET` | `/bookings/my/provider` | Incoming job requests | 🔒 Provider |
| `PATCH` | `/bookings/{id}/status` | Update booking status | 🔒 Provider / Resident |
| `GET` | `/bookings/{id}` | Get booking details | ✅ Any (party to booking) |
| `GET` | `/bookings/admin/all` | All bookings | 🔒 Admin |

**Create Booking**
```json
POST /bookings/
{
  "provider_id": 3,
  "service_description": "Fix leaking pipe under the kitchen sink",
  "scheduled_date": "2024-07-20",
  "scheduled_time": "10:00 AM",
  "notes": "Access through the back gate"
}
```

> Bookings are blocked if the provider's availability is set to `offline`.

---

### Booking Status Flow

```
Created by resident
       │
       ▼
   [ pending ]
       │
   ┌───┴───────────────┐
   │                   │
   ▼                   ▼
[ accepted ]       [ declined ]   ← by provider
   │
   │  ←── [ cancelled ]           ← by resident (while pending)
   │
   ▼
[ completion_requested ]          ← by provider (job done)
   │
   ▼
[ completed ]                     ← confirmed by resident
```

---

### Reviews

Base path: `/reviews`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/reviews/` | Submit a review for a completed booking | 🔒 Resident |
| `GET` | `/reviews/provider/{id}` | Get all reviews for a provider | No |

```json
POST /reviews/
{
  "booking_id": 5,
  "rating": 5,
  "comment": "Excellent work, arrived on time and very professional."
}
```

Reviews are only permitted after a booking reaches `completed` status.

---

### Complaints

Base path: `/complaints`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/complaints/` | Submit a complaint about a booking | 🔒 Resident |
| `GET` | `/complaints/my` | My complaints (resident) or complaints against me (provider) | ✅ Resident / Provider |
| `GET` | `/complaints/` | All complaints (filterable by status) | 🔒 Admin |
| `PUT` | `/complaints/{id}/resolve` | Update complaint status + resolution note | 🔒 Admin |
| `POST` | `/complaints/{id}/actions` | Record an admin action (warning, suspend, etc.) | 🔒 Admin |
| `GET` | `/complaints/{id}/actions` | View actions on a complaint | ✅ Parties to complaint |

One complaint per booking maximum. Admin and the provider are notified on submission.

Admin action types: `warning`, `provider_suspension`, `account_deactivation`, `note`.

---

### Messages

Base path: `/messages`

Used for complaint-related conversations between users and admin.

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/messages/` | Send a message on a complaint | ✅ Any party |
| `GET` | `/messages/complaint/{complaint_id}` | Load all messages for a complaint | ✅ Any party |

> Residents and providers can only message in the context of an open complaint. Admin can initiate messages to either party.

---

### Notifications

Base path: `/notifications`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/notifications/my` | Get my notifications | ✅ Any |
| `PATCH` | `/notifications/{id}/read` | Mark one notification as read | ✅ Any |
| `PATCH` | `/notifications/read-all` | Mark all notifications as read | ✅ Any |
| `POST` | `/notifications/devices/register` | Register a Firebase device token for push notifications | ✅ Any |

---

### Users (Admin)

Base path: `/users`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/users/admin/all` | List all users | 🔒 Admin |
| `GET` | `/users/admin/{id}` | Get single user | 🔒 Admin |
| `PATCH` | `/users/admin/{id}/deactivate` | Deactivate a user account | 🔒 Admin |
| `PATCH` | `/users/admin/{id}/activate` | Reactivate a user account | 🔒 Admin |

---

## Database Schema

| Table | Description |
|---|---|
| `users` | All users: residents, providers, and admins |
| `providers` | Provider service profiles linked to user accounts |
| `categories` | Service categories (Plumbing, Electrical, etc.) |
| `bookings` | Booking requests with status tracking |
| `reviews` | Resident ratings and comments for completed bookings |
| `complaints` | Complaints submitted by residents against bookings |
| `messages` | Complaint conversation messages |
| `complaint_actions` | Admin actions recorded on complaints |
| `notifications` | In-app notification records per user |
| `device_tokens` | Firebase device tokens for Android push notifications |

> The database file `zaria_serviceconnect.db` is auto-created by SQLAlchemy on first startup. For a production system, consider migrating to PostgreSQL.

---

## Firebase Push Notifications

The backend supports three credential strategies for Firebase Admin SDK, checked in this order:

1. **`FIREBASE_SERVICE_ACCOUNT_JSON`** — paste the full service-account JSON as a single environment variable (recommended for Railway and similar PaaS platforms).
2. **`FIREBASE_SERVICE_ACCOUNT_BASE64`** — base64-encode the JSON and paste the encoded string.
3. **`FIREBASE_SERVICE_ACCOUNT_PATH`** — provide a file path to a local JSON key file (useful for local development).

To generate credentials: Firebase Console → Project settings → Service accounts → Generate new private key.

---

## Running on Railway

1. Push the repo to GitHub.
2. Create a new Railway project and connect the repo.
3. Add the environment variables from `.env` in Railway → Variables.
4. Add `FIREBASE_SERVICE_ACCOUNT_JSON` with the full Firebase JSON as the value.
5. Railway auto-detects `runtime.txt` and installs `requirements.txt`.
6. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---
---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## License

This project is currently unlicensed. Contact the repository owner for usage terms.

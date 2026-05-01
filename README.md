# Zaria ServiceConnect — Phase 1: Backend API


# Zaria ServiceConnect Backend

This is the FastAPI backend for Zaria ServiceConnect.

The backend is the main brain of the system. The web app, Android app, and admin dashboard all send requests to this backend. The backend checks the rules, talks to the database, and sends results back.

## What FastAPI Is

FastAPI is a Python framework for building APIs.

A framework is a tool that gives developers a structure for building software faster.

An API is a controlled way for one software system to talk to another. In this project, the API allows the frontend apps to ask the backend to login users, register accounts, search providers, create bookings, submit complaints, and more.

Simple example:

```text
Frontend: "Please login this user."
Backend:  "I checked the database. The password is correct. Here is a token."
```

## What The Backend Is Responsible For

The backend handles:

- Authentication: login, registration, and checking who is logged in.
- Users: resident, provider, and admin accounts.
- Providers: provider profiles, approval, search, location, and availability.
- Bookings: creating and updating service bookings.
- Complaints: submitting, reviewing, resolving, and recording admin actions.
- Messages: complaint conversations between admin and residents/providers.
- Notifications: saved alerts for booking, complaint, message, and admin events.
- Reviews: resident ratings and comments after completed jobs.
- Database connection: reading and writing data in SQLite.

## How The Frontend Communicates With The Backend

The frontend sends HTTP requests.

HTTP is the normal communication method used by websites and apps on the internet.

For example:

```text
POST /auth/login
```

means:

- `POST`: the frontend is sending information.
- `/auth/login`: the backend route that handles login.

The backend responds with data, usually in JSON format.

JSON is a simple text format for sending structured data, such as:

```json
{
  "name": "Aisha",
  "role": "resident"
}
```

## Project Structure

```text
backend/
  main.py
  app/
    core/
      config.py
      database.py
      dependencies.py
      security.py
    models/
      models.py
    routers/
      auth.py
      bookings.py
      categories.py
      complaints.py
      messages.py
      notifications.py
      providers.py
      reviews.py
      users.py
    schemas/
    utils/
  zaria_serviceconnect.db
```

Important files:

- `main.py`: starts the FastAPI app and connects all routers.
- `app/models/models.py`: defines database tables.
- `app/core/database.py`: connects to SQLite.
- `app/core/security.py`: handles password hashing and login tokens.
- `app/core/dependencies.py`: checks the current logged-in user and admin access.
- `app/routers/*.py`: contains the API endpoints.

## Main Database Tables

The backend uses these main tables:

- `users`: stores residents, providers, and admins.
- `providers`: stores provider service profiles.
- `categories`: stores service categories.
- `bookings`: stores resident booking requests.
- `complaints`: stores complaints about bookings.
- `messages`: stores complaint conversation messages.
- `complaint_actions`: stores admin actions on complaints.
- `notifications`: stores user notifications.
- `device_tokens`: stores Android device tokens for push notification support.
- `reviews`: stores resident reviews of providers.

## What SQLite Is

SQLite is a simple database stored as a file.

In this project, the database file is:

```text
zaria_serviceconnect.db
```

SQLite is good for a project MVP because it is simple, easy to run, and does not require a separate database server.

For a very large production system, the database could later be changed to PostgreSQL or another larger database system.

## Authentication

Authentication means checking that a user is who they say they are.

The backend supports three roles:

- `resident`
- `provider`
- `admin`

### Register Resident

Endpoint:

```text
POST /auth/register/resident
```

What it does:

- Checks that the email is not already used.
- Hashes the password.
- Creates a resident user record.

Hashing means storing a protected version of the password instead of the plain password.

### Register Provider

Endpoint:

```text
POST /auth/register/provider
```

What it does:

- Checks that the email is not already used.
- Requires provider service details.
- Allows either a predefined category or a custom service name.
- Uploads verification files, such as passport photo, ID document, and skill proof.
- Creates a provider account with pending status.

Important:

A provider does not become visible to residents immediately. Admin must approve the provider first.

### Login

Endpoint:

```text
POST /auth/login
```

What it does:

- Finds the user by email.
- Checks the password.
- Checks that the account is active.
- Returns a JWT token.

A JWT token is a login pass. The frontend sends it with later requests so the backend knows who is logged in.

### Get Current User

Endpoint:

```text
GET /auth/me
```

What it does:

- Uses the token to identify the logged-in user.
- Returns the user's profile.

## Provider Endpoints

### Get Providers

Endpoint:

```text
GET /providers/
```

What it does:

- Returns approved providers.
- Can filter by category.
- Can sort by distance if latitude and longitude are provided.

### Search Providers

Endpoint:

```text
GET /providers/search?q=electrician
```

What it does:

- Searches approved providers.
- Matches provider name, category name, custom service name, description, and location.
- Can use latitude and longitude to return nearer providers first.

### Get Provider Details

Endpoint:

```text
GET /providers/{provider_id}
```

What it does:

- Returns one approved provider's details.

### Admin Get All Providers

Endpoint:

```text
GET /providers/admin/all
```

What it does:

- Lets admin view all providers, including pending, approved, rejected, and suspended providers.

### Admin Update Provider Status

Endpoint:

```text
PATCH /providers/{provider_id}/status
```

What it does:

- Allows admin to approve, reject, suspend, or return a provider to pending.

## Booking Endpoints

### Create Booking

Endpoint:

```text
POST /bookings/
```

What it does:

- Only residents can create bookings.
- Checks that the provider exists.
- Checks that the provider is approved.
- Blocks booking if the provider is offline.
- Saves the booking as `pending`.
- Creates a notification for the provider.

### Resident Booking History

Endpoint:

```text
GET /bookings/my/resident
```

What it does:

- Returns bookings created by the logged-in resident.

### Provider Booking Requests

Endpoint:

```text
GET /bookings/my/provider
```

What it does:

- Returns bookings assigned to the logged-in provider.

### Update Booking Status

Endpoint:

```text
PATCH /bookings/{booking_id}/status
```

What it does:

- Provider can accept or decline pending bookings.
- Provider can request completion after accepting.
- Resident can cancel pending bookings.
- Resident can confirm completion after provider requests it.

Booking statuses:

- `pending`: resident has requested the booking.
- `accepted`: provider accepted.
- `completion_requested`: provider says the job is done.
- `completed`: resident confirmed the job is done.
- `cancelled`: resident cancelled before acceptance.
- `declined`: provider declined.

### Provider Availability

Endpoint:

```text
PATCH /bookings/provider/availability?availability_status=available
```

What it does:

- Lets a provider set availability to `available`, `busy`, or `offline`.

## Complaint Endpoints

### Submit Complaint

Endpoint:

```text
POST /complaints/
```

What it does:

- Only residents can submit complaints.
- Complaint must be linked to one of the resident's bookings.
- Only one complaint is allowed per booking.
- Admin and provider receive notifications.

### My Complaints

Endpoint:

```text
GET /complaints/my
```

What it does:

- Resident sees complaints they submitted.
- Provider sees complaints made against them.

### Admin View Complaints

Endpoint:

```text
GET /complaints/
```

What it does:

- Admin sees all complaints.
- Admin can filter by status.

### Resolve Complaint

Endpoint:

```text
PUT /complaints/{complaint_id}/resolve
```

What it does:

- Admin changes complaint status.
- Admin can add a resolution note.
- Resident and provider receive notifications.

### Complaint Actions

Endpoints:

```text
POST /complaints/{complaint_id}/actions
GET /complaints/{complaint_id}/actions
```

What they do:

- Admin records actions like warning, provider suspension, account deactivation, or note.
- Users connected to the complaint can view related actions.

## Message Endpoints

Messages are mainly used for complaint conversations.

Endpoint:

```text
GET /messages/complaint/{complaint_id}
```

Loads complaint messages.

Endpoint:

```text
POST /messages/
```

Sends a complaint message.

Important rule:

Residents and providers can only message admin about complaint cases. Admin can message the resident or provider separately.

## Notification Endpoints

Endpoint:

```text
GET /notifications/my
```

Returns notifications for the logged-in user.

Endpoint:

```text
PATCH /notifications/{notification_id}/read
```

Marks one notification as read.

Endpoint:

```text
PATCH /notifications/read-all
```

Marks all notifications as read.

Endpoint:

```text
POST /notifications/devices/register
```

Registers an Android device token for push notification support.

## How A Full Request Works

Example: resident creates a booking.

```text
1. Resident fills booking form.
2. Frontend sends POST /bookings/ with booking details.
3. Backend reads the login token to know the resident.
4. Backend checks the provider.
5. Backend checks availability.
6. Backend saves the booking in SQLite.
7. Backend creates a notification for the provider.
8. Backend sends the saved booking back to the frontend.
```

## How To Run The Backend Locally

From the `backend` folder:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0
```

Then open:

```text
http://localhost:8000
```

API documentation is available at:

```text
http://localhost:8000/docs
```

The `/docs` page is useful during defense because it shows all backend endpoints.

## Defense Explanation

You can say:

"The backend is the central brain of Zaria ServiceConnect. The web app, Android app, and admin dashboard all send API requests to it. The backend checks authentication, applies business rules like provider approval and booking status changes, stores data in SQLite, and returns responses to the apps."






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

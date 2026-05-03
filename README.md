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

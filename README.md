# Superlive 2.0 Architecture & Endpoints

This document tracks the active folder structure, components, and available endpoints specifically built for **Superlive 2.0**.

## 📁 Clean Architecture Directory map

```text
superlive_2.0/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth_routes.py       # Signup OTP flow & Email Login
│   │       ├── device_routes.py     # Device registration
│   │       ├── feed_routes.py       # User posts feed
│   │       ├── livestream_routes.py # Livestream retrieval
│   │       └── user_routes.py       # Profile, search, top gifters, profile update/complete
│   ├── core/
│   │   ├── config.py               # Constants, API Base URLs, Domains, and Timeouts
│   │   ├── http_client.py          # Unified proxy handler & Chrome headers
│   │   ├── security.py             # Dynamic payload (uuid_c1, adid) generation & source_url logic
│   │   └── session_manager.py      # In-memory session store (PENDING_SIGNUPS, ACTIVE_USERS)
│   ├── models/                     # (Future) Payload validation models
│   ├── services/
│   │   └── superlive_service.py    # Upstream integration business logic
│   └── main.py                     # Quart App Initialization & Blueprint registration
├── tests/
│   └── test_device.py              # Unit & Integration tests for payloads
├── run.py                          # Development Server Entrypoint
└── structure.md                    # You are here
```

---

## 🚀 Active Local Endpoints (Quart)

These endpoints are hosted locally via `python run.py` (Default: `http://127.0.0.1:5000`).

### 1. Device Registration
- **URL**: `POST /api/device/register`
- **Description**: Generates a completely new virtual device profile (random `uuid_c1`, `adid`, `installation_id`), signs the header, and registers it with the upstream Superlive API.
- **Payload (Optional)**:
  ```json
  {
    "proxy": "http://user:pass@ip:port"
  }
  ```
- **Returns**: `200 OK`
  ```json
  {
    "status": "success",
    "device_profile": {
      "adid": "...",
      "adjust_web_uuid": "...",
      "ga_session_id": "...",
      "installation_id": "...",
      "ttp": "...",
      "uuid_c1": "..."
    },
    "upstream_response": {
      "guid": "58ae16840d004642c8429d40459818c6"
    }
  }
  ```

### 2. Email Signup Flow (3-Step Postman Guide)

The Email Signup process strictly follows the 3-step browser sequence. The Quart backend uses an in-memory session store (`AUTH_SESSIONS`) to remember your `device_id` and payloads across requests, linked by your email address.

**Step A: Request OTP**
- **URL**: `POST /api/auth/signup/request-otp`
- **Payload**:
  ```json
  {
    "email": "your_test_email@temp.ly"
  }
  ```
- **Returns**: `200 OK`

**Step B: Verify OTP**
- **URL**: `POST /api/auth/signup/verify-otp`
- **Description**: Check your temp email for the 6-digit code and submit it here. The server will auto-attach the session.
- **Payload**:
  ```json
  {
    "email": "your_test_email@temp.ly",
    "code": 123456
  }
  ```

**Step C: Complete Signup**
- **URL**: `POST /api/auth/signup/email`
- **Description**: Finalizes the registration and clears the temporary session.
- **Payload**:
  ```json
  {
    "email": "your_test_email@temp.ly",
    "password": "yourpassword123"
  }
  ```

### 3. Profile Management

**Update Profile Data (Name, Gender, etc.)**
- **URL**: `POST /api/users/verify/update`
- **Description**: Updates user details using the authorization token retrieved from signup. The backend auto-resolves your device session. You can pass any field (like `gender`) that the upstream accepts.
- **Payload**:
  ```json
  {
    "update_data": {
      "name": "Piyush",
      "gender": "2"
    },
    "auth_token": "b50f3200cc0a1ff38c88703daf105c2713..."
  }
  ```

**Complete Profile Onboarding**
- **URL**: `POST /api/users/verify/complete`
- **Description**: The final step of the profile setup flow. Submits the name, gender, and birthday directly in the root payload.
- **Payload**:
  ```json
  {
    "name": "Piyush",
    "gender": 1,
    "birthday": 1115538908000,
    "auth_token": "b50f3200cc0a1ff38c88703daf105c2713..."
  }
  ```

### 4. Email Login & Logout

**Login Existing User**
- **URL**: `POST /api/auth/login/email`
- **Description**: Logs in an existing user. Automatically sets up a fresh device profile behind the scenes.
- **Payload**:
  ```json
  {
    "email": "test@temp.ly",
    "password": "yourpassword123"
  }
  ```
- **Returns**: Contains `upstream_response.token`. You can use this token seamlessly in the Profile Update route.

**Logout User**
- **URL**: `POST /api/users/logout`
- **Description**: Logs out the active user session from the upstream Superlive servers and removes the session from the local memory store.
- **Payload**:
  ```json
  {
    "auth_token": "f6f6e4d0138c695a6ceac3ca49eaedf4a2d1c90a"
  }
  ```

### 5. Livestream

**Retrieve Livestream**
- **URL**: `POST /api/livestream/retrieve`
- **Description**: Fetches livestream data. Requires active session.
- **Payload**:
  ```json
  {
    "livestream_id": "134547347",
    "auth_token": "..."
  }
  ```

**Send Gift**
- **URL**: `POST /api/livestream/chat/send_gift`
- **Description**: Sends a gift during a livestream. Requires active session. Generates random UUID if `guids` is omitted. Defaults to Rose (`gift_id`: 5141) if omitted.
- **Payload**:
  ```json
  {
    "livestream_id": 134590117,
    "auth_token": "..."
  }
  ```
- **Optional Payload**:
  ```json
  {
    "gift_id": 5141,
    "user_ids": [10471059],
    "guids": ["49702a96-c0de-4a23-bbb5-5a38feef67cc"],
    "gift_context": 1,
    "gift_batch_size": 1,
    "tip_gift_id": null
  }
  ```

**Get Active Viewers & Top Gifters**
- **URL**: `POST /api/livestream/active_viewers_and_top_gifters`
- **Description**: Fetches the active viewers and top gifters for a livestream. `auth_token` optional. Supports pagination.
- **Payload**:
  ```json
  {
    "livestream_id": 134590117,
    "auth_token": "...",
    "active_viewers_next": null,
    "top_gifters_next": null
  }
  ```

### 6. User Profile & Discovery

**Get User Profile**
- **URL**: `POST /api/users/profile`
- **Description**: Fetches a user's profile. `auth_token` optional (registers fresh device if not provided). When `is_from_search` is `true`, appends `?isFromSearch=true` to `source_url` and sets `session_source_url` to the search page.
- **Payload**:
  ```json
  {
    "user_id": "43819951",
    "is_from_search": false,
    "auth_token": "...",
    "livestream_id": "134547347"
  }
  ```
  Required: `user_id`, `is_from_search`. Optional: `auth_token`, `livestream_id`.

**Search Users**
- **URL**: `POST /api/users/search`
- **Description**: Searches users by query. `auth_token` optional.
- **Payload**:
  ```json
  {
    "search_query": "anvar"
  }
  ```

**Top Gifters**
- **URL**: `POST /api/users/top_gifters`
- **Description**: Fetches top gifters leaderboard for a user. `auth_token` required.
- **Payload**:
  ```json
  {
    "user_id": 43819951,
    "leaderboard_type": 0,
    "auth_token": "..."
  }
  ```

### 7. Feed

**User Posts**
- **URL**: `POST /api/feed/user_posts`
- **Description**: Fetches a user's posts. `auth_token` optional. Supports pagination via `next` cursor.
- **Payload**:
  ```json
  {
    "owner_id": "43819951",
    "limit": 15,
    "next": null
  }
  ```

### 8. Discover

**Discover Feed**
- **URL**: `POST /api/discover/`
- **Description**: Fetches the discover feed users. `auth_token` optional. Supports pagination.
- **Payload**:
  ```json
  {
    "auth_token": "...",
    "next": null,
    "type": 0
  }
  ```

### 9. TempMail Generation

**Generate Email Address**
- **URL**: `GET /api/tempmail/email`
- **Description**: Generates a new random username and domain combination using `temp.ly`.
- **Returns**: `200 OK`
  ```json
  {
    "username": "p9kq068x8qf1zxp8",
    "domain": "temp.ly",
    "email": "p9kq068x8qf1zxp8@temp.ly"
  }
  ```

**Fetch OTP from Inbox**
- **URL**: `POST /api/tempmail/otp`
- **Description**: Checks the `temp.ly` inbox for the verification email and extracts the 6-digit OTP code.
- **Payload**:
  ```json
  {
    "username": "p9kq068x8qf1zxp8",
    "domain": "temp.ly"
  }
  ```
- **Returns**: `200 OK` (if OTP found)
  ```json
  {
    "success": true,
    "otp": "336439"
  }
  ```

### 10. Auto Gifting Loop

**Start/Stop Auto Gift Loop**
- **URL**: `POST /api/auto/gift/`
- **Description**: Orchestrates the automated creation of accounts using TempMail, OTP bypass, profile completion, and looping 4 gifts to a specified `livestream_id`.
- **Payload (Start)**:
  ```json
  {
    "code": 10,
    "livestream_id": 134600234,
    "worker": 2,
    "use_proxy": false
  }
  ```
- **Payload (Stop)**:
  ```json
  {
    "code": 12
  }
  ```

---

## 🌐 Implemented Upstream Integrations

These are the exact Superlive REST endpoints we are currently successfully communicating with inside our `services` layer.

* **`POST /device/register`** — `register_device` **[ACTIVE]**
* **`POST /signup/send_email_verification_code`** — `request_email_otp` **[ACTIVE]**
* **`POST /signup/verify_email`** — `verify_email_otp` **[ACTIVE]**
* **`POST /signup/email`** — `signup_email` **[ACTIVE]**
* **`POST /signup/email_signin`** — `login_email` **[ACTIVE]**
* **`POST /users/verify/update`** — `update_profile` **[ACTIVE]**
* **`POST /users/update`** — `complete_profile` **[ACTIVE]**
* **`POST /user/logout`** — `logout` **[ACTIVE]**
* **`POST /livestream/retrieve`** — `retrieve_livestream` **[ACTIVE]**
* **`POST /livestream/chat/send_gift`** — `send_gift` **[ACTIVE]**
* **`POST /livestream/active_viewers_and_top_gifters`** — `get_active_viewers_and_top_gifters` **[ACTIVE]**
* **`POST /users/profile`** — `get_user_profile` **[ACTIVE]**
* **`POST /users/search`** — `search_users` **[ACTIVE]**
* **`POST /user/top_gifters`** — `get_top_gifters` **[ACTIVE]**
* **`POST /feed/user_posts`** — `get_user_posts` **[ACTIVE]**
* **`POST /api/web/discover`** — `get_discover` **[ACTIVE]**

---

> **Note**: As we build out more features (Tempmail, AutoGift, Discover), this `structure.md` file will be updated to reflect the new endpoints and modules.

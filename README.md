# Social Media REST API (FastAPI + PostgreSQL)

A robust, production-ready social media backend REST API built with **FastAPI**, **SQLAlchemy ORM (2.0)**, **Pydantic v2**, and **PostgreSQL**.

---

## ✨ Features

- **Authentication & Authorization**:
  - Secure password hashing with `bcrypt`.
  - JWT Access Token generation (`HS256`).
  - Role-Based Access Control (`user` vs `admin`).
  - Active session tracking (`is_logged_in`).
  - User blocking enforcement (blocked users are barred from protected actions).

- **Posts Management**:
  - Create, view, paginate, and delete posts.
  - Ability for post owners / admins to toggle comments on/off per post (`allow_comments`).
  - Track like counts and comment counts.

- **Likes System**:
  - Toggle like/unlike on posts.
  - Unique constraint per user-post pair to avoid duplicate likes.

- **Comments System with Pinning**:
  - Create, edit, and delete comments.
  - **Pin/Unpin comments**: Post owners can pin important comments to the top of the comment section.
  - Cursor-based / timestamp pagination for comments.

- **Admin Controls**:
  - Real-time list of all currently logged-in users.
  - Moderation controls: block/unblock users (instantly revoking sessions).
  - Admin user deletion controls.

- **CORS Support**:
  - Pre-configured CORS middleware for frontend integrations.

---

## 🛠️ Project Structure

```
fastapi-social-app/
├── app/
│   ├── __init__.py
│   ├── auth.py         # Password hashing, JWT utils, OAuth2 dependencies
│   ├── database.py     # SQLAlchemy DB connection & sessionmaker
│   ├── main.py         # FastAPI app routes & middleware
│   ├── models.py       # SQLAlchemy ORM models (User, Post, Comment, Like)
│   └── schemas.py      # Pydantic request & response schemas
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules
├── requirements.txt    # Python dependencies
├── run_backend.bat     # Windows launcher script
└── README.md           # Documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- PostgreSQL database server running locally or remotely

### 2. Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd fastapi-social-app
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your PostgreSQL database credentials and JWT secret:
   ```env
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=social_app_db
   JWT_SECRET=your_jwt_secret_key
   ```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
On Windows, you can also double-click `run_backend.bat`.

Once running:
- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📡 API Overview

### 🔐 Auth (`/auth`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register a new user (`user` or `admin`) | No |
| `POST` | `/auth/login` | Login and receive Bearer JWT token | No |
| `GET` | `/auth/me` | Fetch current user profile | Yes (Bearer) |
| `POST` | `/auth/logout` | Log out current user | Yes (Bearer) |

### 📝 Posts (`/posts`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/posts` | Paginated list of all posts | No |
| `POST` | `/posts` | Create a new post | Yes |
| `GET` | `/posts/my-posts` | List posts created by current user | Yes |
| `DELETE` | `/posts/{post_id}` | Delete post (Owner or Admin) | Yes |
| `PATCH` | `/posts/{post_id}/allow-comments` | Enable/Disable comments on post | Yes (Owner or Admin) |
| `POST` | `/posts/{post_id}/like` | Like / Unlike a post | Yes |

### 💬 Comments (`/posts/{post_id}/comments` & `/comments`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/posts/{post_id}/comments` | List comments (pinned first, cursor paginated) | No |
| `POST` | `/posts/{post_id}/comments` | Create a comment | Yes |
| `PUT` | `/comments/{comment_id}` | Edit comment (Author only) | Yes |
| `DELETE` | `/comments/{comment_id}` | Delete comment (Author or Admin) | Yes |
| `PATCH` | `/posts/{post_id}/comments/{comment_id}/pin` | Pin/Unpin comment | Yes (Post Owner) |

### 🛡️ Admin Moderation (`/admin`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/admin/users/logged-in` | List all active logged-in users | Yes (Admin only) |
| `GET` | `/admin/users` | List all users in system | Yes (Admin only) |
| `PATCH` | `/admin/users/{user_id}/block` | Block or unblock a user | Yes (Admin only) |
| `DELETE` | `/admin/users/{user_id}` | Delete a user account | Yes (Admin only) |

---

## 📄 License
MIT License

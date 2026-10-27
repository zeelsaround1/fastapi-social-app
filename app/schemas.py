import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models import UserRole


# --- 1. Auth & User Schemas ---
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.USER


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    username: str
    role: UserRole


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    is_blocked: bool
    is_logged_in: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- 2. Post Schemas ---
class PostCreate(BaseModel):
    body: str


class PostResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    author_username: Optional[str] = None
    body: str
    allow_comments: bool
    created_at: datetime
    likes_count: int = 0
    comments_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class PaginatedPostsResponse(BaseModel):
    posts: List[PostResponse]
    total_posts: int
    offset: int
    limit: int


# --- 3. Comment Schemas ---
class CommentCreate(BaseModel):
    body: str


class CommentUpdate(BaseModel):
    body: str


class CommentResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID
    author_username: Optional[str] = None
    body: str
    is_pinned: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CommentCursorPage(BaseModel):
    comments: List[CommentResponse]
    next_cursor: Optional[datetime] = None
    has_more: bool

import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app import models, schemas
from app.auth import (
    hash_password, verify_password, create_access_token, 
    get_current_user, require_admin
)
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Social Media API (FastAPI + PostgreSQL)")

# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================================================
# 1. AUTHENTICATION (Register, Login, Logout, Me)
# ====================================================================

@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register User (Role: 'user' or 'admin')"""
    existing = db.scalar(
        select(models.User).where(
            (models.User.username == user_in.username) | (models.User.email == user_in.email)
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username or email is already registered")

    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role or models.UserRole.USER
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login User -> Returns JWT token (Compatible with Swagger Authorize button)"""
    user = db.scalar(select(models.User).where(models.User.username == form_data.username))
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked by an admin")

    # Mark user as logged in
    user.is_logged_in = True
    db.commit()

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }


@app.get("/auth/me", response_model=schemas.UserResponse)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    """Get the current authenticated user's profile"""
    return current_user


@app.post("/auth/logout")
def logout_user(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout Logged-in User"""
    current_user.is_logged_in = False
    db.commit()
    return {"message": "Logged out successfully"}


# ====================================================================
# 2. ADMIN-ONLY USER CONTROLS
# ====================================================================

@app.get("/admin/users/logged-in", response_model=List[schemas.UserResponse])
def list_logged_in_users(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List All logged-in users --> Admin only"""
    return db.scalars(select(models.User).where(models.User.is_logged_in == True)).all()


@app.get("/admin/users", response_model=List[schemas.UserResponse])
def list_all_users_for_admin(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List All users in system --> Admin only"""
    return db.scalars(select(models.User).order_by(models.User.created_at.desc())).all()


@app.patch("/admin/users/{user_id}/block")
def block_or_unblock_user(
    user_id: uuid.UUID,
    block: bool,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Block/Unblock any User --> Admin only"""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == models.UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot block an admin account")

    user.is_blocked = block
    if block:
        user.is_logged_in = False  # Immediately log out blocked user
    db.commit()
    return {"user_id": user_id, "is_blocked": user.is_blocked}


@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: uuid.UUID,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete any User --> Admin only"""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admin cannot delete their own account")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


# ====================================================================
# 3. POSTS MANAGEMENT
# ====================================================================

@app.post("/posts", response_model=schemas.PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: schemas.PostCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Post --> LoggedIn User"""
    new_post = models.Post(user_id=current_user.id, body=post_in.body)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    resp = schemas.PostResponse.model_validate(new_post)
    resp.author_username = current_user.username
    resp.likes_count = 0
    resp.comments_count = 0
    return resp


@app.get("/posts/my-posts", response_model=List[schemas.PostResponse])
def list_my_posts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List LoggedIn User posts --> User Specific"""
    posts = db.scalars(
        select(models.Post)
        .where(models.Post.user_id == current_user.id)
        .order_by(models.Post.created_at.desc())
    ).all()

    result = []
    for post in posts:
        item = schemas.PostResponse.model_validate(post)
        item.likes_count = len(post.likes)
        item.comments_count = len(post.comments)
        item.author_username = post.author.username if post.author else current_user.username
        result.append(item)
    return result


@app.get("/posts", response_model=schemas.PaginatedPostsResponse)
def list_all_posts(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List All posts with pagination --> No Login required"""
    total_posts = db.scalar(select(func.count(models.Post.id))) or 0
    posts = db.scalars(
        select(models.Post)
        .order_by(models.Post.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    result = []
    for post in posts:
        item = schemas.PostResponse.model_validate(post)
        item.likes_count = len(post.likes)
        item.comments_count = len(post.comments)
        item.author_username = post.author.username if post.author else "Unknown"
        result.append(item)

    return {
        "posts": result,
        "total_posts": total_posts,
        "offset": offset,
        "limit": limit
    }


@app.delete("/posts/{post_id}")
def delete_post(
    post_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete Post --> Post Owner or Admin"""
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if current_user.role != models.UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")

    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}


@app.patch("/posts/{post_id}/allow-comments")
def allow_unallow_comments_on_post(
    post_id: uuid.UUID,
    allow: bool,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow/unallow comments on post --> Admin or Post Owner"""
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if current_user.role != models.UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the Post Owner or an Admin can modify comment settings")

    post.allow_comments = allow
    db.commit()
    return {"post_id": post_id, "allow_comments": post.allow_comments}


# ====================================================================
# 4. LIKES MANAGEMENT
# ====================================================================

@app.post("/posts/{post_id}/like")
def like_unlike_post(
    post_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Like/Unlike Post --> Any LoggedIn User"""
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_like = db.scalar(
        select(models.Like).where(
            models.Like.post_id == post_id,
            models.Like.user_id == current_user.id
        )
    )

    if existing_like:
        db.delete(existing_like)
        db.commit()
        likes_count = db.scalar(select(func.count(models.Like.id)).where(models.Like.post_id == post_id)) or 0
        return {"message": "Post unliked", "is_liked": False, "likes_count": likes_count}
    else:
        new_like = models.Like(post_id=post_id, user_id=current_user.id)
        db.add(new_like)
        db.commit()
        likes_count = db.scalar(select(func.count(models.Like.id)).where(models.Like.post_id == post_id)) or 0
        return {"message": "Post liked", "is_liked": True, "likes_count": likes_count}


# ====================================================================
# 5. COMMENTS MANAGEMENT
# ====================================================================

@app.post("/posts/{post_id}/comments", response_model=schemas.CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: uuid.UUID,
    comment_in: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Comment --> Any LoggedIn User (checks if post allows comments)"""
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if not post.allow_comments:
        raise HTTPException(status_code=403, detail="Comments are disabled on this post")

    new_comment = models.Comment(
        post_id=post_id,
        user_id=current_user.id,
        body=comment_in.body
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    resp = schemas.CommentResponse.model_validate(new_comment)
    resp.author_username = current_user.username
    return resp


@app.get("/posts/{post_id}/comments", response_model=schemas.CommentCursorPage)
def list_comments_of_post(
    post_id: uuid.UUID,
    first: int = Query(10, ge=1, le=50),
    after: Optional[datetime] = Query(None, description="ISO timestamp cursor"),
    db: Session = Depends(get_db)
):
    """List all comments of a post with pagination --> No login required (Pinned comments appear first!)"""
    query = select(models.Comment).where(models.Comment.post_id == post_id)
    if after:
        query = query.where(models.Comment.created_at < after)

    comments = db.scalars(
        query.order_by(models.Comment.is_pinned.desc(), models.Comment.created_at.desc()).limit(first + 1)
    ).all()

    has_more = len(comments) > first
    returned = comments[:first]
    next_cursor = returned[-1].created_at if has_more and returned else None

    result_comments = []
    for c in returned:
        c_item = schemas.CommentResponse.model_validate(c)
        c_item.author_username = c.author.username if c.author else "Unknown"
        result_comments.append(c_item)

    return {
        "comments": result_comments,
        "next_cursor": next_cursor,
        "has_more": has_more
    }


@app.put("/comments/{comment_id}", response_model=schemas.CommentResponse)
def edit_comment(
    comment_id: uuid.UUID,
    comment_in: schemas.CommentUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit Comment --> Comment Author only"""
    comment = db.get(models.Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")

    comment.body = comment_in.body
    db.commit()
    db.refresh(comment)
    resp = schemas.CommentResponse.model_validate(comment)
    resp.author_username = current_user.username
    return resp


@app.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete Comment --> Comment Author or Admin"""
    comment = db.get(models.Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if current_user.role != models.UserRole.ADMIN and comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted successfully"}


@app.patch("/posts/{post_id}/comments/{comment_id}/pin")
def pin_unpin_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    pin: bool,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pin/Unpin A comment --> Post Owner only"""
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the post owner can pin or unpin comments")

    comment = db.get(models.Comment, comment_id)
    if not comment or comment.post_id != post_id:
        raise HTTPException(status_code=404, detail="Comment not found on this post")

    comment.is_pinned = pin
    db.commit()
    return {"comment_id": comment_id, "is_pinned": comment.is_pinned}

    return {"comment_id": comment_id, "is_pinned": comment.is_pinned}
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import User, Role
from app.schemas import Token, UserOut, PasswordResetRequest
from app.security import create_access_token, verify_password, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not user.is_active or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(user.id, user.role.value))

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user

# SECURE ADMIN ONLY RESET
@router.post("/admin-reset-password")
def admin_reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin))):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        raise HTTPException(status_code=404, detail="User with this email not found")
    
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Enrollment, GuardianStudent, Role, Student, Teacher, TeachingAssignment, User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
CREDENTIALS_ERROR = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    import jwt as pyjwt
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (pyjwt.PyJWTError, KeyError, ValueError):
        raise CREDENTIALS_ERROR
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise CREDENTIALS_ERROR
    return user

def require_roles(*roles: Role) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return checker

def teacher_teaches_section(db: Session, teacher_id: int, section_id: int) -> bool:
    return db.scalar(select(TeachingAssignment.id).where(TeachingAssignment.teacher_id == teacher_id, TeachingAssignment.section_id == section_id)) is not None

def active_enrollment(db: Session, student_id: int, section_id: int) -> Enrollment | None:
    return db.scalar(select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.section_id == section_id, Enrollment.is_active.is_(True)))

def assert_section_access(db: Session, user: User, section_id: int) -> None:
    if user.role == Role.admin: return
    if user.role == Role.teacher and user.teacher:
        if teacher_teaches_section(db, user.teacher.id, section_id): return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not assigned to this section")
    if user.role == Role.student and user.student:
        if active_enrollment(db, user.student.id, section_id): return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enrolled in this section")
    if user.role == Role.guardian and user.guardian:
        child_ids = db.scalars(select(GuardianStudent.student_id).where(GuardianStudent.guardian_id == user.guardian.id)).all()
        if any(active_enrollment(db, sid, section_id) for sid in child_ids): return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

def active_enrollment_any(db: Session, student_id: int, section_ids: list[int]) -> bool:
    return db.scalar(select(Enrollment.id).where(Enrollment.student_id == student_id, Enrollment.section_id.in_(section_ids), Enrollment.is_active.is_(True))) is not None

def assert_student_access(db: Session, user: User, student_id: int) -> None:
    if user.role == Role.admin: return
    if user.role == Role.teacher and user.teacher:
        section_ids = db.scalars(select(TeachingAssignment.section_id).where(TeachingAssignment.teacher_id == user.teacher.id)).all()
        if section_ids and active_enrollment_any(db, student_id, list(section_ids)): return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your student")
    if user.role == Role.student and user.student and user.student.id == student_id: return
    if user.role == Role.guardian and user.guardian:
        link = db.scalar(select(GuardianStudent).where(GuardianStudent.guardian_id == user.guardian.id, GuardianStudent.student_id == student_id))
        if link: return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Announcement, Audience, Enrollment, GuardianStudent, Role, TeachingAssignment, User
from app.schemas import AnnouncementCreate, AnnouncementOut

router = APIRouter(prefix="/announcements", tags=["announcements"])

@router.post("", response_model=AnnouncementOut, status_code=201)
def create_announcement(payload: AnnouncementCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.teacher))):
    if payload.audience == Audience.section and payload.section_id is None: raise HTTPException(422, "section_id is required for section announcements")
    ann = Announcement(author_user_id=user.id, **payload.model_dump()); db.add(ann); db.commit(); return ann

@router.get("", response_model=list[AnnouncementOut])
def list_announcements(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == Role.admin: return db.scalars(select(Announcement).order_by(Announcement.created_at.desc())).all()
    audiences = [Audience.all]; section_ids: list[int] = []
    if user.role == Role.teacher and user.teacher:
        audiences.append(Audience.teachers)
        section_ids = db.scalars(select(TeachingAssignment.section_id).where(TeachingAssignment.teacher_id == user.teacher.id)).all()
    elif user.role == Role.student and user.student:
        audiences.append(Audience.students)
        section_ids = db.scalars(select(Enrollment.section_id).where(Enrollment.student_id == user.student.id, Enrollment.is_active.is_(True))).all()
    elif user.role == Role.guardian and user.guardian:
        audiences.append(Audience.guardians)
        child_ids = db.scalars(select(GuardianStudent.student_id).where(GuardianStudent.guardian_id == user.guardian.id)).all()
        if child_ids: section_ids = db.scalars(select(Enrollment.section_id).where(Enrollment.student_id.in_(child_ids), Enrollment.is_active.is_(True))).all()
    stmt = select(Announcement).where(Announcement.audience.in_(audiences))
    if section_ids: stmt = stmt.union(select(Announcement).where(Announcement.audience == Audience.section, Announcement.section_id.in_(section_ids)))
    return db.scalars(stmt.order_by(Announcement.created_at.desc())).all()

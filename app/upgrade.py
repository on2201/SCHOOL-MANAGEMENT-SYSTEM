from pathlib import Path

def main():
    # 1. Append new Models
    p = Path("app/models.py")
    text = p.read_text(encoding="utf-8")
    if "class Submission(Base):" not in text:
        text += r"""

class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), index=True)
    file_url: Mapped[str] = mapped_column(String(512))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    grade: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    feedback: Mapped[str | None] = mapped_column(Text)
    assessment: Mapped[Assessment] = relationship()
    enrollment: Mapped[Enrollment] = relationship()

class PayrollRecord(Base):
    __tablename__ = "payroll_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    month: Mapped[int] = mapped_column()
    year: Mapped[int] = mapped_column()
    base_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    deductions: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    teacher: Mapped[Teacher] = relationship()
"""
        p.write_text(text, encoding="utf-8")
        print("Updated models.py")

    # 2. Append new Schemas
    p = Path("app/schemas.py")
    text = p.read_text(encoding="utf-8")
    if "class PayrollCreate(BaseModel):" not in text:
        text += r"""

class PayrollCreate(BaseModel):
    teacher_id: int
    month: int = Field(ge=1, le=12)
    year: int
    base_amount: Decimal = Field(gt=0)
    deductions: Decimal = Field(default=Decimal("0.00"), ge=0)

class PayrollOut(ORMModel):
    id: int
    teacher_id: int
    month: int
    year: int
    base_amount: Decimal
    deductions: Decimal
    net_amount: Decimal
    status: str
    paid_at: datetime | None

class SubmissionOut(ORMModel):
    id: int
    assessment_id: int
    enrollment_id: int
    file_url: str
    submitted_at: datetime
    grade: Decimal | None
    feedback: str | None
"""
        p.write_text(text, encoding="utf-8")
        print("Updated schemas.py")

    # 3. Patch academics.py for Room Conflicts
    p = Path("app/routers/academics.py")
    text = p.read_text(encoding="utf-8")
    old_code = """    existing = db.scalars(select(TimetableEntry).where(TimetableEntry.day_of_week == payload.day_of_week, ((TimetableEntry.section_id == payload.section_id) | (TimetableEntry.teacher_id == payload.teacher_id)))).all()
    for e in existing:
        if payload.start_time < e.end_time and e.start_time < payload.end_time: raise HTTPException(409, "Timetable conflict with an existing entry")"""
    
    new_code = """    existing = db.scalars(select(TimetableEntry).where(TimetableEntry.day_of_week == payload.day_of_week, ((TimetableEntry.section_id == payload.section_id) | (TimetableEntry.teacher_id == payload.teacher_id)))).all()
    for e in existing:
        if payload.start_time < e.end_time and e.start_time < payload.end_time: raise HTTPException(409, "Timetable conflict: Section or Teacher is already booked at this time")
    
    # ADVANCED: Check room conflicts
    if payload.room:
        room_conflict = db.scalars(select(TimetableEntry).where(TimetableEntry.day_of_week == payload.day_of_week, TimetableEntry.room == payload.room)).all()
        for r in room_conflict:
            if payload.start_time < r.end_time and r.start_time < payload.end_time:
                raise HTTPException(409, f"Timetable conflict: Room {payload.room} is already booked at this time")"""
    
    if old_code in text:
        text = text.replace(old_code, new_code)
        p.write_text(text, encoding="utf-8")
        print("Updated academics.py (Advanced Timetable)")

    # 4. Create Submissions Router
    Path("app/routers/submissions.py").write_text(r'''import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import require_roles, active_enrollment
from app.models import Assessment, Role, Submission, User
from app.schemas import SubmissionOut

router = APIRouter(prefix="/submissions", tags=["submissions"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/{assessment_id}", response_model=SubmissionOut, status_code=201)
def upload_submission(assessment_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_roles(Role.student))):
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    
    enrollment = active_enrollment(db, user.student.id, assessment.section_id)
    if not enrollment:
        raise HTTPException(403, "You are not enrolled in this section")

    file_path = os.path.join(UPLOAD_DIR, f"{user.id}_{assessment_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    submission = Submission(
        assessment_id=assessment.id,
        enrollment_id=enrollment.id,
        file_url=file_path
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission

@router.get("/{assessment_id}", response_model=list[SubmissionOut])
def list_submissions(assessment_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.teacher))):
    return db.scalars(select(Submission).where(Submission.assessment_id == assessment_id)).all()
''', encoding="utf-8")
    print("Created submissions.py")

    # 5. Create Payroll Router
    Path("app/routers/payroll.py").write_text(r'''from decimal import Decimal
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import require_roles
from app.models import PayrollRecord, Role, Teacher, User
from app.schemas import PayrollCreate, PayrollOut

router = APIRouter(prefix="/payroll", tags=["payroll"])

@router.post("", response_model=PayrollOut, status_code=201)
def create_payroll(payload: PayrollCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin))):
    teacher = db.get(Teacher, payload.teacher_id)
    if not teacher:
        raise HTTPException(404, "Teacher not found")
    
    net = payload.base_amount - payload.deductions
    record = PayrollRecord(
        **payload.model_dump(),
        net_amount=net
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.get("/teacher/{teacher_id}", response_model=list[PayrollOut])
def get_teacher_payroll(teacher_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin))):
    return db.scalars(select(PayrollRecord).where(PayrollRecord.teacher_id == teacher_id).order_by(PayrollRecord.year.desc(), PayrollRecord.month.desc())).all()

@router.patch("/{payroll_id}/pay", response_model=PayrollOut)
def mark_as_paid(payroll_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin))):
    record = db.get(PayrollRecord, payroll_id)
    if not record:
        raise HTTPException(404, "Payroll record not found")
    if record.status == "paid":
        raise HTTPException(400, "Already paid")
    
    record.status = "paid"
    record.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record
''', encoding="utf-8")
    print("Created payroll.py")

    # 6. Update main.py to include new routers
    p = Path("app/main.py")
    text = p.read_text(encoding="utf-8")
    if "payroll" not in text:
        text = text.replace("from app.routers import academics, announcements, assessments, attendance, auth, finance", "from app.routers import academics, announcements, assessments, attendance, auth, finance, payroll, submissions")
        text = text.replace("app.include_router(announcements.router)", "app.include_router(announcements.router)\napp.include_router(payroll.router)\napp.include_router(submissions.router)")
        p.write_text(text, encoding="utf-8")
        print("Updated main.py")

    print("\nBackend expanded successfully!")

if __name__ == "__main__":
    main()
from pathlib import Path

def main():
    p = Path("app/routers")
    p.mkdir(parents=True, exist_ok=True)
    
    # Create payroll.py
    p.joinpath("payroll.py").write_text(r'''from decimal import Decimal
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
    record = PayrollRecord(**payload.model_dump(), net_amount=net)
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
    print("Created app/routers/payroll.py")

    # Create submissions.py
    p.joinpath("submissions.py").write_text(r'''import os
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
    print("Created app/routers/submissions.py")

if __name__ == "__main__":
    main()
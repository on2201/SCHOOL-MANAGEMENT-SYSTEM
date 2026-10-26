import os
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
    submission = Submission(assessment_id=assessment.id, enrollment_id=enrollment.id, file_url=file_path)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission

@router.get("/{assessment_id}", response_model=list[SubmissionOut])
def list_submissions(assessment_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.teacher))):
    return db.scalars(select(Submission).where(Submission.assessment_id == assessment_id)).all()

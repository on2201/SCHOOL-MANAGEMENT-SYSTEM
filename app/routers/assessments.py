from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import active_enrollment, assert_section_access, assert_student_access, require_roles, teacher_teaches_section
from app.models import Assessment, Enrollment, Role, Score, Student, Subject, Term, User
from app.schemas import AssessmentCreate, AssessmentOut, ReportCard, ScoreBulkIn, ScoreLine, SubjectResult

router = APIRouter(prefix="/assessments", tags=["assessments"])
author = require_roles(Role.admin, Role.teacher)
reader = require_roles(Role.admin, Role.teacher, Role.student, Role.guardian)

@router.post("", response_model=AssessmentOut, status_code=201)
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db), user: User = Depends(author)):
    assert_section_access(db, user, payload.section_id)
    if user.role == Role.teacher and not teacher_teaches_section(db, user.teacher.id, payload.section_id): raise HTTPException(403, "Not assigned to this section")
    if not db.get(Term, payload.term_id): raise HTTPException(404, "Term not found")
    assessment = Assessment(**payload.model_dump(), created_by_id=user.teacher.id if user.teacher else None)
    db.add(assessment); db.commit(); return assessment

@router.get("", response_model=list[AssessmentOut])
def list_assessments(section_id: int | None = None, term_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(reader)):
    if section_id: assert_section_access(db, user, section_id)
    q = select(Assessment).order_by(Assessment.due_date)
    if section_id: q = q.where(Assessment.section_id == section_id)
    if term_id: q = q.where(Assessment.term_id == term_id)
    return db.scalars(q).all()

@router.post("/{assessment_id}/scores")
def enter_scores(assessment_id: int, payload: ScoreBulkIn, db: Session = Depends(get_db), user: User = Depends(author)):
    assessment = db.get(Assessment, assessment_id)
    if not assessment: raise HTTPException(404, "Assessment not found")
    assert_section_access(db, user, assessment.section_id)
    if user.role == Role.teacher and not teacher_teaches_section(db, user.teacher.id, assessment.section_id): raise HTTPException(403, "Not assigned to this section")
    saved = 0
    for item in payload.records:
        if item.score > assessment.max_score: raise HTTPException(422, f"Score {item.score} exceeds max_score {assessment.max_score} for student {item.student_id}")
        enrollment = active_enrollment(db, item.student_id, assessment.section_id)
        if not enrollment: raise HTTPException(422, f"Student {item.student_id} is not enrolled in this section")
        row = db.scalar(select(Score).where(Score.assessment_id == assessment.id, Score.enrollment_id == enrollment.id))
        if row:
            row.score = item.score; row.comment = item.comment; row.graded_by_id = user.teacher.id if user.teacher else None
        else:
            db.add(Score(assessment_id=assessment.id, enrollment_id=enrollment.id, score=item.score, comment=item.comment, graded_by_id=user.teacher.id if user.teacher else None))
        saved += 1
    db.commit(); return {"saved": saved}

@router.get("/students/{student_id}/report", response_model=ReportCard)
def report_card(student_id: int, term_id: int, db: Session = Depends(get_db), user: User = Depends(reader)):
    assert_student_access(db, user, student_id)
    student = db.get(Student, student_id); term = db.get(Term, term_id)
    if not student or not term: raise HTTPException(404, "Student or term not found")
    enrollment = db.scalar(select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.is_active.is_(True)).order_by(Enrollment.enrolled_on.desc()).limit(1))
    if not enrollment:
        return ReportCard(student_id=student_id, student_name=student.full_name, term_id=term_id, term_name=term.name, subjects=[], overall_percentage=0.0)
    rows = db.execute(select(Assessment, Subject, Score).join(Subject, Subject.id == Assessment.subject_id).outerjoin(Score, and_(Score.assessment_id == Assessment.id, Score.enrollment_id == enrollment.id)).where(Assessment.section_id == enrollment.section_id, Assessment.term_id == term_id).order_by(Subject.name, Assessment.due_date)).all()
    grouped: dict[int, SubjectResult] = {}
    for assessment, subject, score in rows:
        bucket = grouped.setdefault(subject.id, SubjectResult(subject_id=subject.id, subject_name=subject.name, lines=[], total_scored=Decimal("0.00"), total_possible=Decimal("0.00"), percentage=0.0))
        bucket.lines.append(ScoreLine(assessment_id=assessment.id, title=assessment.title, type=assessment.type, score=score.score if score else None, max_score=assessment.max_score, comment=score.comment if score else None))
        if score: bucket.total_scored += score.score
        bucket.total_possible += assessment.max_score
    subjects: list[SubjectResult] = []; scored_total = Decimal("0.00"); possible_total = Decimal("0.00")
    for bucket in grouped.values():
        bucket.percentage = float(bucket.total_scored / bucket.total_possible * 100) if bucket.total_possible else 0.0
        scored_total += bucket.total_scored; possible_total += bucket.total_possible; subjects.append(bucket)
    return ReportCard(student_id=student.id, student_name=student.full_name, term_id=term.id, term_name=term.name, subjects=subjects, overall_percentage=float(scored_total / possible_total * 100) if possible_total else 0.0)

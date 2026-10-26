from decimal import Decimal
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

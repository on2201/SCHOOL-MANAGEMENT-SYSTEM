from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import require_roles
from app.models import Student, Teacher, Invoice, InvoiceStatus, Role, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.admin))):
    total_students = db.scalar(select(func.count()).select_from(Student)) or 0
    total_teachers = db.scalar(select(func.count()).select_from(Teacher)) or 0
    
    unpaid_invoices = db.scalars(select(Invoice).where(Invoice.status != InvoiceStatus.paid)).all()
    outstanding_fees = sum((inv.balance for inv in unpaid_invoices), start=0)
    
    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "outstanding_fees": float(outstanding_fees)
    }
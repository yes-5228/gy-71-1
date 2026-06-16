from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.contract import Contract
from app.models.workstation import Workstation
from app.schemas.contract import ContractCreate, ContractRenew, ContractUpdate


def list_contracts(db: Session, status: str | None = None) -> list[Contract]:
    stmt = (
        select(Contract)
        .options(joinedload(Contract.workstation))
        .order_by(Contract.end_date.asc())
    )
    if status:
        stmt = stmt.where(Contract.status == status)
    return list(db.scalars(stmt).all())


def get_contract(db: Session, contract_id: int) -> Contract | None:
    stmt = (
        select(Contract)
        .options(joinedload(Contract.workstation))
        .where(Contract.id == contract_id)
    )
    return db.scalars(stmt).first()


def create_contract(db: Session, payload: ContractCreate) -> Contract:
    workstation = db.get(Workstation, payload.workstation_id)
    if not workstation:
        raise ValueError("workstation_not_found")
    if workstation.status not in {"available", "reserved"}:
        raise ValueError("workstation_not_available")
    if payload.end_date <= payload.start_date:
        raise ValueError("invalid_contract_dates")

    contract = Contract(
        **payload.model_dump(),
        contract_no=f"CT-{date.today().strftime('%Y%m%d')}-{payload.workstation_id:03d}",
        status="active",
    )
    workstation.status = "leased"
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def renew_contract(db: Session, contract_id: int, payload: ContractRenew) -> Contract:
    original = get_contract(db, contract_id)
    if not original:
        raise ValueError("contract_not_found")
    if original.status != "active":
        raise ValueError("contract_not_active")
    if payload.end_date <= payload.start_date:
        raise ValueError("invalid_contract_dates")
    if payload.start_date < original.end_date:
        raise ValueError("renew_start_before_original_end")

    new_contract_no = f"CT-{date.today().strftime('%Y%m%d')}-{original.workstation_id:03d}-R{original.renewal_count + 1}"

    deposit = payload.deposit if payload.deposit is not None else original.deposit
    tenant_name = payload.tenant_name if payload.tenant_name else original.tenant_name
    tenant_contact = payload.tenant_contact if payload.tenant_contact is not None else original.tenant_contact

    new_contract = Contract(
        tenant_name=tenant_name,
        tenant_contact=tenant_contact,
        workstation_id=original.workstation_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        monthly_rent=payload.monthly_rent,
        deposit=deposit,
        contract_no=new_contract_no,
        status="active",
        parent_contract_id=original.id,
        renewal_count=original.renewal_count + 1,
    )

    original.status = "renewed"

    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)
    return new_contract


def get_renewal_history(db: Session, contract_id: int) -> list[Contract]:
    contract = get_contract(db, contract_id)
    if not contract:
        raise ValueError("contract_not_found")

    stmt = (
        select(Contract)
        .where(Contract.workstation_id == contract.workstation_id)
        .order_by(Contract.start_date.asc(), Contract.signed_at.asc())
    )
    return list(db.scalars(stmt).all())


def update_contract(db: Session, contract_id: int, payload: ContractUpdate) -> Contract | None:
    contract = db.get(Contract, contract_id)
    if not contract:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(contract, key, value)
    if contract.status in {"terminated", "expired"} and contract.workstation:
        contract.workstation.status = "available"
    db.commit()
    db.refresh(contract)
    return contract


def expiring_contracts(db: Session, days: int) -> list[Contract]:
    today = date.today()
    until = date.fromordinal(today.toordinal() + days)
    stmt = (
        select(Contract)
        .options(joinedload(Contract.workstation))
        .where(Contract.status == "active", Contract.end_date >= today, Contract.end_date <= until)
        .order_by(Contract.end_date.asc())
    )
    return list(db.scalars(stmt).all())

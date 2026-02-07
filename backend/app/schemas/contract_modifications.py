"""
Contract modification and CLIN schemas.
"""

from datetime import date, datetime

from pydantic import BaseModel


class ModificationCreate(BaseModel):
    modification_number: str
    mod_type: str | None = None
    description: str | None = None
    effective_date: date | None = None
    value_change: float | None = None


class ModificationRead(BaseModel):
    id: int
    contract_id: int
    modification_number: str
    mod_type: str | None
    description: str | None
    effective_date: date | None
    value_change: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CLINCreate(BaseModel):
    clin_number: str
    description: str | None = None
    clin_type: str | None = None
    unit_price: float | None = None
    quantity: int | None = None
    total_value: float | None = None
    funded_amount: float | None = None


class CLINUpdate(BaseModel):
    description: str | None = None
    clin_type: str | None = None
    unit_price: float | None = None
    quantity: int | None = None
    total_value: float | None = None
    funded_amount: float | None = None


class CLINRead(BaseModel):
    id: int
    contract_id: int
    clin_number: str
    description: str | None
    clin_type: str | None
    unit_price: float | None
    quantity: int | None
    total_value: float | None
    funded_amount: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

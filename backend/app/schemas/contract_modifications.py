"""
Contract modification and CLIN schemas.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ModificationCreate(BaseModel):
    modification_number: str
    mod_type: Optional[str] = None
    description: Optional[str] = None
    effective_date: Optional[date] = None
    value_change: Optional[float] = None


class ModificationRead(BaseModel):
    id: int
    contract_id: int
    modification_number: str
    mod_type: Optional[str]
    description: Optional[str]
    effective_date: Optional[date]
    value_change: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class CLINCreate(BaseModel):
    clin_number: str
    description: Optional[str] = None
    clin_type: Optional[str] = None
    unit_price: Optional[float] = None
    quantity: Optional[int] = None
    total_value: Optional[float] = None
    funded_amount: Optional[float] = None


class CLINUpdate(BaseModel):
    description: Optional[str] = None
    clin_type: Optional[str] = None
    unit_price: Optional[float] = None
    quantity: Optional[int] = None
    total_value: Optional[float] = None
    funded_amount: Optional[float] = None


class CLINRead(BaseModel):
    id: int
    contract_id: int
    clin_number: str
    description: Optional[str]
    clin_type: Optional[str]
    unit_price: Optional[float]
    quantity: Optional[int]
    total_value: Optional[float]
    funded_amount: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

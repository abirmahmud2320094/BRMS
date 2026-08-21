from datetime import date
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class Role(str, Enum):
    administrator = "administrator"
    building_manager = "building_manager"
    accountant = "accountant"


class RecordStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class UserProfileBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: Role
    status: RecordStatus = RecordStatus.active


class UserCreate(UserProfileBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role: Optional[Role] = None
    status: Optional[RecordStatus] = None


class BuildingBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    address: str = Field(min_length=3, max_length=300)
    city: str = Field(default="Dhaka", min_length=2, max_length=100)
    contact_phone: Optional[str] = Field(default=None, max_length=40)
    total_area: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=1000)


class FloorBase(BaseModel):
    building_id: str
    name: str = Field(min_length=1, max_length=100)
    level: int = Field(ge=-10, le=200)
    description: Optional[str] = Field(default=None, max_length=500)


class ShopBase(BaseModel):
    floor_id: str
    shop_number: str = Field(min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, max_length=120)
    monthly_rent: float = Field(default=0, ge=0)
    area_sqft: Optional[float] = Field(default=None, ge=0)
    status: Literal["available", "occupied", "inactive"] = "available"
    notes: Optional[str] = Field(default=None, max_length=500)


class TenantBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    business_name: Optional[str] = Field(default=None, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: Optional[EmailStr] = None
    national_id: Optional[str] = Field(default=None, max_length=80)
    address: Optional[str] = Field(default=None, max_length=300)
    status: RecordStatus = RecordStatus.active


class TenancyBase(BaseModel):
    tenant_id: str
    shop_id: str
    start_date: date
    end_date: Optional[date] = None
    monthly_rent: float = Field(ge=0)
    security_deposit: float = Field(default=0, ge=0)
    status: Literal["active", "ended"] = "active"
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("end_date")
    @classmethod
    def check_dates(cls, value, info):
        start = info.data.get("start_date")
        if value and start and value < start:
            raise ValueError("End date must be later than the start date")
        return value


class RentPaymentBase(BaseModel):
    tenancy_id: str
    accounting_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    amount: float = Field(ge=0)
    payment_date: Optional[date] = None
    status: Literal["paid", "unpaid", "partial"] = "paid"
    reference: Optional[str] = Field(default=None, max_length=120)
    note: Optional[str] = Field(default=None, max_length=500)


class UtilityBillBase(BaseModel):
    shop_id: str
    tenancy_id: Optional[str] = None
    utility_type: Literal["electricity", "water", "gas", "service_charge"]
    accounting_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    amount: float = Field(ge=0)
    due_date: Optional[date] = None
    status: Literal["paid", "unpaid", "partial"] = "unpaid"
    note: Optional[str] = Field(default=None, max_length=500)


class MaintenanceBase(BaseModel):
    scope_type: Literal["building", "floor", "shop"] = "building"
    scope_id: Optional[str] = None
    maintenance_date: date
    description: str = Field(min_length=3, max_length=1000)
    cost: float = Field(ge=0)
    status: Literal["planned", "in_progress", "completed"] = "completed"
    notes: Optional[str] = Field(default=None, max_length=1000)


class DemoLogin(BaseModel):
    email: EmailStr
    password: str


class GenericUpdate(BaseModel):
    data: dict

import pytest
from pydantic import ValidationError
from app.models.schemas import RentPaymentBase, UtilityBillBase, TenancyBase


def test_accounting_month_validation():
    with pytest.raises(ValidationError):
        RentPaymentBase(tenancy_id="t1", accounting_month="2026-13", amount=100)


def test_utility_type_validation():
    with pytest.raises(ValidationError):
        UtilityBillBase(shop_id="s1", utility_type="internet", accounting_month="2026-08", amount=100)


def test_tenancy_date_order():
    with pytest.raises(ValidationError) as exc_info:
        TenancyBase(tenant_id="t1", shop_id="s1", start_date="2026-08-20", end_date="2026-08-01", monthly_rent=1000)
    assert "End date must be later than the start date" in str(exc_info.value)

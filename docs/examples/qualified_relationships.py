from importlib import reload

# --8<-- [start:load]
from account_models import billing, support

from corm import Entity, Nested, RegistryError, Storage


class Customer(Entity):
    payer: billing.Account = Nested("account_models.billing.Account")
    contact: support.Account = Nested("account_models.support.Account")


customer = Customer(
    {"payer": {"invoice_email": "a@example.org"}, "contact": {"queue": "returns"}},
    Storage(),
)
assert type(customer.payer) is billing.Account
assert type(customer.contact) is support.Account
assert customer.dict() == {
    "payer": {"invoice_email": "a@example.org"},
    "contact": {"queue": "returns"},
}
# --8<-- [end:load]


class AmbiguousCustomer(Entity):
    account = Nested("Account")


try:
    AmbiguousCustomer({"account": {}}, Storage())
except RegistryError as error:
    assert "account_models.billing.Account" in str(error)
    assert "account_models.support.Account" in str(error)
else:
    raise AssertionError("A short name shared by two models is ambiguous")


old_billing_account = billing.Account
reload(billing)
assert billing.Account is not old_billing_account
assert type(customer.payer) is old_billing_account
assert type(Customer(customer.dict(), Storage()).payer) is old_billing_account


class NewCustomer(Entity):
    payer: billing.Account = Nested("account_models.billing.Account")
    contact: support.Account = Nested("account_models.support.Account")


fresh = NewCustomer(customer.dict(), Storage())
assert type(fresh.payer) is billing.Account
assert type(fresh.contact) is support.Account
assert fresh.dict() == customer.dict()

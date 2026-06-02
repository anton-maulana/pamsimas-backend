from fastcrud import FastCRUD

from ..models.customer import Customer
from ..schemas.customer import (
    CustomerCreateInternal,
    CustomerDelete,
    CustomerRead,
    CustomerUpdate,
    CustomerUpdateInternal,
)

CRUDCustomer = FastCRUD[
    Customer,
    CustomerCreateInternal,
    CustomerUpdate,
    CustomerUpdateInternal,
    CustomerDelete,
    CustomerRead,
]
crud_customers = CRUDCustomer(Customer)

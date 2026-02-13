from fastcrud import FastCRUD

from ..models.customer import Customer
from ..schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

CRUDCustomer = FastCRUD[Customer, CustomerCreate, CustomerUpdate, CustomerUpdate, CustomerRead, CustomerRead]
crud_customer = CRUDCustomer(Customer)

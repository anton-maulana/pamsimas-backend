from fastcrud import FastCRUD

from ..models.payment import Payment
from ..schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

CRUDPayment = FastCRUD[Payment, PaymentCreate, PaymentUpdate, PaymentUpdate, PaymentRead, PaymentRead]
crud_payment = CRUDPayment(Payment)

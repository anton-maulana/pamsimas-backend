from fastcrud import FastCRUD

from ..models.bill import Bill
from ..schemas.bill import BillCreate, BillRead, BillUpdate

CRUDBill = FastCRUD[Bill, BillCreate, BillUpdate, BillUpdate, BillRead, BillRead]
crud_bill = CRUDBill(Bill)

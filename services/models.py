from pydantic import BaseModel
from typing import List, Optional

class Customer(BaseModel):
    id: Optional[int] = None
    email: str
    first_name: str
    last_name: str

class CustomerResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    created_at: str
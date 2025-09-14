from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="Customer Service API",
    description="API for managing customer data",
    version="1.0.0"
)

# Existing models
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

# Existing endpoints (these are already documented)
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"message": "Customer Service is running"}

@app.post("/api/customers/", response_model=CustomerResponse, tags=["Customers"])
async def create_customer(customer: Customer):
    """
    Create a new customer account
    """
    # Simulate customer creation
    new_customer = CustomerResponse(
        id=123,
        email=customer.email,
        first_name=customer.first_name,
        last_name=customer.last_name,
        created_at="2025-01-15T10:30:00Z"
    )
    return new_customer

@app.get("/api/customers/{customer_id}", response_model=CustomerResponse, tags=["Customers"])
async def get_customer(customer_id: int):
    """
    Retrieve customer by ID
    """
    if customer_id != 123:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse(
        id=customer_id,
        email="john@example.com",
        first_name="John",
        last_name="Doe",
        created_at="2025-01-15T10:30:00Z"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
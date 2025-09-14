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

# NEW MODEL - This will be detected by AI
class CustomerPreferences(BaseModel):
    categories: List[str]
    price_range: Optional[dict] = {"min": 0, "max": 1000}
    brands: Optional[List[str]] = []
    newsletter_subscription: bool = True

class PreferencesResponse(BaseModel):
    id: int
    customer_id: int
    categories: List[str]
    price_range: dict
    brands: List[str]
    newsletter_subscription: bool
    created_at: str
    updated_at: str

# Existing endpoints (unchanged)
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

# 🚨 NEW ENDPOINT - This should trigger documentation generation
@app.post("/api/customers/{customer_id}/preferences", response_model=PreferencesResponse, tags=["Preferences"])
async def create_customer_preferences(customer_id: int, preferences: CustomerPreferences):
    """
    Create or update customer preferences for personalized recommendations.
    
    This endpoint allows customers to set their shopping preferences including:
    - Product categories they're interested in
    - Price range for recommendations  
    - Preferred brands
    - Newsletter subscription status
    """
    # Simulate preferences creation
    new_preferences = PreferencesResponse(
        id=456,
        customer_id=customer_id,
        categories=preferences.categories,
        price_range=preferences.price_range,
        brands=preferences.brands,
        newsletter_subscription=preferences.newsletter_subscription,
        created_at="2025-01-15T14:30:00Z",
        updated_at="2025-01-15T14:30:00Z"
    )
    return new_preferences

# 🚨 ANOTHER NEW ENDPOINT - This should also be detected
@app.get("/api/customers/{customer_id}/preferences", response_model=PreferencesResponse, tags=["Preferences"])
async def get_customer_preferences(customer_id: int):
    """
    Retrieve customer preferences by customer ID.
    
    Returns the customer's current preferences for personalized recommendations.
    """
    # Simulate preferences retrieval
    if customer_id != 123:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return PreferencesResponse(
        id=456,
        customer_id=customer_id,
        categories=["electronics", "books", "clothing"],
        price_range={"min": 10, "max": 500},
        brands=["Apple", "Nike", "Amazon"],
        newsletter_subscription=True,
        created_at="2025-01-15T14:30:00Z",
        updated_at="2025-01-15T14:30:00Z"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Customer Service API Reference

## Overview
The Customer Service API provides endpoints for managing customer accounts and data.

## Endpoints

### POST /api/customers/
Create a new customer account.

**Request Body:**
```json
{
  "email": "john@example.com",
  "first_name": "John", 
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "id": 123,
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe", 
  "created_at": "2025-01-15T10:30:00Z"
}
```

### GET /api/customers/{customer_id}
Retrieve customer information by ID.

**Response:**
```json
{
  "id": 123,
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2025-01-15T10:30:00Z"
}
```
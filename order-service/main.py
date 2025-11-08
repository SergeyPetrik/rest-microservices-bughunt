import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel  # ВИПРАВЛЕННЯ 7: додано для валідації
import httpx
import asyncio

app = FastAPI(title="OrderService")

lock = asyncio.Lock()

AUTH_URL = os.getenv("AUTH_URL", "http://localhost:8001")
PRODUCT_URL = os.getenv("PRODUCT_URL", "http://localhost:8002")

ORDERS: list[dict] = []

# >>> Pydantic модель для валідації вхідних даних
class CreateOrderPayload(BaseModel):
    productId: int
    qty: int

@app.post("/orders")
async def create_order(payload: CreateOrderPayload, authorization: str | None = Header(default=None)):  # >>> payload тепер CreateOrderPayload
    """
    Очікуваний payload: {"productId": int, "qty": int}
    """
    # >>> Обробка помилок запиту до AuthService
    try:
        async with httpx.AsyncClient() as client:
            # >>> Перевірка відповіді від AuthService
            auth_response = await client.get(f"{AUTH_URL}/whoami", headers={"Authorization": authorization or ""})
            
            # >>> Перевірка статус-коду відповіді
            if auth_response.status_code != 200:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            
            # >>> Отримання email користувача для прив'язки до замовлення
            user_data = auth_response.json()
            user_email = user_data.get("email")
    
    # >>> Обробка помилок при недоступності AuthService
    except httpx.RequestError:
        return JSONResponse({"error": "auth service unavailable"}, status_code=503)
    
    # >>> Перевірка існування продукту
    try:
        async with httpx.AsyncClient() as client:
            product_response = await client.get(f"{PRODUCT_URL}/products/{payload.productId}")
            
            # >>> Перевірка, чи існує продукт
            if product_response.status_code != 200:
                return JSONResponse({"error": "product not found"}, status_code=404)
            
            # >>> Отримання інформації про stock
            product_data = product_response.json()
            in_stock = product_data.get("inStock", 0)
            
            # >>> Перевірка наявності на складі
            if in_stock < payload.qty:
                return JSONResponse({"error": f"insufficient stock: available {in_stock}, requested {payload.qty}"}, status_code=400)
    
    except httpx.RequestError:
        return JSONResponse({"error": "product service unavailable"}, status_code=503)
    
    # >>> Використання thread-safe способу генерації ID
    async with lock:
        order = {
            "order_id": len(ORDERS) + 1,
            "product_id": payload.productId,
            "quantity": payload.qty,
            "status": "created",
            # >>> Прив'язка замовлення до користувача
            "user_email": user_email,
        }
        ORDERS.append(order)

    # >>>  Виклик ендпоінту для зменшення stock
    try:
        async with httpx.AsyncClient() as client:
            reduce_response = await client.patch(
                f"{PRODUCT_URL}/products/{payload.productId}/reduce-stock",
                params={"quantity": payload.qty}
            )
            
            if reduce_response.status_code != 200:
                return JSONResponse({"error": "failed to reduce stock"}, status_code=500)
    
    except httpx.RequestError:
        return JSONResponse({"error": "product service unavailable when reducing stock"}, status_code=503)
    
    return JSONResponse(order, status_code=201)

@app.get("/orders")
async def list_orders():
    return {"orders": ORDERS}

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="ProductService")

# >>> Pydantic модель для валідації структури товару
class Product(BaseModel):
    product_id: int
    name: str
    price: float  # >>> змінено з str на float
    inStock: int  # >>> явна типізація як int

# Нехай у нас є простий каталог товарів
# >>> price тепер число (float), а не рядок
PRODUCTS = [
    {"product_id": 100, "name": "Keyboard", "price": 59.99, "inStock": 5},
    {"product_id": 101, "name": "Mouse", "price": 29.99, "inStock": 0},
]

@app.get("/products")
async def list_products():
    return {"items": PRODUCTS}

@app.get("/products/{pid}")
async def get_product(pid: int):
    for p in PRODUCTS:
        if p["product_id"] == pid:
            return p
    # >>> повертається 404 замість 200 для відсутнього товару
    raise HTTPException(status_code=404, detail="not found")

# >>> Ендпоінт для зменшення stock при створенні замовлення
@app.patch("/products/{pid}/reduce-stock")
async def reduce_stock(pid: int, quantity: int):
    """
    Зменшує stock товару при створенні замовлення.
    Має викликатися з OrderService після успішного створення замовлення.
    """
    for p in PRODUCTS:
        if p["product_id"] == pid:
            if p["inStock"] < quantity:
                raise HTTPException(status_code=400, detail="insufficient stock")
            
            p["inStock"] -= quantity
            return {"product_id": pid, "new_stock": p["inStock"]}
    
    raise HTTPException(status_code=404, detail="product not found")

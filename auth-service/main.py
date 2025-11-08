from fastapi import FastAPI, Response, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

app = FastAPI(title="AuthService")

# Простеньке "сховище" користувачів у пам'яті (для навчальних цілей)
USERS = {
    "alice@example.com": {"password": "alice123", "id": 1},
    "bob@example.com": {"password": "bob123", "id": 2},
}

# >>> Pydantic модель для валідації вхідних даних
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# >>> POST замість GET
@app.post("/login")
async def login(credentials: LoginRequest, response: Response):
    user = USERS.get(credentials.email)
    if not user or user["password"] != credentials.password:
        # >>> Некоректний HTTP статус при помилках (200 замість 401)
        return JSONResponse({"message": "invalid credentials"}, status_code=401)

    # TOKЕН спрощений (НЕ використовуйте так у проді!)
    token = f"fake-token-for-{credentials.email}"

    return {"accessToken": token, "userId": user["id"]}

@app.get("/whoami")
async def whoami(authorization: str | None = Header(default=None)):
    """
    Стверджується, що токен подається як Bearer у заголовку Authorization.
    """
    if not authorization or not authorization.startswith("Bearer"):
        # >>> Некоректний HTTP статус при помилках (200 замість 401)
        return JSONResponse({"error": "missing or invalid token"}, status_code=401)
    
    token = authorization.removeprefix("Bearer ")
    # Немає перевірки підпису/строку дії — навчальний спрощений варіант
    email = token.replace("fake-token-for-", "")
    user = USERS.get(email)
    if not user:
        return JSONResponse({"error": "invalid token"}, status_code=401)
    return {"email": email, "status_code": 200}

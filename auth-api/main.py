from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ldap_adapter import LDAPAuthAdapter
import jwt
from datetime import datetime, timedelta, timezone

app = FastAPI(title="API de Autenticación Centralizada")
ldap_service = LDAPAuthAdapter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción, aquí iría la IP de tu servidor
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

SECRET_KEY = "super_clave_secreta_del_proyecto"
ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/api/v1/auth/login")
def login(credentials: LoginRequest):
    es_valido = ldap_service.authenticate_user(credentials.username, credentials.password)
    
    if not es_valido:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
    access_token = create_access_token(data={"sub": credentials.username}, expires_delta=timedelta(minutes=30))
    
    return {
        "status": "success",
        "username": credentials.username,  
        "access_token": access_token
    }

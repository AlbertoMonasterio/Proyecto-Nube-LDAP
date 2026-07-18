import os
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from ldap_adapter import LDAPAuthAdapter
import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="API de Autenticación Centralizada UCAB")
ldap_service = LDAPAuthAdapter()
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_clave_secreta_del_proyecto")
ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    lastname: str
    email: str
    department: str = "estudiantes"

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token expirado o inválido")

@app.post("/api/v1/auth/login")
def login(credentials: LoginRequest):
    es_valido = ldap_service.authenticate_user(credentials.username, credentials.password)
    
    if not es_valido:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
    access_token = create_access_token(data={"sub": credentials.username}, expires_delta=timedelta(minutes=60))
    
    return {
        "status": "success",
        "username": credentials.username,  
        "access_token": access_token
    }

@app.get("/api/v1/users")
def get_users(current_user: str = Depends(verify_token)):
    users = ldap_service.get_all_users()
    return {"status": "success", "users": users}

@app.post("/api/v1/users")
def register_user(user: RegisterRequest):
    # En este caso permitiremos el registro publico para el demo universitario
    success = ldap_service.create_user(
        user.username, 
        user.password, 
        user.lastname, 
        user.email, 
        user.department
    )
    if not success:
        raise HTTPException(status_code=400, detail="Error al crear el usuario en LDAP. Puede que el usuario ya exista o el departamento sea inválido.")
        
    return {"status": "success", "message": "Usuario creado exitosamente"}

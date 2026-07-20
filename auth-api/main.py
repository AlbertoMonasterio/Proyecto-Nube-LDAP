import os
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from ldap_adapter import LDAPAuthAdapter
import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import logging
import re

# Configuración del Logger de Auditoría
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("audit.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - AUDIT - %(message)s'))
audit_logger.addHandler(file_handler)

load_dotenv()

app = FastAPI(title="API de Autenticación Centralizada UCAB")
ldap_service = LDAPAuthAdapter()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:8000", "http://127.0.0.1:8000"], 
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecreto_cambiar_en_produccion")
ALGORITHM = "HS256"

def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if not re.search(r"[A-Z]", v):
        raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
    if not re.search(r"\d", v):
        raise ValueError("La contraseña debe incluir al menos un número")
    return v

class LoginRequest(BaseModel):
    username: str
    password: str

class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    firstname: str
    lastname: str
    email: EmailStr
    department: str = "estudiantes"

    @field_validator('password')
    @classmethod
    def check_pass(cls, v):
        return validate_password_strength(v)

class RoleChangeRequest(BaseModel):
    roles: list[str]

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def check_new_pass(cls, v):
        return validate_password_strength(v)

class CurrentUser(BaseModel):
    username: str
    roles: list[str] = []

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(request: Request) -> CurrentUser:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return CurrentUser(username=username, roles=payload.get("roles", []))
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token expirado o inválido")

def require_role(*allowed_roles: str):
    def _check(current_user: CurrentUser = Depends(verify_token)) -> CurrentUser:
        if not any(r in current_user.roles for r in allowed_roles):
            raise HTTPException(status_code=403, detail="No tiene permisos para esta acción")
        return current_user
    return _check

@app.post("/api/v1/auth/login")
def login(credentials: LoginRequest, response: Response):
    es_valido = ldap_service.authenticate_user(credentials.username, credentials.password)

    if not es_valido:
        audit_logger.warning(f"Intento fallido de login para el usuario: {credentials.username}")
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    audit_logger.info(f"Usuario autenticado exitosamente: {credentials.username}")

    roles = ldap_service.get_user_roles(credentials.username)
    access_token = create_access_token(
        data={"sub": credentials.username, "roles": roles},
        expires_delta=timedelta(minutes=60),
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=3600,
        samesite="lax",
        secure=False
    )

    return {
        "status": "success",
        "username": credentials.username,
        "roles": roles
    }

@app.post("/api/v1/auth/logout")
def logout(response: Response, current_user: CurrentUser = Depends(verify_token)):
    audit_logger.info(f"Usuario cerró sesión: {current_user.username}")
    response.delete_cookie("access_token")
    return {"status": "success"}

@app.get("/api/v1/users")
def get_users(current_user: CurrentUser = Depends(verify_token)):
    users = ldap_service.get_all_users()
    
    # RBAC Privacidad: Admins y Profesores ven todo el directorio
    if "admins" in current_user.roles or "profesores" in current_user.roles:
        for user in users:
            user["roles"] = ldap_service.get_user_roles(user["username"])
        return {"status": "success", "users": users}
        
    # Estudiantes (o usuarios sin rol especial) solo se ven a sí mismos
    mis_datos = [u for u in users if u["username"] == current_user.username]
    for user in mis_datos:
        user["roles"] = ldap_service.get_user_roles(user["username"])
    return {"status": "success", "users": mis_datos}

@app.post("/api/v1/users")
def create_user(user: AdminCreateUserRequest, admin: CurrentUser = Depends(require_role("admins"))):
    success = ldap_service.create_user(
        user.username,
        user.password,
        user.firstname,
        user.lastname,
        user.email,
        user.department
    )
    if not success:
        audit_logger.error(f"Error al crear usuario {user.username} por admin {admin.username}")
        raise HTTPException(status_code=400, detail="Error al crear el usuario en LDAP. Puede que el usuario ya exista o el departamento sea inválido.")

    audit_logger.info(f"Admin {admin.username} creó un nuevo usuario: {user.username} en el departamento {user.department}")
    return {"status": "success", "message": "Usuario creado exitosamente"}

@app.delete("/api/v1/users/{username}")
def delete_user(username: str, admin: CurrentUser = Depends(require_role("admins"))):
    if username == admin.username:
        raise HTTPException(status_code=400, detail="No puede eliminar su propio usuario")
    success = ldap_service.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o error al eliminar")
        
    audit_logger.info(f"Admin {admin.username} eliminó al usuario: {username}")
    return {"status": "success", "message": f"Usuario {username} eliminado"}

@app.put("/api/v1/users/{username}/roles")
def update_user_roles(username: str, body: RoleChangeRequest, admin: CurrentUser = Depends(require_role("admins"))):
    if username == admin.username and "admins" not in body.roles:
        raise HTTPException(status_code=400, detail="No puede quitarse su propio rol de administrador")
    
    try:
        ldap_service.set_user_roles(username, body.roles)
        audit_logger.info(f"Admin {admin.username} actualizó los roles de {username} a: {body.roles}")
        return {"status": "success", "message": f"Roles actualizados para {username}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al actualizar roles: {str(e)}")

@app.put("/api/v1/users/me/password")
def change_my_password(body: PasswordChangeRequest, current_user: CurrentUser = Depends(verify_token)):
    try:
        ldap_service.change_password(current_user.username, body.old_password, body.new_password)
        audit_logger.info(f"El usuario {current_user.username} actualizó su contraseña con éxito")
        return {"status": "success", "message": "Contraseña actualizada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/api/v1/audit/logs")
def get_audit_logs(admin: CurrentUser = Depends(require_role("admins"))):
    try:
        if not os.path.exists("audit.log"):
            return {"logs": []}
        with open("audit.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Devolvemos las últimas 100 líneas, invertidas para que las más nuevas salgan arriba
        return {"logs": [line.strip() for line in reversed(lines[-100:])]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error leyendo logs de auditoría")

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

class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    lastname: str
    email: str
    department: str = "estudiantes"

class RoleChangeRequest(BaseModel):
    action: str  # "add" | "remove"
    role: str    # "admins" | "profesores" | "estudiantes"

class CurrentUser(BaseModel):
    username: str
    roles: list[str] = []

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> CurrentUser:
    token = credentials.credentials
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
def login(credentials: LoginRequest):
    es_valido = ldap_service.authenticate_user(credentials.username, credentials.password)

    if not es_valido:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    roles = ldap_service.get_user_roles(credentials.username)
    access_token = create_access_token(
        data={"sub": credentials.username, "roles": roles},
        expires_delta=timedelta(minutes=60),
    )

    return {
        "status": "success",
        "username": credentials.username,
        "roles": roles,
        "access_token": access_token
    }

@app.get("/api/v1/users")
def get_users(current_user: CurrentUser = Depends(verify_token)):
    users = ldap_service.get_all_users()
    for user in users:
        user["roles"] = ldap_service.get_user_roles(user["username"])
    return {"status": "success", "users": users}

@app.post("/api/v1/users")
def create_user(user: AdminCreateUserRequest, admin: CurrentUser = Depends(require_role("admins"))):
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

@app.delete("/api/v1/users/{username}")
def delete_user(username: str, admin: CurrentUser = Depends(require_role("admins"))):
    if username == admin.username:
        raise HTTPException(status_code=400, detail="No puede eliminar su propio usuario")
    success = ldap_service.delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o error al eliminar")
    return {"status": "success", "message": f"Usuario {username} eliminado"}

@app.put("/api/v1/users/{username}/role")
def change_user_role(username: str, body: RoleChangeRequest, admin: CurrentUser = Depends(require_role("admins"))):
    if body.role not in ldap_service.ROLE_GROUPS:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Use uno de: {ldap_service.ROLE_GROUPS}")

    if body.action == "add":
        success = ldap_service.add_user_to_role(username, body.role)
    elif body.action == "remove":
        if username == admin.username and body.role == "admins":
            raise HTTPException(status_code=400, detail="No puede quitarse su propio rol de administrador")
        success = ldap_service.remove_user_from_role(username, body.role)
    else:
        raise HTTPException(status_code=400, detail="action debe ser 'add' o 'remove'")

    if not success:
        raise HTTPException(status_code=400, detail="No se pudo actualizar el rol (usuario/rol inexistente, o es el último miembro del grupo)")
    return {"status": "success", "message": f"Rol actualizado para {username}"}

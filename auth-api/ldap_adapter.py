import os
import base64
import hashlib
from ldap3 import Server, Connection, ALL, MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE, SUBTREE
from ldap3.core.exceptions import LDAPException
from dotenv import load_dotenv

load_dotenv()

def hash_ssha(password: str) -> str:
    salt = os.urandom(4)
    h = hashlib.sha1(password.encode('utf-8') + salt)
    return '{SSHA}' + base64.b64encode(h.digest() + salt).decode('utf-8')

class LDAPAuthAdapter:
    GROUPS_OU = "ou=grupos"
    ROLE_GROUPS = ["admins", "profesores", "estudiantes"]
    VALID_DEPARTMENTS = ["Ingenieria", "Derecho", "Medicina", "Administracion", "RRHH", "estudiantes", "profesores", "administrativo"]

    def __init__(self):
        self.server_uri = os.getenv("LDAP_URI", "ldap://openldap:389")
        self.base_dn = os.getenv("LDAP_BASE_DN", "dc=proyecto,dc=ucab")
        self.admin_dn = os.getenv("LDAP_ADMIN_DN", "cn=admin,dc=proyecto,dc=ucab")
        self.admin_pw = os.getenv("LDAP_ADMIN_PASSWORD", "admin")
        
        self.server = Server(self.server_uri, get_info=ALL)

    def _get_admin_connection(self) -> Connection:
        return Connection(self.server, user=self.admin_dn, password=self.admin_pw, auto_bind=True)

    def authenticate_user(self, username: str, password: str) -> bool:
        try:
            conn = self._get_admin_connection()
            conn.search(self.base_dn, f'(cn={username})', attributes=['cn'])
            
            if len(conn.entries) == 0:
                conn.unbind()
                return False
                
            user_real_dn = conn.entries[0].entry_dn
            user_conn = Connection(self.server, user=user_real_dn, password=password, auto_bind=True)
            user_conn.unbind()
            conn.unbind()
            
            return True
            
        except LDAPException as e:
            print(f"LDAP Auth Error: {e}")
            return False
        except Exception as e:
            print(f"Auth Error: {e}")
            return False

    def get_all_users(self) -> list:
        try:
            conn = self._get_admin_connection()
            # Buscar todos los inetOrgPerson
            conn.search(self.base_dn, '(objectClass=inetOrgPerson)', attributes=['cn', 'givenName', 'sn', 'mail', 'ou'])
            
            users = []
            for entry in conn.entries:
                # Extraer OU del DN si no viene como atributo
                dn_parts = entry.entry_dn.split(',')
                ou = "general"
                for part in dn_parts:
                    if part.startswith("ou="):
                        ou = part.replace("ou=", "")
                        break
                        
                user = {
                    "username": entry.cn.value if 'cn' in entry else "",
                    "firstname": entry.givenName.value if 'givenName' in entry else "",
                    "lastname": entry.sn.value if 'sn' in entry else "",
                    "email": entry.mail.value if 'mail' in entry else "",
                    "department": ou
                }
                users.append(user)
                
            conn.unbind()
            return users
        except Exception as e:
            print(f"Error listing users: {e}")
            return []

    def _get_user_dn(self, conn: Connection, username: str):
        conn.search(self.base_dn, f'(cn={username})', search_scope=SUBTREE, attributes=['cn'])
        if len(conn.entries) == 0:
            return None
        return conn.entries[0].entry_dn

    def get_user_roles(self, username: str) -> list:
        try:
            conn = self._get_admin_connection()
            user_dn = self._get_user_dn(conn, username)
            if user_dn is None:
                conn.unbind()
                return []
            groups_base = f"{self.GROUPS_OU},{self.base_dn}"
            conn.search(groups_base, f'(&(objectClass=groupOfNames)(member={user_dn}))',
                        search_scope=SUBTREE, attributes=['cn'])
            roles = [entry.cn.value for entry in conn.entries]
            conn.unbind()
            return roles
        except Exception as e:
            print(f"Error fetching roles: {e}")
            return []

    def set_user_roles(self, username: str, new_roles: list[str]) -> bool:
        conn = self._get_admin_connection()
        user_dn = self._get_user_dn(conn, username)
        if not user_dn:
            conn.unbind()
            raise ValueError(f"Usuario {username} no encontrado")
            
        current_roles = self.get_user_roles(username)
        
        roles_to_add = set(new_roles) - set(current_roles)
        roles_to_remove = set(current_roles) - set(new_roles)
        
        for role in roles_to_add:
            if role in self.ROLE_GROUPS:
                group_dn = f"cn={role},{self.GROUPS_OU},{self.base_dn}"
                conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn])]})
                
        for role in roles_to_remove:
            if role in self.ROLE_GROUPS:
                group_dn = f"cn={role},{self.GROUPS_OU},{self.base_dn}"
                conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
                
        conn.unbind()
        return True

    def delete_user(self, username: str) -> bool:
        try:
            conn = self._get_admin_connection()
            user_dn = self._get_user_dn(conn, username)
            if user_dn is None:
                conn.unbind()
                return False
            for role in self.ROLE_GROUPS:
                group_dn = f"cn={role},{self.GROUPS_OU},{self.base_dn}"
                conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
            success = conn.delete(user_dn)
            conn.unbind()
            return success
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def create_user(self, username: str, password: str, firstname: str, lastname: str, email: str, department: str = "estudiantes") -> bool:
        if department not in self.VALID_DEPARTMENTS:
            raise ValueError(f"Departamento {department} no es válido")
        try:
            conn = self._get_admin_connection()
            user_dn = f"cn={username},ou={department},{self.base_dn}"
            
            attrs = {
                'objectClass': ['inetOrgPerson'],
                'cn': username,
                'givenName': firstname,
                'sn': lastname,
                'userPassword': hash_ssha(password).encode('utf-8'),
                'mail': email
            }
            
            success = conn.add(user_dn, attributes=attrs)
            if not success:
                err_desc = conn.result.get('description', 'Error desconocido en LDAP')
                conn.unbind()
                raise Exception(err_desc)
            conn.unbind()
            return success
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        # Verificamos la clave anterior primero
        if not self.authenticate_user(username, old_password):
            raise ValueError("La contraseña actual es incorrecta")
            
        conn = self._get_admin_connection()
        user_dn = self._get_user_dn(conn, username)
        if not user_dn:
            conn.unbind()
            raise ValueError(f"Usuario {username} no encontrado")
            
        # Modificamos el atributo userPassword
        success = conn.modify(user_dn, {'userPassword': [(MODIFY_REPLACE, [hash_ssha(new_password).encode('utf-8')])]})
        if not success:
            err_desc = conn.result.get('description', 'Error cambiando contraseña')
            conn.unbind()
            raise Exception(err_desc)
            
        conn.unbind()
        return True

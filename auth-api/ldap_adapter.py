import os
from ldap3 import Server, Connection, ALL, MODIFY_ADD, MODIFY_DELETE, SUBTREE
from ldap3.core.exceptions import LDAPException
from dotenv import load_dotenv

load_dotenv()

class LDAPAuthAdapter:
    GROUPS_OU = "ou=grupos"
    ROLE_GROUPS = ["admins", "profesores", "estudiantes"]
    VALID_DEPARTMENTS = ["estudiantes", "profesores", "administrativo"]

    def __init__(self):
        self.server_uri = os.getenv("LDAP_URI", "ldap://openldap:389")
        self.base_dn = os.getenv("LDAP_BASE_DN", "dc=proyecto,dc=ucab")
        self.admin_dn = os.getenv("LDAP_ADMIN_DN", "cn=admin,dc=proyecto,dc=ucab")
        self.admin_pw = os.getenv("LDAP_ADMIN_PASSWORD", "admin")

    def _get_admin_connection(self) -> Connection:
        server = Server(self.server_uri, get_info=ALL)
        return Connection(server, user=self.admin_dn, password=self.admin_pw, auto_bind=True)

    def authenticate_user(self, username: str, password: str) -> bool:
        try:
            conn = self._get_admin_connection()
            conn.search(self.base_dn, f'(cn={username})', attributes=['cn'])
            
            if len(conn.entries) == 0:
                conn.unbind()
                return False
                
            user_real_dn = conn.entries[0].entry_dn
            user_conn = Connection(conn.server, user=user_real_dn, password=password, auto_bind=True)
            
            user_conn.unbind()
            conn.unbind()
            return True
            
        except LDAPException:
            return False
        except Exception:
            return False

    def get_all_users(self) -> list:
        try:
            conn = self._get_admin_connection()
            # Buscar todos los inetOrgPerson
            conn.search(self.base_dn, '(objectClass=inetOrgPerson)', attributes=['cn', 'sn', 'mail', 'ou'])
            
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

    def add_user_to_role(self, username: str, role: str) -> bool:
        if role not in self.ROLE_GROUPS:
            return False
        try:
            conn = self._get_admin_connection()
            user_dn = self._get_user_dn(conn, username)
            if user_dn is None:
                conn.unbind()
                return False
            group_dn = f"cn={role},{self.GROUPS_OU},{self.base_dn}"
            success = conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn])]})
            conn.unbind()
            return success
        except Exception as e:
            print(f"Error adding role: {e}")
            return False

    def remove_user_from_role(self, username: str, role: str) -> bool:
        if role not in self.ROLE_GROUPS:
            return False
        try:
            conn = self._get_admin_connection()
            user_dn = self._get_user_dn(conn, username)
            if user_dn is None:
                conn.unbind()
                return False
            group_dn = f"cn={role},{self.GROUPS_OU},{self.base_dn}"
            success = conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
            conn.unbind()
            return success
        except Exception as e:
            print(f"Error removing role: {e}")
            return False

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

    def create_user(self, username: str, password: str, lastname: str, email: str, department: str = "estudiantes") -> bool:
        if department not in self.VALID_DEPARTMENTS:
            return False
        try:
            conn = self._get_admin_connection()
            user_dn = f"cn={username},ou={department},{self.base_dn}"
            
            attrs = {
                'objectClass': ['inetOrgPerson'],
                'cn': username,
                'sn': lastname,
                'userPassword': password,
                'mail': email
            }
            
            success = conn.add(user_dn, attributes=attrs)
            conn.unbind()
            return success
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

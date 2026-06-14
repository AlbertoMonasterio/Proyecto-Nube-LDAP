from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPException

class LDAPAuthAdapter:
    def __init__(self):
        # Usamos el nombre del servicio 'openldap' definido en el docker-compose
        self.server_uri = 'ldap://openldap:389'
        self.base_dn = 'dc=proyecto,dc=ucab'
        self.admin_dn = 'cn=admin,dc=proyecto,dc=ucab'
        self.admin_pw = 'admin'

    def authenticate_user(self, username: str, password: str) -> bool:
        try:
            server = Server(self.server_uri, get_info=ALL)
            conn = Connection(server, user=self.admin_dn, password=self.admin_pw, auto_bind=True)
            conn.search(self.base_dn, f'(cn={username})', attributes=['cn'])
            
            if len(conn.entries) == 0:
                return False
                
            user_real_dn = conn.entries[0].entry_dn
            user_conn = Connection(server, user=user_real_dn, password=password, auto_bind=True)
            
            user_conn.unbind()
            conn.unbind()
            return True
            
        except LDAPException:
            return False
        except Exception:
            return False

# 📑 Dossier Técnico Completo: Sistema de Autenticación Centralizada (LDAP)

**Asignatura:** Computación en la Nube  
**Institución:** Universidad Católica Andrés Bello (UCAB)  
**Integrantes del Equipo:** 
* Alberto Monasterio  
* Jose Mondim  

---

## 1. 🚀 Guía de Operación y Despliegue Rápido

Siga estos pasos estrictos en la terminal del servidor Ubuntu (VirtualBox) para levantar, verificar y limpiar el entorno de ejecución.

### Arranque del Ecosistema
1. **Navegar al directorio del proyecto:**
   ```bash
   cd ~/proyecto-ldap
   ```

2. **Parada preventiva y limpieza de hilos de red:**
   ```bash
   sudo docker compose down
   ```

3. **Construcción e inicialización en segundo plano (Detached Mode):**
   ```bash
   sudo docker compose up --build -d
   ```

4. **Validación de contenedores activos:**
   ```bash
   sudo docker ps
   ```

### Verificación de Endpoints desde el Sistema Anfitrión (Windows)
* **Frontend Web Application:** [http://localhost](http://localhost) o [http://127.0.0.1](http://127.0.0.1)
* **Documentación Interactiva de la API:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
* **Panel de Administración phpLDAPadmin:** [http://localhost:8080](http://localhost:8080) *(Acceder obligatoriamente en modo incógnito)*

---

## 2. 🔌 Manual de Red y Reenvío de Puertos (VirtualBox)

Si la máquina virtual opera bajo el esquema de red **NAT**, es mandatorio configurar las siguientes reglas de *Port Forwarding* para permitir que las peticiones asíncronas del navegador en Windows crucen el hipervisor hacia la subred interna de Docker:

| Nombre de la Regla | Protocolo | IP Anfitrión | Puerto Anfitrión | IP Invitado | Puerto Invitado |
|--------------------|-----------|--------------|------------------|-------------|-----------------|
| Nginx Frontend     | TCP       | `127.0.0.1`  | `80`             | (Vacío)     | `80`            |
| FastAPI Auth-API   | TCP       | `127.0.0.1`  | `8000`           | (Vacío)     | `8000`          |
| phpLDAPadmin Web   | TCP       | `127.0.0.1`  | `8080`           | (Vacío)     | `80`            |
| OpenLDAP Core      | TCP       | `127.0.0.1`  | `389`            | (Vacío)     | `389`           |

---

## 3. 🗄️ Diseño del Directorio LDAP y Credenciales de Prueba

El árbol de información del directorio (DIT) se ha modelado bajo esquemas de seguridad corporativos estandarizados, estructurándose de la siguiente manera:

```text
dc=proyecto,dc=ucab (Nodo Raíz Base)
  └── ou=ingenieria (Unidad Organizativa / Carpeta Principal)
       ├── cn=usuarios (Grupo de Sistema POSIX - GID: 500)
       └── cn=amonasterio (Cuenta de Usuario - inetOrgPerson / posixAccount)
```

### Credenciales de Infraestructura
* **Administrador del LDAP (Root DN):** `cn=admin,dc=proyecto,dc=ucab`
* **Contraseña Administrativa:** `admin`

### Credenciales de Usuario para Validación (Frontend)
* **Nombre de Usuario (cn / uid):** `amonasterio`
* **Contraseña de Acceso:** `123456`
* **Propiedades POSIX del Usuario:**
  * **Login Shell:** `/bin/bash`
  * **Home Directory:** `/home/amonasterio`
  * **Primary GID Number:** `500` (Asociado al grupo `usuarios`)

---

## 4. 📝 Archivos Fuente de Configuración y Código

### A. Orquestador de Contenedores (`docker-compose.yml`)
Este manifiesto define la topología de la microarquitectura, el aislamiento de red y el mapeo de volúmenes físicos estables para evitar la volatilidad de los datos de usuario.

```yaml
version: '3.8'

services:
  openldap:
    image: osixia/openldap:latest
    container_name: openldap
    ports:
      - "389:389"
    environment:
      - LDAP_ORGANISATION=UCAB
      - LDAP_DOMAIN=proyecto.ucab
      - LDAP_ADMIN_PASSWORD=admin
    volumes:
      - ldap_data:/var/lib/ldap
      - ldap_config:/etc/ldap/slapd.d

  phpladpadmin:
    image: osixia/phpldapadmin:latest
    container_name: phpladpadmin
    ports:
      - "8080:80"
    environment:
      - PHPLDAPADMIN_LDAP_HOSTS=openldap
      - PHPLDAPADMIN_HTTPS=false
      - PHPLDAPADMIN_TRUST_PROXY_SSL=true
    depends_on:
      - openldap

  auth-api:
    build: ./auth-api
    container_name: microservicio_auth
    ports:
      - "8000:8000"
    depends_on:
      - openldap

  frontend:
    build: ./frontend
    container_name: web_frontend
    ports:
      - "80:80"
    depends_on:
      - auth-api

volumes:
  ldap_data:
  ldap_config:
```

### B. Adaptador de Autenticación Backend (`ldap_adapter.py`)
Módulo en Python integrado con la librería `ldap3` enfocado en realizar búsquedas estrictas sobre el atributo de Nombre Común (`cn`) y ejecutar operaciones de enlace activo (`bind`).

```python
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPException

class LDAPAuthAdapter:
    def __init__(self):
        self.server_uri = 'ldap://openldap:389'
        self.base_dn = 'dc=proyecto,dc=ucab'
        self.admin_dn = 'cn=admin,dc=proyecto,dc=ucab'
        self.admin_pw = 'admin'

    def authenticate_user(self, username: str, password: str) -> bool:
        try:
            server = Server(self.server_uri, get_info=ALL)
            conn = Connection(server, user=self.admin_dn, password=self.admin_pw, auto_bind=True)
            
            # Busqueda filtrada por el atributo de Nombre Comun (cn) para localizar el DN real
            conn.search(self.base_dn, f'(cn={username})', attributes=['cn'])

            if len(conn.entries) == 0:
                return False

            user_real_dn = conn.entries[0].entry_dn
            
            # Operacion de Bind directo empleando las credenciales crudas del cliente
            user_conn = Connection(server, user=user_real_dn, password=password, auto_bind=True)

            user_conn.unbind()
            conn.unbind()
            return True

        except LDAPException:
            return False
        except Exception:
            return False
```

---


## 5. 📊 Informe de Actividades Académicas (Formato de Lectura)

### Introducción
En el diseño de plataformas distribuidas y arquitecturas de microservicios, la gestión centralizada de identidades representa un principio fundamental para garantizar la seguridad y la gobernanza de datos. El presente proyecto documenta el desarrollo y despliegue automatizado de un ecosistema de autenticación centralizada basado en el protocolo industrial LDAP (Lightweight Directory Access Protocol), implementado mediante la herramienta OpenLDAP y expuesto a través de una API transaccional rápida en FastAPI. Todo el sistema se encuentra orquestado de manera modular mediante contenedores independientes, garantizando la consistencia del software.

### Problema que Resuelve
El almacenamiento descentralizado de credenciales en bases de datos aisladas introduce severos inconvenientes en entornos de nube:
1. **Redundancia Operativa:** La creación, modificación o baja de una identidad debe ejecutarse de forma manual en cada sistema de software independiente.
2. **Inseguridad Estructural:** Múltiples vectores de ataque debido a la disparidad de algoritmos de hash y lógicas de validación entre aplicaciones.
3. **Falta de Auditoría:** Imposibilidad de centralizar los logs de acceso de los operarios para detectar anomalías en tiempo real.

Al introducir una *Única Fuente de Verdad* (Single Source of Truth), el protocolo LDAP permite aislar las identidades. Las aplicaciones satélites no manipulan contraseñas de forma interna, sino que delegan la comprobación a este núcleo seguro.

### Mejoras Tecnológicas Realizadas
Durante las fases de integración del laboratorio, se aplicaron técnicas de robustecimiento de infraestructura:
* **Persistencia mediante Volúmenes de Docker:** Se enlazaron los directorios `/var/lib/ldap` y `/etc/ldap/slapd.d` del contenedor a volúmenes administrados del host de Ubuntu. Esto asegura que la base de datos sobreviva a comandos de destrucción y parada del servicio (`docker compose down`).
* **Sincronización del Flujo de Búsqueda:** Se corrigió el desacoplamiento entre el cliente web y el backend reemplazando las búsquedas del atributo `uid` por el atributo de Nombre Común (`cn`), logrando compatibilidad simétrica con las plantillas de cuentas de usuario POSIX generadas de manera gráfica.
* **Resolución de Red NAT:** Se integraron variables de entorno específicas (`PHPLDAPADMIN_TRUST_PROXY_SSL=true`) en la capa web para interceptar y validar de forma exitosa las cabeceras HTTP redirigidas por los mecanismos de port forwarding de la máquina virtual.

### Conclusiones
* La automatización de infraestructura mediante Docker Compose mitiga el problema clásico de variabilidad de entornos, permitiendo empaquetar bases de datos jerárquicas y middlewares de código de manera portable.
* La separación de responsabilidades a través de adaptadores de infraestructura (`ldap_adapter.py`) facilita la escalabilidad en la nube: cualquier microservicio futuro podrá consumir este motor de autenticación utilizando protocolos de comunicación livianos y estandarizados.

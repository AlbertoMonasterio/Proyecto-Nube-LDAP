# 🎓 Proyecto Nube - Autenticación Centralizada (OpenLDAP)

¡Bienvenido al repositorio del proyecto universitario de Autenticación Centralizada! Este proyecto implementa un directorio activo utilizando OpenLDAP, expone sus funcionalidades a través de una API RESTful construida con FastAPI, y presenta una interfaz gráfica moderna (Frontend) para la interacción de los usuarios.

---

## 🏗️ Arquitectura del Proyecto

El proyecto está dockerizado y consta de **4 microservicios** orquestados con Docker Compose:

1. **`openldap` (Puerto 389):** El motor principal de base de datos de directorio. Aquí residen todos los usuarios organizados por Unidades Organizativas (OUs).
2. **`phpldapadmin` (Puerto 8080):** Panel de administración visual web para gestionar el servidor LDAP.
3. **`auth-api` (Puerto 8000):** Un microservicio desarrollado en Python (FastAPI). Sirve de "puente" seguro entre el Frontend y la base de datos LDAP. Maneja el inicio de sesión, generación de tokens JWT, registro de nuevos usuarios y el listado del directorio.
4. **`frontend` (Puerto 80):** Interfaz web servida mediante Nginx. Está construida con HTML5, CSS3 (con estilo Glassmorphism) y JS Vanilla para proporcionar un diseño premium, dinámico y responsivo.

---

## 📂 Estructura de Archivos Principal

```text
Proyecto-Nube-LDAP/
│
├── auth-api/                 # Backend en Python (FastAPI)
│   ├── main.py               # Rutas de la API (Login, Registro, Listado)
│   ├── ldap_adapter.py       # Lógica de conexión y manipulación de OpenLDAP (ldap3)
│   ├── requirements.txt      # Dependencias de Python
│   └── Dockerfile            # Construcción de la imagen del backend
│
├── frontend/                 # Frontend Web
│   ├── index.html            # Estructura del portal (Login/Dashboard)
│   ├── styles.css            # Hoja de estilos (Modo oscuro, Glassmorphism, Colores UCAB)
│   ├── app.js                # Lógica de conexión con la API
│   └── Dockerfile            # Contenedor Nginx para servir la web
│
├── .env                      # Variables de Entorno (Credenciales seguras, Secret JWT)
├── docker-compose.yml        # Archivo maestro de orquestación de contenedores
├── estructura_completa.ldif  # Base de datos inicial a inyectar en LDAP (Facultades y Usuarios)
└── start.ps1                 # Script de automatización nativo para Windows
```

---

## 🚀 ¿Cómo ejecutar el proyecto (Windows)?

Se ha creado un script nativo en PowerShell que automatiza toda la limpieza, construcción, inyección de datos y despliegue del proyecto.

1. **Requisito indispensable:** Asegúrate de tener **Docker Desktop** instalado y ejecutándose en tu máquina.
2. Abre una terminal de **PowerShell**.
3. Navega a la carpeta raíz de este repositorio.
4. Ejecuta el script de inicio:
   ```powershell
   .\start.ps1
   ```

Este script se encargará de levantar todos los servicios y de forzar la inyección del archivo `estructura_completa.ldif` para asegurar que siempre haya datos de prueba disponibles.

---

## 🔑 Credenciales y Accesos

### 🌐 Portal de Usuarios (Frontend)
- **URL:** [http://localhost](http://localhost)
- **¿Qué puedes hacer?** Iniciar sesión, ver el directorio de usuarios de la universidad en el Dashboard, y registrar nuevas cuentas.
- **Usuarios de prueba pre-cargados:**
  - `amonasterio` (Clave: `123456`)
  - `prof_lopez` (Clave: `profepassword`)

### 🛠️ Portal del Administrador (phpLDAPadmin)
- **URL:** [http://localhost:8080](http://localhost:8080)
- **Login DN:** `cn=admin,dc=proyecto,dc=ucab`
- **Contraseña:** `admin_ucab_seguro`
- **¿Qué puedes hacer?** Control total. Auditar, borrar, modificar atributos directamente en el árbol LDAP y gestionar de forma profunda toda la estructura.

### 🔌 Documentación de la API (Swagger UI)
- **URL:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **¿Qué puedes hacer?** Ver todos los endpoints disponibles del backend (`/api/v1/auth/login`, `/api/v1/users`), sus formatos de Request/Response y probarlos manualmente.

---

## 📝 Notas para el Desarrollo Futuro

- **Variables de Entorno (`.env`):** Las contraseñas fuertes (como la clave maestra de LDAP o el secreto del JWT) ahora se manejan a través del archivo `.env`. Si necesitas modificar una credencial base, hazlo allí.
- **Frontend CSS:** El frontend no usa frameworks pesados como React ni librerías como Tailwind o Bootstrap. Todo el diseño "Premium" está escrito de cero en `frontend/styles.css`.
- **Datos Iniciales (`.ldif`):** Si necesitas que el sistema inicie con más usuarios o departamentos de prueba por defecto, simplemente agrégalos al archivo `estructura_completa.ldif`. El script `start.ps1` se encarga del resto.

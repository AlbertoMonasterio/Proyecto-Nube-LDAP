# UCAB Cloud LDAP Directory Project

## Overview
A cloud-native LDAP-based Identity Management system. It features a FastAPI backend, a Vanilla JS responsive frontend, and an OpenLDAP database containerized using Docker Compose.

## Key Features
- **LDAP Authentication**: Secure login against an OpenLDAP directory.
- **Role-Based Access Control (RBAC)**: Distinct privileges for Admins, Professors, and Students.
- **Enterprise Security**: 
  - `HttpOnly` cookies for JWT storage to prevent XSS.
  - SSHA Password hashing for secure storage.
  - Strict password policies (length, uppercase, digits).
- **Audit Logging**: Action traceability in `audit.log`.
- **Responsive UI**: Glassmorphism design, floating Toast notifications, and real-time search filtering.

## How to Run
1. Clone the repository.
2. Run `docker-compose up -d --build` (or your preferred start script).
3. Access the frontend at `http://localhost`.
4. Access the API at `http://localhost:8000/docs`.

## Test Credentials
The database comes pre-seeded with the following users for testing purposes:

| Role | Department/Faculty | Username | Password |
|---|---|---|---|
| **Admin** | RRHH | `jperez` | `adminpassword` |
| **Admin** | RRHH | `mgomez` | `clave123` |
| **Professor** | Ingenieria | `lsilva` | `profepassword` |
| **Professor** | Administracion | `arojas` | `clave123` |
| **Student** | Ingenieria | `cmendez` | `123456` |
| **Student** | Ingenieria | `etorres` | `clave123` |
| **Student** | Derecho | `pvargas` | `clave123` |
| **Student** | Medicina | `scastro` | `clave123` |

> **Note**: For security, all test passwords are SSHA-hashed within the LDAP initialization file. New passwords created via the UI are automatically hashed by the backend API.

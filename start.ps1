Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Iniciando Proyecto LDAP UCAB en Windows" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
docker info >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker no esta corriendo. Por favor inicia Docker Desktop y vuelve a intentar." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Docker esta corriendo." -ForegroundColor Cyan

# Remove old volumes to allow re-seeding LDIF data (since we modified it)
Write-Host "[INFO] Limpiando volumenes antiguos de LDAP para aplicar nueva estructura LDIF..." -ForegroundColor Yellow
docker-compose down -v

Write-Host "[INFO] Construyendo e iniciando contenedores en segundo plano..." -ForegroundColor Cyan
docker-compose up -d --build

Write-Host "[INFO] Esperando 10 segundos a que OpenLDAP inicie completamente..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "[INFO] Inyectando datos iniciales (Facultades y usuarios) en LDAP..." -ForegroundColor Cyan
docker exec openldap ldapadd -x -D "cn=admin,dc=proyecto,dc=ucab" -w admin_ucab_seguro -f /container/run/custom/estructura_completa.ldif -c

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Servicios Iniciados Exitosamente!" -ForegroundColor Green
Write-Host "  Frontend (Web):        http://localhost"
Write-Host "  Auth API (FastAPI):    http://localhost:8000/docs"
Write-Host "  phpLDAPadmin:          http://localhost:8080"
Write-Host "=============================================" -ForegroundColor Green
Write-Host "Nota: Puede tomar unos segundos para que LDAP aplique la base de datos." -ForegroundColor Yellow

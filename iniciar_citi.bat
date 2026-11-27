@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "DOCKER=docker"
where docker >nul 2>nul
if errorlevel 1 (
  if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
    set "DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
  ) else (
    echo [CITI] No se encontro Docker en el PATH.
    echo [CITI] Abre Docker Desktop y vuelve a ejecutar iniciar_citi.bat.
    pause
    exit /b 1
  )
)

echo [CITI] Construyendo la imagen y levantando los contenedores...
"%DOCKER%" compose up -d --build
if errorlevel 1 (
  echo [CITI] No fue posible levantar Docker.
  echo [CITI] Verifica que Docker Desktop este abierto y vuelve a intentar.
  pause
  exit /b 1
)

echo [CITI] Esperando a que Django responda en http://localhost:8000 ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$url='http://localhost:8000/cuenta/login/'; for ($i=0; $i -lt 60; $i++) { try { $r=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch { }; Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 (
  echo [CITI] El contenedor sigue arrancando. Revisa: docker compose logs -f web
  echo [CITI] Se abrira la URL de todos modos.
)

start "" "http://localhost:8000"
echo [CITI] Listo. Si el navegador no se abrio, visita http://localhost:8000
endlocal

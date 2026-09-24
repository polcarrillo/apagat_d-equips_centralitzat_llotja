@echo off
REM ============================================================
REM  PREPARAR WINDOWS 7 PARA CONTROL REMOTO + SINCRONIZACION DE HORA
REM  Ejecutar UNA VEZ en cada equipo Windows 7, como Administrador
REM  (clic derecho > "Ejecutar como administrador")
REM
REM  EDITA ESTA LINEA con el nombre o IP del PC que ejecuta la app:
set CONTROLADOR=192.168.1.10
REM ============================================================

net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Tienes que ejecutar este .bat como Administrador.
    pause
    exit /b 1
)

echo.
echo === 1/6  Servicios necesarios ===========================
REM Schedule  -> necesario para schtasks /s  (sincronizar hora)
REM RemoteRegistry -> necesario para shutdown /m  (apagar/reiniciar)
REM W32Time   -> servicio de hora; en Win7 viene en Manual y parado
sc config Schedule start= auto
sc config RemoteRegistry start= auto
sc config W32Time start= auto
net start Schedule
net start RemoteRegistry
net start W32Time

echo.
echo === 2/6  Firewall (valido tambien en red Publica) ========
REM profile=Any amplia el ambito de la regla a Dominio+Privada+Publica,
REM sin tocar la categoria de red del equipo. Los nombres de grupo
REM estan traducidos: se prueban ES y EN, los que no existan se ignoran.
netsh advfirewall firewall set rule group="Administracion remota de tareas programadas" new enable=Yes profile=Any
netsh advfirewall firewall set rule group="Administración remota de tareas programadas" new enable=Yes profile=Any
netsh advfirewall firewall set rule group="Remote Scheduled Tasks Management" new enable=Yes profile=Any
netsh advfirewall firewall set rule group="Compartir archivos e impresoras" new enable=Yes profile=Any
netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes profile=Any
netsh advfirewall firewall set rule group="Instrumental de administracion de Windows (WMI)" new enable=Yes profile=Any
netsh advfirewall firewall set rule group="Windows Management Instrumentation (WMI)" new enable=Yes profile=Any
netsh advfirewall firewall add rule name="NTP cliente UDP 123" dir=out action=allow protocol=UDP remoteport=123 profile=Any

echo.
echo === 3/6  UAC remoto (grupo de trabajo, sin dominio) =====
REM Sin esto, un admin local que entra por red pierde privilegios
REM y schtasks /s + ADMIN$ devuelven "Acceso denegado".
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f

echo.
echo === 4/6  Zona horaria ===================================
tzutil /s "Romance Standard Time"

echo.
echo === 5/6  Permitir correcciones GRANDES de hora ==========
REM Por defecto W32Time se niega a corregir desfases > 48h
REM y hace "resync" sin cambiar nada. Esta es una causa muy comun.
reg add "HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Config" /v MaxPosPhaseCorrection /t REG_DWORD /d 0xFFFFFFFF /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Config" /v MaxNegPhaseCorrection /t REG_DWORD /d 0xFFFFFFFF /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Config" /v AnnounceFlags /t REG_DWORD /d 10 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient" /v Enabled /t REG_DWORD /d 1 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient" /v SpecialPollInterval /t REG_DWORD /d 3600 /f

echo.
echo === 6/6  Apuntar al servidor de hora ====================
REM 0x8 = modo cliente NTP con intervalo propio
w32tm /config /manualpeerlist:"%CONTROLADOR%,0x8" /syncfromflags:manual /reliable:no /update
net stop w32time
net start w32time
w32tm /resync /rediscover

echo.
echo === COMPROBACION ========================================
w32tm /query /status
w32tm /query /source
echo.
echo Hora local actual:
time /t
date /t
echo.
echo Listo. Si "w32tm /query /source" muestra "Local CMOS Clock",
echo el equipo NO esta sincronizando: revisa que %CONTROLADOR%
echo responda por UDP 123.
echo.
echo IMPORTANTE: si el cambio de UAC remoto (paso 3) es la primera vez
echo que se aplica en este equipo, reinicialo para que tenga efecto.
pause
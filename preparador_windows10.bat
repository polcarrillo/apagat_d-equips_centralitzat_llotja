@echo off
REM ============================================================
REM  Convierte el PC Windows 10 que ejecuta la app en servidor
REM  de hora (NTP) de la red local. Ejecutar UNA VEZ como Admin.
REM ============================================================

net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Ejecuta este .bat como Administrador.
    pause
    exit /b 1
)

echo.
echo === 1/5  Firewall: compartir archivos (valido en red Publica) ====
REM Necesario para que los clientes puedan hacer "net time \\controlador".
REM profile=Any amplia el ambito de la regla a Dominio+Privada+Publica,
REM sin tocar la categoria de red del equipo.
netsh advfirewall firewall set rule group="Compartir archivos e impresoras" new enable=Yes profile=Any
netsh advfirewall firewall set rule group="File and Printer Sharing" new enable=Yes profile=Any

echo.
echo === 2/5  Que el controlador coja la hora de Internet =====
w32tm /config /manualpeerlist:"hora.roa.es,0x8 es.pool.ntp.org,0x8" /syncfromflags:manual /reliable:yes /update

echo.
echo === 3/5  Activar el rol de servidor NTP ==================
reg add "HKLM\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpServer" /v Enabled /t REG_DWORD /d 1 /f
REM AnnounceFlags 5 = "soy una fuente de tiempo fiable" (imprescindible sin dominio)
reg add "HKLM\SYSTEM\CurrentControlSet\Services\W32Time\Config" /v AnnounceFlags /t REG_DWORD /d 5 /f

echo.
echo === 4/5  Servicio en automatico y reiniciado =============
sc config W32Time start= auto
net stop w32time
net start w32time

echo.
echo === 5/5  Abrir el puerto NTP de entrada ==================
netsh advfirewall firewall add rule name="NTP servidor UDP 123" dir=in action=allow protocol=UDP localport=123 profile=Any

echo.
echo === COMPROBACION =========================================
w32tm /resync /rediscover
w32tm /query /status
echo.
echo Anota la IP de este equipo y ponla como CONTROLADOR en preparar_win7.bat:
ipconfig | findstr /i "IPv4"
pause
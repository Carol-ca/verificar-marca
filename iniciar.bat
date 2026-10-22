@echo off
echo ============================================
echo   VERIFICADOR DE MARCAS MARKETPLACE
echo   Iniciando sistema...
echo ============================================
echo.

REM Instalar dependencias
echo [1/2] Instalando dependencias...
pip install flask requests beautifulsoup4 lxml Pillow Werkzeug >nul 2>&1

echo [2/2] Iniciando servidor...
echo.
echo   Acesse: http://localhost:5000
echo.

python app.py
pause

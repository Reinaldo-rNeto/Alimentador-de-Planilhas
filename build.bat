@echo off
chcp 65001 >nul
echo === Alimentador de Planilha — Build ===
echo.

:: Instalar dependências se necessário
echo [1/3] Verificando dependências...
pip install pyinstaller customtkinter openpyxl google-auth-oauthlib google-api-python-client --quiet

echo.
echo [2/3] Gerando .exe com PyInstaller...
pyinstaller ^
  --name "AlimentadorPlanilha" ^
  --onefile ^
  --windowed ^
  --icon NONE ^
  --add-data "app;app" ^
  --add-data "credentials.json;." ^
  --hidden-import customtkinter ^
  --hidden-import openpyxl ^
  --hidden-import openpyxl.styles ^
  --hidden-import openpyxl.worksheet.datavalidation ^
  --hidden-import google.auth ^
  --hidden-import google.auth.transport.requests ^
  --hidden-import google.oauth2.credentials ^
  --hidden-import google_auth_oauthlib.flow ^
  --hidden-import googleapiclient.discovery ^
  --hidden-import googleapiclient.http ^
  run.py

echo.
echo [3/3] Concluído!
echo O executável está em:  dist\AlimentadorPlanilha.exe
echo.
echo ATENÇÃO: Coloque o credentials.json na mesma pasta do .exe para ativar o Drive.
pause

@echo off
echo === Installation de l'environnement Projet Voltaire assistant ===
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installé ou n'est pas dans le PATH
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Vérifier si pip est installé
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] pip n'est pas installé correctement
    echo Veuillez réinstaller Python en cochant l'option "Add pip to PATH"
    pause
    exit /b 1
)

REM Créer le fichier requirements.txt s'il n'existe pas
if not exist requirements.txt (
    echo flask==3.0.2 > requirements.txt
    echo g4f >> requirements.txt
    echo flask-cors==4.0.0 >> requirements.txt
    echo requests==2.32.3 >> requirements.txt
    echo SpeechRecognition==3.10.3 >> requirements.txt
    echo [INFO] Fichier requirements.txt créé
)

echo [INFO] Installation des dépendances...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation des dépendances
    pause
    exit /b 1
)

echo.
echo [SUCCÈS] Toutes les dépendances ont été installées
echo.
echo [INFO] Démarrage de l'application...
echo.

REM Démarrer l'application Flask
python -m flask --app main run

pause
exit /b 0
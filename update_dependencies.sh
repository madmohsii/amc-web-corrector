#!/bin/bash

echo "🔄 Mise à jour des dépendances AMC Web Corrector"
echo "=============================================="

# Vérifier que nous sommes dans l'environnement virtuel
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Environnement virtuel actif: $VIRTUAL_ENV"
else
    echo "⚠️  Activation de l'environnement virtuel..."
    source venv/bin/activate
fi

# Installer les nouvelles dépendances Python
echo "📦 Installation des nouvelles dépendances..."
pip install pandas

# Vérifier que LaTeX est installé pour AMC
echo "🔧 Vérification de LaTeX..."
if ! command -v pdflatex &> /dev/null; then
    echo "📚 Installation de LaTeX..."
    sudo apt install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended
fi

# Vérifier l'installation d'AMC
echo "🔍 Vérification d'AMC..."
if ! command -v auto-multiple-choice &> /dev/null; then
    echo "❌ AMC n'est pas installé. Installation..."
    sudo apt update
    sudo apt install -y auto-multiple-choice
else
    echo "✅ AMC est installé"
    auto-multiple-choice --version
fi

# Créer les nouveaux fichiers du projet
echo "📝 Création des nouveaux fichiers..."

# Créer amc_manager.py s'il n'existe pas
if [ ! -f "amc_manager.py" ]; then
    echo "Création de amc_manager.py..."
    # Le contenu sera copié depuis l'artifact
fi

# Créer sample_questions.py s'il n'existe pas
if [ ! -f "sample_questions.py" ]; then
    echo "Création de sample_questions.py..."
    # Le contenu sera copié depuis l'artifact
fi

# Créer le template configure_qcm.html s'il n'existe pas
if [ ! -f "templates/configure_qcm.html" ]; then
    echo "Création de templates/configure_qcm.html..."
    # Le contenu sera copié depuis l'artifact
fi

# Mettre à jour requirements.txt
echo "📋 Mise à jour de requirements.txt..."
cat > requirements.txt << 'EOF'
Flask==2.3.3
Werkzeug==2.3.7
Jinja2==3.1.2
MarkupSafe==2.1.3
itsdangerous==2.1.2
click==8.1.7
blinker==1.6.3
pandas==2.0.3
EOF

echo "✅ Mise à jour terminée!"
echo ""
echo "📝 Prochaines étapes:"
echo "1. Copiez le contenu des nouveaux fichiers depuis les artifacts"
echo "2. Redémarrez l'application: python app.py"
echo "3. Testez la nouvelle fonctionnalité de configuration QCM"

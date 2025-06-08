#!/bin/bash

echo "🚀 Installation d'AMC Web Corrector"
echo "=================================="

# Vérifier si on est sur Ubuntu/Debian
if ! command -v apt &> /dev/null; then
    echo "❌ Ce script est conçu pour Ubuntu/Debian"
    exit 1
fi

# Mise à jour du système
echo "📦 Mise à jour du système..."
sudo apt update

# Installation d'AMC
echo "🔧 Installation d'Auto Multiple Choice..."
sudo apt install -y auto-multiple-choice

# Vérification de l'installation AMC
if ! command -v auto-multiple-choice &> /dev/null; then
    echo "❌ Erreur: AMC n'a pas pu être installé"
    exit 1
fi

# Installation de Python et pip
echo "🐍 Installation de Python et pip..."
sudo apt install -y python3 python3-pip python3-venv

# Création de l'environnement virtuel
echo "🏗️  Création de l'environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances Python
echo "📚 Installation des dépendances Python..."
pip install -r requirements.txt

# Création de la structure de dossiers
echo "📁 Création de la structure de projet..."
mkdir -p templates uploads amc-projects results

# Permissions
echo "🔐 Configuration des permissions..."
chmod +x app.py
chmod 755 uploads amc-projects results

echo "✅ Installation terminée!"
echo ""
echo "Pour démarrer l'application:"
echo "1. source venv/bin/activate"
echo "2. python app.py"
echo ""
echo "L'application sera accessible sur http://localhost:5000"

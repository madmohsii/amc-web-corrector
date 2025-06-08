# 🎓 AMC Web Corrector

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Interface web moderne pour la correction automatique de QCM basée sur **Auto Multiple Choice (AMC)**.

![AMC Web Corrector Demo](https://via.placeholder.com/800x400/667eea/ffffff?text=AMC+Web+Corrector)

## ✨ Fonctionnalités

- 🏗️ **Gestion de projets** - Créez et organisez vos projets de correction
- 📤 **Upload intuitif** - Glissez-déposez vos copies scannées (PDF, images)
- ⚡ **Traitement automatique** - Correction AMC en un clic
- 📊 **Résultats détaillés** - Notes, statistiques et exports
- 🎨 **Interface moderne** - Design responsive et convivial
- 🔧 **Prêt à l'emploi** - Installation automatique incluse

## 🚀 Installation rapide

### Prérequis
- Ubuntu 18.04+ ou Debian 10+
- Python 3.6+
- Accès sudo

### Installation en une commande
```bash
git clone https://github.com/VOTRE-USERNAME/amc-web-corrector.git
cd amc-web-corrector
./setup.sh
```

### Démarrage
```bash
source venv/bin/activate
python app.py
```

Ouvrez votre navigateur sur **http://localhost:5000**

## 📋 Guide d'utilisation

### 1️⃣ Créer un projet
- Cliquez sur "Nouveau Projet"
- Donnez un nom à votre projet de QCM

### 2️⃣ Uploader les copies
- Glissez vos PDFs scannés dans la zone d'upload
- Formats supportés : PDF, PNG, JPG, JPEG

### 3️⃣ Lancer le traitement
- Cliquez sur "Lancer le traitement"
- AMC analyse automatiquement les réponses

### 4️⃣ Consulter les résultats
- Téléchargez les notes au format CSV/PDF
- Consultez les statistiques détaillées

## 🏗️ Architecture

```
amc-web-corrector/
├── 📄 app.py              # Application Flask principale
├── 📋 requirements.txt    # Dépendances Python
├── 🔧 setup.sh           # Script d'installation
├── 🌐 templates/         # Interface web
│   ├── base.html
│   ├── index.html
│   ├── create_project.html
│   ├── projects.html
│   ├── project_detail.html
│   └── results.html
├── 📁 uploads/           # Fichiers uploadés
├── 📂 amc-projects/      # Projets AMC
└── 📊 results/           # Résultats générés
```

## ⚙️ Configuration AMC

### Exemple de QCM LaTeX compatible
```latex
\documentclass[a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[francais,bloc]{automultiplechoice}

\begin{document}
\AMCrandomseed{1234567}

\begin{question}{q1}
  Quelle est la capitale de la France ?
  \begin{choices}
    \correctchoice{Paris}
    \wrongchoice{Londres}
    \wrongchoice{Berlin}
    \wrongchoice{Madrid}
  \end{choices}
\end{question}

\end{document}
```

## 🌐 Déploiement en production

### Sur VPS (OVH, DigitalOcean, etc.)
```bash
# Installation identique
git clone https://github.com/VOTRE-USERNAME/amc-web-corrector.git
cd amc-web-corrector
./setup.sh

# Configuration Nginx
sudo nano /etc/nginx/sites-available/amc-web
```

### Service systemd
```ini
[Unit]
Description=AMC Web Corrector
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/amc-web-corrector
Environment=PATH=/path/to/amc-web-corrector/venv/bin
ExecStart=/path/to/amc-web-corrector/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🔐 Sécurité

⚠️ **Important pour la production :**
- Changez la `secret_key` dans `app.py`
- Ajoutez l'authentification utilisateur
- Configurez HTTPS
- Limitez les tailles d'upload
- Validez les types de fichiers

## 🤝 Contribution

Les contributions sont les bienvenues ! 

1. Forkez le projet
2. Créez votre branche feature (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Poussez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 🐛 Problèmes courants

### AMC non trouvé
```bash
sudo apt update
sudo apt install auto-multiple-choice
```

### Erreur de permissions
```bash
chmod 755 uploads amc-projects results
```

### Port déjà utilisé
Modifiez le port dans `app.py` :
```python
app.run(debug=True, port=5001)
```

## 📚 Ressources

- [Documentation AMC](https://www.auto-multiple-choice.net/)
- [Guide LaTeX AMC](https://www.auto-multiple-choice.net/auto-multiple-choice.fr/AMC-doc.fr.pdf)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👨‍💻 Auteur

**Votre Nom** - [@votre-github](https://github.com/votre-username)

---

⭐ **N'oubliez pas de donner une étoile si ce projet vous aide !**

## 📈 Roadmap

- [ ] 🔐 Système d'authentification
- [ ] 📱 Interface mobile optimisée
- [ ] 🌍 Support multi-langues
- [ ] 📊 Statistiques avancées
- [ ] 🔌 API REST
- [ ] 📧 Notifications par email
- [ ] 🎨 Thèmes personnalisables

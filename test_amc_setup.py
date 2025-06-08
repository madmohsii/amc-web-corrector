#!/usr/bin/env python3
"""
Test script pour vérifier l'installation AMC et les nouvelles fonctionnalités
"""

import subprocess
import sys
import os
from pathlib import Path

def test_command(command, description):
    """Teste si une commande existe et fonctionne"""
    print(f"🔍 Test: {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - OK")
            return True
        else:
            print(f"❌ {description} - ERREUR")
            print(f"   Erreur: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False

def test_python_imports():
    """Teste les imports Python nécessaires"""
    print("\n📦 Test des imports Python:")
    
    imports_to_test = [
        ("flask", "Flask"),
        ("pandas", "Pandas"),
        ("pathlib", "Pathlib"),
        ("json", "JSON"),
        ("subprocess", "Subprocess")
    ]
    
    all_ok = True
    for module, description in imports_to_test:
        try:
            __import__(module)
            print(f"✅ {description}")
        except ImportError:
            print(f"❌ {description} - Module non trouvé")
            all_ok = False
    
    return all_ok

def test_amc_installation():
    """Teste l'installation AMC"""
    print("\n🔧 Test d'Auto Multiple Choice:")
    
    tests = [
        ("auto-multiple-choice --help", "AMC disponible"),
        ("pdflatex --version", "LaTeX disponible"),
        ("which auto-multiple-choice", "Chemin AMC")
    ]
    
    results = []
    for command, description in tests:
        results.append(test_command(command, description))
    
    return all(results)

def test_project_structure():
    """Teste la structure du projet"""
    print("\n📁 Test de la structure du projet:")
    
    required_files = [
        ("app.py", "Application Flask principale"),
        ("requirements.txt", "Dépendances Python"),
        ("templates/base.html", "Template de base"),
        ("templates/index.html", "Page d'accueil"),
        ("templates/configure_qcm.html", "Configuration QCM")
    ]
    
    optional_files = [
        ("amc_manager.py", "Gestionnaire AMC"),
        ("sample_questions.py", "Questions d'exemple"),
        ("uploads/", "Dossier uploads"),
        ("amc-projects/", "Dossier projets")
    ]
    
    all_required = True
    for file_path, description in required_files:
        if os.path.exists(file_path):
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - MANQUANT: {file_path}")
            all_required = False
    
    print("\n📝 Fichiers optionnels:")
    for file_path, description in optional_files:
        if os.path.exists(file_path):
            print(f"✅ {description}")
        else:
            print(f"⚠️  {description} - À créer: {file_path}")
    
    return all_required

def create_test_qcm():
    """Crée un QCM de test"""
    print("\n📝 Test de création QCM:")
    
    try:
        # Importer nos modules s'ils existent
        if os.path.exists('amc_manager.py') and os.path.exists('sample_questions.py'):
            sys.path.append('.')
            from amc_manager import AMCManager
            from sample_questions import SAMPLE_QUESTIONS
            
            # Créer un dossier de test
            test_dir = Path('test_project')
            test_dir.mkdir(exist_ok=True)
            
            # Tester le gestionnaire AMC
            amc = AMCManager(test_dir)
            latex_file = amc.create_latex_template(SAMPLE_QUESTIONS[:2])  # 2 questions de test
            
            if latex_file.exists():
                print("✅ Génération LaTeX réussie")
                print(f"   Fichier créé: {latex_file}")
                
                # Lire et afficher un extrait
                with open(latex_file, 'r') as f:
                    content = f.read()
                    print(f"   Taille: {len(content)} caractères")
                
                return True
            else:
                print("❌ Fichier LaTeX non créé")
                return False
        else:
            print("⚠️  Modules AMC non disponibles - à créer manuellement")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test QCM: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🧪 TEST AMC WEB CORRECTOR")
    print("=" * 50)
    
    tests_results = []
    
    # Tests des commandes système
    tests_results.append(test_amc_installation())
    
    # Tests des imports Python
    tests_results.append(test_python_imports())
    
    # Tests de structure
    tests_results.append(test_project_structure())
    
    # Test de création QCM
    tests_results.append(create_test_qcm())
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS")
    
    passed = sum(tests_results)
    total = len(tests_results)
    
    print(f"✅ Tests réussis: {passed}/{total}")
    
    if passed == total:
        print("🎉 Tous les tests sont passés! Le système est prêt.")
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        print("\n🔧 Actions recommandées:")
        if not test_command("auto-multiple-choice --help", ""):
            print("   - Installer AMC: sudo apt install auto-multiple-choice")
        if not os.path.exists('amc_manager.py'):
            print("   - Créer amc_manager.py depuis l'artifact")
        if not os.path.exists('sample_questions.py'):
            print("   - Créer sample_questions.py depuis l'artifact")

if __name__ == "__main__":
    main()

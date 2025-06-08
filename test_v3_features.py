#!/usr/bin/env python3
"""
Test des nouvelles fonctionnalités de la version 3.0
"""

import sys
import os
import requests
import json
from pathlib import Path

def test_dashboard_api():
    """Test des API du dashboard"""
    print("\n📊 Test des API Dashboard:")
    
    base_url = "http://localhost:5000"
    
    # Test de l'API des statistiques générales
    try:
        response = requests.get(f"{base_url}/api/stats/overview")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ API stats/overview - {stats.get('total_projects', 0)} projets")
        else:
            print(f"❌ API stats/overview - Erreur {response.status_code}")
    except requests.ConnectionError:
        print("❌ Impossible de se connecter - L'application est-elle démarrée?")
        return False
    except Exception as e:
        print(f"❌ Erreur API stats: {e}")
        return False
    
    return True

def test_file_structure():
    """Test de la structure des fichiers v3.0"""
    print("\n📁 Test de la structure v3.0:")
    
    required_files = [
        ("dashboard.py", "Gestionnaire dashboard"),
        ("templates/dashboard.html", "Template dashboard"),
        ("static/js/enhanced-upload.js", "Upload amélioré"),
        ("static/css/", "Dossier CSS"),
        ("static/images/", "Dossier images")
    ]
    
    all_ok = True
    for file_path, description in required_files:
        if os.path.exists(file_path):
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - MANQUANT: {file_path}")
            all_ok = False
    
    return all_ok

def test_imports():
    """Test des nouveaux imports"""
    print("\n📦 Test des imports v3.0:")
    
    imports_to_test = [
        ("pandas", "Pandas pour les données"),
        ("matplotlib", "Matplotlib pour les graphiques"),
        ("seaborn", "Seaborn pour les visualisations")
    ]
    
    all_ok = True
    for module, description in imports_to_test:
        try:
            __import__(module)
            print(f"✅ {description}")
        except ImportError:
            print(f"❌ {description} - Module non installé")
            all_ok = False
    
    return all_ok

def test_dashboard_functionality():
    """Test des fonctionnalités du dashboard"""
    print("\n🎯 Test des fonctionnalités dashboard:")
    
    # Vérifier que les modules nécessaires sont disponibles
    try:
        if os.path.exists('dashboard.py'):
            sys.path.append('.')
            from dashboard import get_global_statistics, get_recent_projects
            
            # Test des statistiques globales
            stats = get_global_statistics()
            print(f"✅ Statistiques globales: {stats.get('total_projects', 0)} projets")
            
            # Test des projets récents
            recent = get_recent_projects()
            print(f"✅ Projets récents: {len(recent)} projets")
            
            return True
        else:
            print("⚠️  dashboard.py non trouvé - à créer")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test dashboard: {e}")
        return False

def create_sample_data():
    """Crée des données d'exemple pour tester le dashboard"""
    print("\n🔧 Création de données d'exemple:")
    
    try:
        # Créer un projet de test s'il n'existe pas
        test_project_path = Path("amc-projects/test_dashboard_project")
        test_project_path.mkdir(parents=True, exist_ok=True)
        
        # Créer les métadonnées du projet
        project_info = {
            "name": "Projet Test Dashboard",
            "id": "test_dashboard",
            "created": "2025-06-08T10:00:00"
        }
        
        with open(test_project_path / "project_info.json", "w") as f:
            json.dump(project_info, f, indent=2)
        
        # Créer des données de résultats factices
        exports_path = test_project_path / "exports"
        exports_path.mkdir(exist_ok=True)
        
        # CSV de notes fictif
        csv_content = """Nom,Prénom,Note,Note Max
Dupont,Jean,15.5,20
Martin,Claire,18.0,20
Bernard,Paul,12.0,20
Durand,Marie,16.5,20
Moreau,Pierre,14.0,20
"""
        
        with open(exports_path / "notes.csv", "w") as f:
            f.write(csv_content)
        
        print("✅ Données d'exemple créées")
        return True
        
    except Exception as e:
        print(f"❌ Erreur création données: {e}")
        return False

def generate_test_report():
    """Génère un rapport de test"""
    print("\n" + "="*60)
    print("📋 RAPPORT DE TEST v3.0")
    print("="*60)
    
    tests = [
        ("Structure des fichiers", test_file_structure),
        ("Imports Python", test_imports),
        ("Fonctionnalités dashboard", test_dashboard_functionality),
        ("API Dashboard", test_dashboard_api),
        ("Données d'exemple", create_sample_data)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            results.append((test_name, False))
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Toutes les fonctionnalités v3.0 sont prêtes!")
        print("\n🚀 Actions recommandées:")
        print("   1. Démarrez l'application: python app.py")
        print("   2. Visitez http://localhost:5000/dashboard")
        print("   3. Testez l'upload amélioré")
        print("   4. Explorez les statistiques")
    else:
        print(f"\n⚠️  {total - passed} tests ont échoué")
        print("\n🔧 Actions recommandées:")
        print("   1. Vérifiez les fichiers manquants")
        print("   2. Installez les dépendances: pip install pandas matplotlib seaborn")
        print("   3. Créez les fichiers depuis les artifacts")
        print("   4. Relancez les tests")

def main():
    """Fonction principale"""
    print("🧪 TEST AMC WEB CORRECTOR v3.0")
    print("Interface avancée et dashboard")
    
    generate_test_report()

if __name__ == "__main__":
    main()

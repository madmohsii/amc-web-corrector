#!/usr/bin/env python3
"""
Script de test et optimisation pour la correction automatique AMC
Utilisation: python correction_tester.py [options]
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from amc_manager import AMCManager
from sample_questions import SAMPLE_QUESTIONS

class CorrectionTester:
    """Classe pour tester et optimiser la correction automatique"""
    
    def __init__(self, test_projects_dir="test_projects"):
        self.test_dir = Path(test_projects_dir)
        self.test_dir.mkdir(exist_ok=True)
        self.results = []
    
    def create_test_project(self, project_name, num_questions=10, num_students=30):
        """Crée un projet de test avec questionnaire et fausses données"""
        project_path = self.test_dir / project_name
        project_path.mkdir(exist_ok=True)
        
        amc = AMCManager(project_path)
        
        # Créer un questionnaire de test
        test_questions = self.generate_test_questions(num_questions)
        latex_file = amc.create_latex_template(
            test_questions,
            title=f"Test {project_name}",
            subject="Test automatique",
            duration="60 minutes"
        )
        
        # Créer une liste d'étudiants fictifs
        students_data = self.generate_test_students(num_students)
        amc.create_student_list_csv(students_data)
        
        # Préparer le projet
        prep_result = amc.prepare_project()
        
        return {
            'project_path': project_path,
            'amc': amc,
            'preparation_success': prep_result['success'],
            'students_count': num_students,
            'questions_count': num_questions
        }
    
    def generate_test_questions(self, num_questions):
        """Génère des questions de test"""
        questions = []
        
        for i in range(num_questions):
            if i < len(SAMPLE_QUESTIONS):
                # Utiliser les questions d'exemple
                q = SAMPLE_QUESTIONS[i].copy()
                q['id'] = f'q{i+1}'
                questions.append(q)
            else:
                # Générer des questions basiques
                questions.append({
                    'id': f'q{i+1}',
                    'text': f'Question de test numéro {i+1}. Quelle est la bonne réponse ?',
                    'choices': [
                        {'text': 'Réponse A', 'correct': i % 4 == 0},
                        {'text': 'Réponse B', 'correct': i % 4 == 1},
                        {'text': 'Réponse C', 'correct': i % 4 == 2},
                        {'text': 'Réponse D', 'correct': i % 4 == 3}
                    ],
                    'comment': f'Question de test {i+1}'
                })
        
        return questions
    
    def generate_test_students(self, num_students):
        """Génère une liste d'étudiants fictifs"""
        students = []
        
        first_names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry']
        last_names = ['Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard', 'Petit', 'Durand']
        
        for i in range(num_students):
            students.append({
                'id': str(i+1).zfill(3),
                'nom': last_names[i % len(last_names)],
                'prenom': first_names[i % len(first_names)],
                'code': str(i+1).zfill(3)
            })
        
        return students
    
    def simulate_scanned_papers(self, project_path, num_papers=None, simulate_errors=False):
        """Simule des copies scannées (pour test sans vrais scans)"""
        uploads_path = project_path / 'uploads'
        uploads_path.mkdir(exist_ok=True)
        
        # Créer des fichiers factices pour simuler les scans
        if num_papers is None:
            num_papers = 20
        
        for i in range(num_papers):
            fake_scan = uploads_path / f'copie_{i+1:03d}.pdf'
            
            # Créer un fichier PDF minimal (juste pour les tests)
            with open(fake_scan, 'wb') as f:
                # En-tête PDF minimal
                f.write(b'%PDF-1.4\n')
                f.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
                f.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
                f.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n')
                f.write(b'xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n179\n%%EOF\n')
        
        return num_papers
    
    def test_correction_performance(self, num_questions_list=[5, 10, 20], 
                                  num_students_list=[10, 30, 50],
                                  scoring_strategies=['french_standard', 'adaptive']):
        """Teste les performances de correction avec différents paramètres"""
        
        print("=== Test de Performance de Correction ===\n")
        
        for num_questions in num_questions_list:
            for num_students in num_students_list:
                for strategy in scoring_strategies:
                    
                    test_name = f"Q{num_questions}_S{num_students}_{strategy}"
                    print(f"Test: {test_name}")
                    
                    start_time = time.time()
                    
                    try:
                        # Créer le projet de test
                        project_data = self.create_test_project(
                            f"test_{test_name}",
                            num_questions,
                            num_students
                        )
                        
                        if not project_data['preparation_success']:
                            print(f"  ❌ Échec préparation")
                            continue
                        
                        # Simuler les scans
                        num_scans = self.simulate_scanned_papers(
                            project_data['project_path'],
                            num_students
                        )
                        
                        # Tester la correction (simulation sans vrais scans)
                        amc = project_data['amc']
                        
                        # Créer des données de test dans data/ pour simuler l'analyse
                        self.create_mock_analysis_data(amc, num_students, num_questions)
                        
                        # Tester la notation
                        scoring_start = time.time()
                        scoring_result = amc.smart_scoring(strategy)
                        scoring_time = time.time() - scoring_start
                        
                        total_time = time.time() - start_time
                        
                        # Enregistrer les résultats
                        test_result = {
                            'test_name': test_name,
                            'num_questions': num_questions,
                            'num_students': num_students,
                            'scoring_strategy': strategy,
                            'total_time': total_time,
                            'scoring_time': scoring_time,
                            'success': scoring_result['success'],
                            'preparation_time': start_time,
                            'avg_time_per_student': total_time / num_students if num_students > 0 else 0
                        }
                        
                        self.results.append(test_result)
                        
                        print(f"  ✅ Succès - {total_time:.2f}s ({total_time/num_students:.2f}s/étudiant)")
                        
                    except Exception as e:
                        print(f"  ❌ Erreur: {e}")
                        
                        self.results.append({
                            'test_name': test_name,
                            'num_questions': num_questions,
                            'num_students': num_students,
                            'scoring_strategy': strategy,
                            'success': False,
                            'error': str(e)
                        })
                    
                    print()
        
        return self.results
    
    def create_mock_analysis_data(self, amc, num_students, num_questions):
        """Crée des données d'analyse fictives pour tester la notation"""
        
        # Créer le fichier scoring.xml minimal
        scoring_xml = amc.data_path / 'scoring.xml'
        scoring_xml.parent.mkdir(parents=True, exist_ok=True)
        
        with open(scoring_xml, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<project>\n')
            f.write('  <questions>\n')
            
            for i in range(num_questions):
                f.write(f'    <question id="q{i+1}" scoring="b=1,m=-0.5,p=-0.5"/>\n')
            
            f.write('  </questions>\n')
            f.write('</project>\n')
        
        # Créer des fichiers de résultats fictifs dans cr/
        amc.cr_path.mkdir(parents=True, exist_ok=True)
        
        for student_id in range(1, num_students + 1):
            result_file = amc.cr_path / f'student_{student_id:03d}.xml'
            
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<student>\n')
                f.write(f'  <id>{student_id:03d}</id>\n')
                
                # Simuler des réponses aléatoirement correctes/incorrectes
                import random
                for q in range(num_questions):
                    correct = random.choice([True, False])
                    f.write(f'    <question id="q{q+1}" correct="{str(correct).lower()}"/>\n')
                
                f.write('</student>\n')
    
    def analyze_results(self):
        """Analyse les résultats des tests"""
        if not self.results:
            print("Aucun résultat à analyser")
            return
        
        print("=== Analyse des Résultats ===\n")
        
        successful_tests = [r for r in self.results if r.get('success', False)]
        failed_tests = [r for r in self.results if not r.get('success', False)]
        
        print(f"Tests réussis: {len(successful_tests)}/{len(self.results)}")
        print(f"Taux de réussite: {len(successful_tests)/len(self.results)*100:.1f}%\n")
        
        if successful_tests:
            # Analyse des temps
            avg_total_time = sum(r['total_time'] for r in successful_tests) / len(successful_tests)
            avg_time_per_student = sum(r['avg_time_per_student'] for r in successful_tests) / len(successful_tests)
            
            print(f"Temps moyen total: {avg_total_time:.2f}s")
            print(f"Temps moyen par étudiant: {avg_time_per_student:.2f}s")
            
            # Meilleure stratégie
            strategy_performance = {}
            for result in successful_tests:
                strategy = result['scoring_strategy']
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = []
                strategy_performance[strategy].append(result['avg_time_per_student'])
            
            print("\nPerformance par stratégie:")
            for strategy, times in strategy_performance.items():
                avg_time = sum(times) / len(times)
                print(f"  {strategy}: {avg_time:.2f}s/étudiant")
        
        if failed_tests:
            print(f"\nÉchecs ({len(failed_tests)}):")
            for failure in failed_tests:
                print(f"  {failure['test_name']}: {failure.get('error', 'Erreur inconnue')}")
    
    def save_results(self, filename="correction_test_results.json"):
        """Sauvegarde les résultats dans un fichier JSON"""
        results_data = {
            'timestamp': time.time(),
            'total_tests': len(self.results),
            'successful_tests': len([r for r in self.results if r.get('success', False)]),
            'results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nRésultats sauvegardés dans: {filename}")
    
    def cleanup_test_projects(self):
        """Nettoie les projets de test"""
        import shutil
        
        if self.test_dir.exists():
            try:
                shutil.rmtree(self.test_dir)
                print(f"Projets de test nettoyés: {self.test_dir}")
            except Exception as e:
                print(f"Erreur nettoyage: {e}")

def main():
    parser = argparse.ArgumentParser(description='Tester la correction automatique AMC')
    parser.add_argument('--quick', action='store_true', help='Test rapide avec moins de variations')
    parser.add_argument('--cleanup', action='store_true', help='Nettoyer les projets de test')
    parser.add_argument('--output', default='correction_test_results.json', help='Fichier de sortie')
    
    args = parser.parse_args()
    
    tester = CorrectionTester()
    
    if args.cleanup:
        tester.cleanup_test_projects()
        return
    
    try:
        if args.quick:
            # Test rapide avec moins de variations
            print("Mode test rapide activé")
            results = tester.test_correction_performance(
                num_questions_list=[5, 10],
                num_students_list=[10, 20],
                scoring_strategies=['french_standard', 'adaptive']
            )
        else:
            # Test complet
            print("Mode test complet activé")
            results = tester.test_correction_performance()
        
        # Analyser et sauvegarder
        tester.analyze_results()
        tester.save_results(args.output)
        
    except KeyboardInterrupt:
        print("\nTest interrompu par l'utilisateur")
    except Exception as e:
        print(f"Erreur pendant les tests: {e}")
    finally:
        if input("\nSupprimer les projets de test? (y/N): ").lower() == 'y':
            tester.cleanup_test_projects()

if __name__ == "__main__":
    main()

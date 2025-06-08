import os
import subprocess
import json
import shutil
from pathlib import Path
import logging

class AMCManager:
    """Gestionnaire pour les opérations Auto Multiple Choice"""
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.data_path = self.project_path / 'data'
        self.cr_path = self.project_path / 'cr'
        self.exports_path = self.project_path / 'exports'
        self.uploads_path = self.project_path / 'uploads'
        
        # Créer les dossiers nécessaires
        for path in [self.data_path, self.cr_path, self.exports_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Configuration du logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def run_command(self, command, check=True):
        """Exécute une commande AMC et retourne le résultat"""
        try:
            self.logger.info(f"Exécution: {command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.project_path,
                check=check
            )
            
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'command': command
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur commande: {e}")
            return {
                'success': False,
                'stdout': e.stdout,
                'stderr': e.stderr,
                'returncode': e.returncode,
                'command': command,
                'error': str(e)
            }
        except Exception as e:
            self.logger.error(f"Erreur inattendue: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': command
            }
    
    def create_latex_template(self, questions_data):
        """Crée un fichier LaTeX AMC à partir de données structurées"""
        latex_content = self._generate_latex_header()
        
        for i, question in enumerate(questions_data, 1):
            latex_content += self._generate_question_latex(i, question)
        
        latex_content += self._generate_latex_footer()
        
        # Sauvegarder le fichier
        latex_file = self.project_path / 'questionnaire.tex'
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        return latex_file
    
    def _generate_latex_header(self):
        """Génère l'en-tête LaTeX AMC"""
        return """\\documentclass[a4paper]{article}
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage[francais,bloc]{automultiplechoice}
\\usepackage{multicol}

% Configuration AMC
\\geometry{hmargin=2cm,headheight=2cm}
\\AMCrandomseed{1234567}
\\AMCboxDimensions{shape=oval}

\\begin{document}

% En-tête du questionnaire
\\noindent{\\bf QCM} \\hfill \\champnom{\\fbox{%
    \\begin{minipage}{.5\\linewidth}
      Nom et prénom:\\\\[.5cm]\\dotfill\\\\[.5cm]\\dotfill
    \\end{minipage}%
  }}

\\begin{center}\\em
Instructions: Noircissez complètement les cases correspondant aux bonnes réponses.
\\end{center}

\\champnom{\\fbox{%
  \\begin{minipage}{4cm}
    \\vspace*{.5cm}\\dotfill\\\\
    \\vspace*{.5cm}\\dotfill\\\\
    \\vspace*{1mm}
  \\end{minipage}%
}}

\\AMCcleardoublepage

% Questions
\\begin{multicols}{2}

"""
    
    def _generate_question_latex(self, num, question):
        """Génère le LaTeX pour une question"""
        latex = f"""
\\begin{{question}}{{q{num}}}
  {question['text']}
  \\begin{{choices}}
"""
        
        for choice in question['choices']:
            if choice.get('correct', False):
                latex += f"    \\correctchoice{{{choice['text']}}}\n"
            else:
                latex += f"    \\wrongchoice{{{choice['text']}}}\n"
        
        latex += "  \\end{choices}\n\\end{question}\n"
        return latex
    
    def _generate_latex_footer(self):
        """Génère le pied de page LaTeX"""
        return """
\\end{multicols}
\\end{document}
"""
    
    def prepare_project(self, latex_file=None):
        """Prépare le projet AMC (compilation LaTeX)"""
        if latex_file is None:
            latex_file = self.project_path / 'questionnaire.tex'
        
        if not latex_file.exists():
            return {
                'success': False,
                'error': f'Fichier LaTeX non trouvé: {latex_file}'
            }
        
        # Préparer les sujets
        cmd = f"auto-multiple-choice prepare --with xelatex --filter latex --latex-stdout --data {self.data_path} {latex_file}"
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info("Préparation AMC réussie")
        
        return result
    
    def analyse_papers(self, threshold=0.5):
        """Analyse les copies scannées"""
        # Vérifier qu'il y a des fichiers à analyser
        scan_files = list(self.uploads_path.glob('*.pdf')) + list(self.uploads_path.glob('*.jpg')) + list(self.uploads_path.glob('*.png'))
        
        if not scan_files:
            return {
                'success': False,
                'error': 'Aucun fichier scanné trouvé'
            }
        
        # Commande d'analyse
        cmd = f"auto-multiple-choice analyse --data {self.data_path} --cr {self.cr_path} --auto-capture --threshold {threshold}"
        
        # Ajouter les fichiers scannés
        for scan_file in scan_files:
            cmd += f" {scan_file}"
        
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info(f"Analyse de {len(scan_files)} fichiers terminée")
        
        return result
    
    def calculate_marks(self, scoring_strategy='default'):
        """Calcule les notes"""
        # Définir la stratégie de notation
        if scoring_strategy == 'default':
            scoring_params = "--bareme default"
        elif scoring_strategy == 'negative':
            scoring_params = "--bareme '(b=1,m=0,v=-1)'"
        else:
            scoring_params = "--bareme default"
        
        cmd = f"auto-multiple-choice note --data {self.data_path} {scoring_params}"
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info("Calcul des notes terminé")
        
        return result
    
    def export_results(self, format_type='csv'):
        """Exporte les résultats"""
        results = []
        
        if format_type in ['csv', 'all']:
            # Export CSV
            csv_file = self.exports_path / 'notes.csv'
            cmd = f"auto-multiple-choice export --data {self.data_path} --module CSV --fich-noms '' --o {csv_file}"
            result = self.run_command(cmd)
            results.append(('CSV', result, csv_file))
        
        if format_type in ['ods', 'all']:
            # Export OpenDocument
            ods_file = self.exports_path / 'notes.ods'
            cmd = f"auto-multiple-choice export --data {self.data_path} --module ODS --fich-noms '' --o {ods_file}"
            result = self.run_command(cmd)
            results.append(('ODS', result, ods_file))
        
        return results
    
    def generate_annotated_papers(self):
        """Génère les copies annotées"""
        annotated_dir = self.exports_path / 'annotated'
        annotated_dir.mkdir(exist_ok=True)
        
        cmd = f"auto-multiple-choice annote --data {self.data_path} --cr {self.cr_path} --fich-noms '' --projet {annotated_dir}"
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info("Copies annotées générées")
        
        return result
    
    def get_statistics(self):
        """Récupère les statistiques du projet"""
        try:
            # Lire les données de la base AMC (si disponible)
            stats = {
                'total_papers': 0,
                'average_score': 0,
                'min_score': 0,
                'max_score': 0,
                'questions_stats': []
            }
            
            # Essayer de lire le fichier CSV des notes
            csv_file = self.exports_path / 'notes.csv'
            if csv_file.exists():
                import pandas as pd
                df = pd.read_csv(csv_file)
                
                if not df.empty and 'Note' in df.columns:
                    stats['total_papers'] = len(df)
                    stats['average_score'] = float(df['Note'].mean())
                    stats['min_score'] = float(df['Note'].min())
                    stats['max_score'] = float(df['Note'].max())
            
            return stats
        except Exception as e:
            self.logger.error(f"Erreur calcul statistiques: {e}")
            return {}
    
    def full_process(self, questions_data=None, scoring_strategy='default'):
        """Processus complet de A à Z"""
        results = []
        
        # 1. Créer le LaTeX si questions fournies
        if questions_data:
            try:
                latex_file = self.create_latex_template(questions_data)
                results.append(('Template LaTeX créé', {'success': True}, latex_file))
            except Exception as e:
                return [('Erreur création template', {'success': False, 'error': str(e)})]
        
        # 2. Préparer le projet
        result = self.prepare_project()
        results.append(('Préparation AMC', result))
        if not result['success']:
            return results
        
        # 3. Analyser les copies
        result = self.analyse_papers()
        results.append(('Analyse des copies', result))
        if not result['success']:
            return results
        
        # 4. Calculer les notes
        result = self.calculate_marks(scoring_strategy)
        results.append(('Calcul des notes', result))
        if not result['success']:
            return results
        
        # 5. Exporter les résultats
        export_results = self.export_results('all')
        for export_type, result, file_path in export_results:
            results.append((f'Export {export_type}', result))
        
        # 6. Générer les copies annotées
        result = self.generate_annotated_papers()
        results.append(('Copies annotées', result))
        
        return results

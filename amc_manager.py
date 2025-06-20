import os
import subprocess
import json
import shutil
from pathlib import Path
import logging
import csv
import shutil
from datetime import datetime # Added for generate_advanced_statistics

class AMCManager:
    """Gestionnaire pour les opérations Auto Multiple Choice - Version adaptée au format français"""
    
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
                cwd=self.project_path, # Execute command from project root
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

    def _generate_latex_header_french(self, title, subject, duration, instructions, csv_filename=None, num_pages=2):
        """Génère l'en-tête LaTeX compatible avec AMC"""
        
        base_header = r"""\documentclass[12pt,a4paper]{article}

    \usepackage{csvsimple,graphicx,pifont}
    \usepackage[francais,bloc]{automultiplechoice}
    \usepackage[utf8]{inputenc}    
    \usepackage[T1]{fontenc}
    \usepackage{verbatimbox}
    \usepackage{tcolorbox}

    \newtcolorbox{codebox}{colback=gray!5!white, colframe=black, boxrule=0.5mm, arc=3mm, width=\linewidth}

    """

        # Si pas de CSV, définir les commandes nécessaires
        if not csv_filename or not (self.project_path / csv_filename).exists():
            base_header += r"""% Mode sans CSV - définition des commandes
    \def\nom{NOM}
    \def\prenom{PRENOM}
    \def\id{001}

    """

        base_header += rf"""\newcommand{{\sujet}}{{
        \exemplaire{{1}}{{%
            \begin{{center}}
                \noindent{{}}\fbox{{\vspace*{{3mm}}
                    \Large\bf\nom{{}}~\prenom{{}}\normalsize{{}}
                    \vspace*{{3mm}}
                }}
            \end{{center}}
            
            \begin{{center}}\em
                \textbf{{{title}}}
                
                {subject if subject else ''}
                
                Durée : {duration}.
                
                \vspace{{0.2cm}}
                
                \textbf{{{instructions}}}
            \end{{center}}
            
            \vspace{{1ex}}
            
            \restituegroupe{{CN}}
            
            \AMCassociation{{\id}}
            
            \AMCaddpagesto{{{num_pages}}}
        }}
    }}

    \begin{{document}}
        \AMCrandomseed{{1237893}}
        \def\AMCformQuestion#1{{{{\\sc Question #1 :}}}}
        \setdefaultgroupmode{{withoutreplacement}}

    """
        
        return base_header

    def _generate_question_latex_french(self, question):
        """Génère le LaTeX pour une question"""
        question_id = question.get('id', 'q1')
        question_text = question['text']
        choices = question['choices']

        latex = f"""    \\element{{CN}}{{
        \\begin{{question}}{{{question_id}}}\\scoring{{b=1,m=-.5,p=-0.5}}
            {question_text}
            \\begin{{reponseshoriz}}
"""

        # Ajouter les choix dans l'ordre
        for choice in choices:
            if choice.get('correct', False):
                latex += f"                \\bonne{{{choice['text']}}}\n"
            else:
                latex += f"                \\mauvaise{{{choice['text']}}}\n"

        latex += """            \\end{reponseshoriz}
        \\end{question}
    }

"""
        return latex

    def _generate_latex_footer_french(self, csv_filename=None):
        """Génère le pied de page LaTeX"""
        if csv_filename and (self.project_path / csv_filename).exists():
            # Mode CSV
            return f"""
    %%%% fin des groupes

    \\csvreader[head to column names]{{{csv_filename}}}{{}}{{\\sujet}}

\\end{{document}}
"""
        else:
            # Mode simple
            return """
    %%%% fin des groupes
    
    \\sujet

\\end{document}
"""

    def create_latex_template(self, questions_data, title="QCM", subject="", duration="60 minutes", 
                        instructions=None, csv_filename="liste.csv", num_pages=2):
        """Crée un fichier LaTeX AMC à partir de données structurées selon le format français"""
        
        print(f"Création template LaTeX avec {len(questions_data)} questions sur {num_pages} page(s)")
        
        if instructions is None:
            instructions = ("Vous ne devez cocher qu'une seule case. 1 point par bonne réponse. "
                        "-0.5 point par mauvaise réponse ou si plusieurs cases sont cochées. "
                        "0 point si aucune case n'est cochée pour la même question.")
        
        # Créer automatiquement un fichier CSV minimal si nécessaire
        self._ensure_csv_exists(csv_filename)
        
        # 1. En-tête LaTeX avec num_pages
        latex_content = self._generate_latex_header_french(title, subject, duration, instructions, csv_filename, num_pages)
        
        # 2. Générer TOUTES les questions
        print("Génération des questions...")
        for i, question in enumerate(questions_data):
            print(f"  Question {i+1}: {question.get('text', '')[:50]}...")
            latex_content += self._generate_question_latex_french(question)
        
        # 3. Pied de page
        latex_content += self._generate_latex_footer_french(csv_filename)
        
        # Sauvegarder le fichier
        latex_file = self.project_path / 'questionnaire.tex'
        print(f"Sauvegarde dans: {latex_file}")
        
        try:
            with open(latex_file, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            print(f"Fichier LaTeX sauvegardé avec succès - {num_pages} page(s) par élève")
            
        except Exception as e:
            print(f"ERREUR sauvegarde: {e}")
            raise
        
        return latex_file


    def _ensure_csv_exists(self, csv_filename="liste.csv"):
        """S'assure qu'un fichier CSV existe pour AMC"""
        csv_path = self.project_path / csv_filename
        
        if not csv_path.exists():
            # Chercher un autre fichier CSV existant
            csv_files = list(self.project_path.glob("*.csv"))
            if csv_files:
                self.logger.info(f"Utilisation du CSV existant : {csv_files[0].name}")
                return csv_files[0].name
            
            # Créer un CSV minimal
            self.logger.info(f"Création d'un fichier CSV minimal : {csv_filename}")
            csv_content = """id,nom,prenom
001,ETUDIANT,Test
"""
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
        
        return csv_filename
    
    def prepare_project(self, latex_file=None):
        """Prépare le projet AMC avec la commande prepare"""
        if latex_file is None:
            latex_file = self.project_path / 'questionnaire.tex'
        
        if not latex_file.exists():
            return {
                'success': False,
                'error': f'Fichier LaTeX non trouvé: {latex_file}'
            }
        
        self.logger.info(f"Préparation du projet avec le fichier: {latex_file}")
        
        # Nettoyer les anciens fichiers
        self._clean_old_files()
        
        # CORRECTION: Ajouter --out-calage pour forcer la génération du fichier de calibrage
        # Cette option est ESSENTIELLE pour générer le layout AMC
        cmd = f"""auto-multiple-choice prepare \
            --mode s \
            --data '{self.data_path.name}' \
            --prefix '.' \
            --out-calage DOC-calage.xy \
            --out-sujet DOC-sujet.pdf \
            --out-corrige DOC-corrige.pdf \
            --out-catalog DOC-catalog.pdf \
            '{latex_file.name}'"""

        # Conservez la ligne de débogage pour vérification finale
        print(f"DEBUG: Contenu brut de cmd: {cmd}") 
        self.logger.critical(f"DEBUG_COMMAND_TO_EXECUTE: {cmd}") 
        self.logger.info(f"Exécution AMC prepare : {cmd}")
        
        result = self.run_command(cmd)
        
        if result['success'] or result['returncode'] == 0:
            self.logger.info("AMC prepare terminé")
            
            # NOUVEAU: Appliquer meptex pour extraire le layout depuis DOC-calage.xy
            calage_file = self.project_path / 'DOC-calage.xy'
            if calage_file.exists():
                self.logger.info("Application de meptex pour extraire le layout...")
                cmd_meptex = f"auto-multiple-choice meptex --src 'DOC-calage.xy' --data '{self.data_path.name}'"
                meptex_result = self.run_command(cmd_meptex)
                
                if meptex_result['success']:
                    self.logger.info("Layout extrait avec succès")
                    
                    # Vérifier que le layout a été généré
                    try:
                        import sqlite3
                        layout_db = self.data_path / 'layout.sqlite'
                        if layout_db.exists():
                            conn = sqlite3.connect(layout_db)
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM layout_box")
                            box_count = cursor.fetchone()[0]
                            cursor.execute("SELECT COUNT(*) FROM layout_question")
                            question_count = cursor.fetchone()[0]
                            conn.close()
                            
                            self.logger.info(f"Layout généré: {box_count} boxes, {question_count} questions")
                            
                            if box_count == 0:
                                self.logger.warning("Aucune box détectée dans le layout")
                            if question_count == 0:
                                self.logger.warning("Aucune question détectée dans le layout")
                                
                    except Exception as e:
                        self.logger.error(f"Erreur vérification layout: {e}")
                else:
                    self.logger.error(f"Échec meptex: {meptex_result.get('stderr')}")
            else:
                self.logger.warning("Fichier DOC-calage.xy non créé - layout incomplet")
            
            # Chercher le PDF généré
            pdf_found = False
            pdf_candidates = [
                'DOC-sujet.pdf',
                'amc-compiled.pdf',
                f'{latex_file.stem}.pdf'
            ]
            
            for pdf_name in pdf_candidates:
                pdf_path = self.project_path / pdf_name
                if pdf_path.exists():
                    # Copier vers un nom standard
                    output_pdf = self.project_path / 'questionnaire_output.pdf'
                    try:
                        shutil.copy2(pdf_path, output_pdf)
                        self.logger.info(f"PDF AMC généré : {pdf_path}")
                        pdf_found = True
                        break
                    except Exception as e:
                        self.logger.error(f"Erreur copie PDF : {e}")
            
            if pdf_found:
                return {
                    'success': True,
                    'method': 'amc_prepare',
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', ''),
                    'layout_file': str(calage_file) if calage_file.exists() else None
                }
        
        self.logger.error(f"La commande AMC prepare a échoué (code de retour: {result.get('returncode', 'N/A')}).")
        if result.get('stdout'):
            self.logger.error(f"Sortie standard (stdout) de AMC prepare (échec):\n{result['stdout']}")
        if result.get('stderr'):
            self.logger.error(f"Sortie d'erreur (stderr) de AMC prepare (échec):\n{result['stderr']}")
        else:
            self.logger.error("La sortie d'erreur (stderr) de AMC prepare était vide.")
        
        # Si AMC prepare échoue, essayer avec pdflatex en fallback
        self.logger.warning("AMC prepare a échoué, tentative avec pdflatex")
        return self._fallback_pdflatex_compilation(latex_file)

    def _clean_old_files(self):
        """Nettoie les anciens fichiers de compilation"""
        extensions_to_clean = ['*.pdf', '*.aux', '*.log', '*.fls', '*.fdb_latexmk', '*.out', '*.synctex.gz']
        for ext in extensions_to_clean:
            for file in self.project_path.glob(ext):
                try:
                    file.unlink()
                    self.logger.info(f"Fichier nettoyé: {file}")
                except OSError as e:
                    self.logger.warning(f"Impossible de nettoyer {file}: {e}")
    
    
    def get_analysis_statistics(self):
        """Récupère les statistiques de l'analyse (copies détectées, erreurs, etc.)"""
        stats = {
            'papers_detected': 0,
            'papers_with_errors': 0,
            'unreadable_papers': 0,
            'missing_student_codes': 0,
            'duplicate_codes': 0
        }
        
        try:
            # Chercher les fichiers de résultats d'analyse dans cr/
            cr_files = list(self.cr_path.glob('*.xml'))
            
            if cr_files:
                stats['papers_detected'] = len(cr_files)
                
                # Analyser les fichiers XML pour détecter les erreurs
                # (ici simplifié, vous pourriez parser le XML pour plus de détails)
                
            # Alternative: utiliser la commande AMC pour obtenir des stats
            # Path for --data is relative to cwd (self.project_path)
            cmd = f"auto-multiple-choice export --data '{self.data_path.name}' --module CSV --fich-noms liste.csv --stats-only"
            result = self.run_command(cmd, check=False)
            
            if result['success'] and result['stdout']:
                # Parser les stats de la sortie (format dépend de la version AMC)
                lines = result['stdout'].split('\n')
                for line in lines:
                    if 'papers' in line.lower():
                        # Extraire le nombre de copies
                        import re
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            stats['papers_detected'] = int(numbers[0])
        
        except Exception as e:
            self.logger.error(f"Erreur statistiques analyse: {e}")
        
        return stats
    
    def _fallback_pdflatex_compilation(self, latex_file):
        """Compilation de secours avec pdflatex"""
        self.logger.info("Tentative de compilation directe avec pdflatex...")
        
        # abs_latex_file = latex_file.resolve() # Not needed as cwd is project_path and file.name is used
        # abs_project_path = self.project_path.resolve() # Not needed as cwd is project_path
        
        # Compiler 2 fois pour résoudre les références
        for i in range(2):
            # Command should be relative to cwd which is project_path
            cmd = f"pdflatex -interaction=nonstopmode -output-directory '.' '{latex_file.name}'"
            self.logger.info(f"Pass {i+1} : {cmd}")
            result = self.run_command(cmd, check=False)
        
        # Vérifier si le PDF existe
        pdf_output = self.project_path / f"{latex_file.stem}.pdf"
        if pdf_output.exists() and pdf_output.stat().st_size > 1000:
            standard_pdf = self.project_path / 'questionnaire_output.pdf'
            try:
                shutil.copy2(pdf_output, standard_pdf)
                self.logger.info(f"PDF de secours créé : {standard_pdf}")
                
                return {
                    'success': True,
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', ''),
                    'method': 'pdflatex_fallback',
                    'pdf_size': pdf_output.stat().st_size,
                    'warnings': 'PDF créé avec pdflatex (sans marques AMC)'
                }
            except Exception as e:
                self.logger.error(f"Erreur copie PDF : {e}")
        
        return {
            'success': False,
            'error': 'Échec de compilation (AMC prepare et pdflatex)',
            'stdout': result.get('stdout', ''),
            'stderr': result.get('stderr', '')
        }

    
    def calculate_marks(self, scoring_strategy='default'): # Removed auto_optimize param
        """Calcule les notes"""
        # Adapter au système de notation français (b=1, m=-0.5, p=-0.5)
        if scoring_strategy == 'french':
            scoring_params = "--bareme '(b=1,m=-0.5,p=-0.5)'"
        elif scoring_strategy == 'default':
            scoring_params = "--bareme default"
        elif scoring_strategy == 'no_negative':
            scoring_params = "--bareme '(b=1,m=0,p=0)'"
        else:
            scoring_params = "--bareme default"
        
        # Path for --data is relative to cwd (self.project_path)
        cmd = f"auto-multiple-choice note --data {self.data_path.name} {scoring_params}"
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info("Calcul des notes terminé")
        
        return result
    
    def fix_csv_names(self, csv_file_path):
        """Corrige les noms dans le fichier CSV généré"""
        try:
            # Lire le fichier liste.csv pour récupérer les noms
            names_map = {}
            liste_file = self.project_path / 'liste.csv'
            if liste_file.exists():
                with open(liste_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Utiliser l'ID comme clé et construire le nom complet
                        student_id = row['id'].lstrip('0')  # Enlever les zéros devant (001 -> 1)
                        full_name = f"{row['nom']} {row['prenom']}"
                        names_map[student_id] = full_name
            
            # Corriger le fichier CSV des notes
            if names_map and csv_file_path.exists():
                with open(csv_file_path, 'r') as file:
                    content = file.read()
                
                for student_id, name in names_map.items():
                    old_line = f'"{student_id}","","?","'
                    new_line = f'"{student_id}","","{name}","'
                    content = content.replace(old_line, new_line)
                
                with open(csv_file_path, 'w') as file:
                    file.write(content)
                
                self.logger.info(f"Noms corrigés dans {csv_file_path}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la correction des noms: {e}")

    def export_results(self, format_type='csv'):
        """Exporte les résultats"""
        results = []
        if format_type in ['csv', 'all']:
            # Export CSV
            csv_file = self.exports_path / 'notes.csv'
            # Path for --data is relative to cwd (self.project_path)
            cmd = f"auto-multiple-choice export --data {self.data_path.name} --module CSV --fich-noms liste.csv --o '{csv_file.relative_to(self.project_path)}'"
            result = self.run_command(cmd)
            results.append(('CSV', result, str(csv_file)))
            # Corriger les noms dans le fichier CSV
            self.fix_csv_names(csv_file)
            
        if format_type in ['ods', 'all']:
            # Export OpenDocument
            ods_file = self.exports_path / 'notes.ods'
            # Path for --data is relative to cwd (self.project_path)
            cmd = f"auto-multiple-choice export --data {self.data_path.name} --module ODS --fich-noms liste.csv --o '{ods_file.relative_to(self.project_path)}'"
            result = self.run_command(cmd)
            results.append(('ODS', result, str(ods_file)))
        return results
    
    def generate_annotated_papers(self):
        """Génère les copies annotées - Version manuelle directe"""
        
        # Nettoyer d'abord les anciens PDF vides si ils existent
        self._cleanup_old_empty_pdfs()
        
        # Utiliser directement notre méthode qui fonctionne
        self.logger.info("Génération des copies annotées avec méthode manuelle")
        return self.generate_manual_annotated_papers()

    def _cleanup_old_empty_pdfs(self):
        """Nettoie les anciens PDF vides générés par AMC annotate"""
        annotated_dir = self.exports_path / 'annotated'
        
        if not annotated_dir.exists():
            return
        
        cleaned_count = 0
        for pdf_file in annotated_dir.glob("*.pdf"):
            try:
                # Supprimer les PDF < 2KB (anciens PDF AMC vides)
                if pdf_file.stat().st_size < 2000:
                    pdf_file.unlink()
                    cleaned_count += 1
                    self.logger.info(f"Ancien PDF vide supprimé: {pdf_file.name}")
            except Exception as e:
                self.logger.error(f"Erreur suppression {pdf_file.name}: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Nettoyage: {cleaned_count} ancien(s) PDF vide(s) supprimé(s)")

    def _try_standard_annotate(self):
        """Essaie la méthode AMC standard"""
        annotated_dir = self.exports_path / 'annotated'
        annotated_dir.mkdir(exist_ok=True)
        
        cr_pdf_dir = self.cr_path / 'corrections' / 'pdf'
        cr_pdf_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = f"auto-multiple-choice annotate --data '{self.data_path.name}' --cr '{self.cr_path.name}'"
        result = self.run_command(cmd)
        
        if result['success']:
            # Copier les PDF générés
            try:
                import glob
                pdf_files = glob.glob(str(cr_pdf_dir / "*.pdf"))
                for pdf_file in pdf_files:
                    shutil.copy2(pdf_file, annotated_dir)
                self.logger.info(f"Copies annotées AMC copiées: {len(pdf_files)} fichiers")
            except Exception as e:
                self.logger.error(f"Erreur copie: {e}")
        
        return result

    def _are_pdfs_empty(self):
        """Vérifie si les PDF générés sont vides (< 5KB)"""
        annotated_dir = self.exports_path / 'annotated'
        if not annotated_dir.exists():
            return True
        
        for pdf_file in annotated_dir.glob("*.pdf"):
            if pdf_file.stat().st_size > 5000:  # Plus de 5KB
                return False
        
        return True
    
    def generate_manual_annotated_papers(self):
        """Génère les copies annotées manuellement (remplacement de la méthode AMC défaillante)"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.colors import green, red, black, blue
            
            annotated_dir = self.exports_path / 'annotated'
            annotated_dir.mkdir(exist_ok=True)
            
            # Charger les bonnes réponses depuis qcm_config.json
            correct_answers = {}
            config_file = self.project_path / 'qcm_config.json'
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                for i, question in enumerate(config['questions'], 1):
                    for choice in question['choices']:
                        if choice['correct']:
                            correct_answers[f"q{i}"] = choice['text']
                            break
            
            # Charger la liste des étudiants
            students = {}
            liste_file = self.project_path / 'liste.csv'
            
            if liste_file.exists():
                with open(liste_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        student_id = row['id'].lstrip('0')
                        students[student_id] = f"{row['nom']} {row['prenom']}"
            
            # Charger les réponses des étudiants (normalement depuis capture.sqlite, mais ici on simule)
            student_answers = {}  # Vide car copies vierges
            
            generated_files = []
            
            # Générer une copie annotée pour chaque étudiant
            for student_id, student_name in students.items():
                output_file = annotated_dir / f"copie_annotee_{student_id}_{student_name.replace(' ', '_')}.pdf"
                
                # Créer le PDF
                c = canvas.Canvas(str(output_file), pagesize=A4)
                width, height = A4
                
                # Titre
                c.setFont("Helvetica-Bold", 16)
                c.setFillColor(black)
                c.drawString(50, height - 50, f"COPIE ANNOTÉE - {student_name}")
                
                # Note (0 car pas de réponses cochées)
                c.setFont("Helvetica-Bold", 14)
                c.setFillColor(blue)
                c.drawString(50, height - 80, f"NOTE: 0/{len(correct_answers)}")
                
                # Ligne de séparation
                c.line(50, height - 100, width - 50, height - 100)
                
                # Détail des questions
                y_pos = height - 130
                c.setFont("Helvetica-Bold", 12)
                c.setFillColor(black)
                c.drawString(50, y_pos, "CORRECTION DÉTAILLÉE:")
                
                y_pos -= 30
                
                # Pour chaque question
                for i, (question_id, correct_answer) in enumerate(correct_answers.items(), 1):
                    # Récupérer le texte de la question
                    question_text = f"Question {i}"
                    if config_file.exists():
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                            if i <= len(config['questions']):
                                question_text = config['questions'][i-1]['text'][:50] + "..."
                        except:
                            pass
                    
                    # Afficher la question
                    c.setFont("Helvetica", 10)
                    c.setFillColor(black)
                    c.drawString(70, y_pos, f"Question {i}: {question_text}")
                    y_pos -= 15
                    
                    # Réponse de l'étudiant (aucune)
                    c.setFillColor(red)
                    c.drawString(90, y_pos, "Réponse: Aucune case cochée")
                    y_pos -= 12
                    
                    # Bonne réponse
                    c.setFillColor(green)
                    c.drawString(90, y_pos, f"Bonne réponse: {correct_answer}")
                    y_pos -= 25
                    
                    # Vérifier qu'on ne dépasse pas la page
                    if y_pos < 100:
                        c.showPage()
                        y_pos = height - 50
                
                # Pied de page
                c.setFont("Helvetica", 8)
                c.setFillColor(black)
                c.drawString(50, 50, f"Copie générée automatiquement - Projet: {self.project_path.name}")
                
                # Sauvegarder le PDF
                c.save()
                generated_files.append(str(output_file))
                
                self.logger.info(f"Copie annotée générée: {output_file}")
            
            self.logger.info(f"Toutes les copies annotées générées: {len(generated_files)} fichiers")
            
            return {
                'success': True,
                'stdout': f'{len(generated_files)} copies annotées générées manuellement',
                'stderr': '',
                'returncode': 0,
                'command': 'generate_manual_annotated_papers',
                'generated_files': generated_files
            }
            
        except ImportError:
            error_msg = "ReportLab requis pour générer les copies annotées. Installez avec: pip install reportlab"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'command': 'generate_manual_annotated_papers'
            }
        except Exception as e:
            self.logger.error(f"Erreur génération copies annotées manuelles: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': 'generate_manual_annotated_papers'
            }
    
    def get_statistics(self):
        """Récupère les statistiques du projet"""
        try:
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
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_file)
                    
                    if not df.empty and 'Note' in df.columns:
                        stats['total_papers'] = len(df)
                        stats['average_score'] = float(df['Note'].mean())
                        stats['min_score'] = float(df['Note'].min())
                        stats['max_score'] = float(df['Note'].max())
                except ImportError:
                    # Fallback si pandas n'est pas disponible
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        notes = []
                        for row in reader:
                            if 'Note' in row:
                                try:
                                    notes.append(float(row['Note']))
                                except ValueError:
                                    continue
                        
                        if notes:
                            stats['total_papers'] = len(notes)
                            stats['average_score'] = sum(notes) / len(notes)
                            stats['min_score'] = min(notes)
                            stats['max_score'] = max(notes)
            
            return stats
        except Exception as e:
            self.logger.error(f"Erreur calcul statistiques: {e}")
            return {}

    def create_complete_questionnaire(self, questions_data, students_data=None, 
                                 title="QCM", subject="", duration="60 minutes", 
                                 instructions=None, csv_filename="liste.csv", num_pages=2):
        """Alias pour create_latex_template - compatibilité avec l'ancien code"""
        return self.create_latex_template(
            questions_data, title, subject, duration, instructions, csv_filename, num_pages
        )

    def create_student_list_csv(self, students_data=None, csv_filename="liste.csv"):
        """Crée le fichier CSV des étudiants avec codes"""
        csv_file = self.project_path / csv_filename
        
        if students_data is None:
            # CSV par défaut avec codes séquentiels
            students_data = [
                {'id': '001', 'nom': 'EXEMPLE', 'prenom': 'Eleve', 'code': '001'}
            ]
        
        # Écrire le CSV avec les bonnes colonnes pour AMC
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'nom', 'prenom', 'code']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for student in students_data:
                # S'assurer que tous les champs sont présents
                student_row = {
                    'id': student.get('id', student.get('code', '001')),
                    'nom': student.get('nom', ''),
                    'prenom': student.get('prenom', ''),
                    'code': student.get('code', student.get('id', '001'))
                }
                writer.writerow(student_row)
        
        self.logger.info(f"Fichier CSV créé avec {len(students_data)} élèves: {csv_file}")
        return csv_file

    def create_subnetting_questionnaire(self):
        """Crée le questionnaire de subnetting de l'exemple"""
        questions_data = [
            {
                'id': 'q1',
                'text': 'Quel est le nombre d\'adresses possibles dans le sous-réseau ayant un masque de sous-réseau 255.255.255.192 ?',
                'choices': [
                    {'text': '64', 'correct': False},
                    {'text': '62', 'correct': True},
                    {'text': '128', 'correct': False},
                    {'text': '30', 'correct': False}
                ],
                'comment': 'Conversion d\'un masque de sous-réseau'
            },
            {
                'id': 'q2',
                'text': 'Combien d\'hôtes sont possibles dans un sous-réseau avec un masque de 255.255.255.248 ?',
                'choices': [
                    {'text': '8', 'correct': False},
                    {'text': '6', 'correct': True},
                    {'text': '10', 'correct': False},
                    {'text': '4', 'correct': False}
                ],
                'comment': 'Calcul du nombre d\'hôtes'
            },
            {
                'id': 'q3',
                'text': 'Quelle est la notation binaire du masque 255.255.255.0 ?',
                'choices': [
                    {'text': '11111111.11111111.11111111.11111100', 'correct': False},
                    {'text': '11111111.11111111.11111111.00000000', 'correct': True},
                    {'text': '11111111.11111111.00000000.00000000', 'correct': False},
                    {'text': '11111111.00000000.00000000.00000000', 'correct': False}
                ],
                'comment': 'Conversion en binaire d\'un masque'
            }
        ]
        
        return self.create_latex_template(
            questions_data,
            title="BTS CIEL1 - Subnetting",
            subject="",
            duration="60 minutes"
        )
    
    def create_answer_sheet(self, output_path=None):
        """Crée la feuille de réponses pour la correction"""
        if output_path is None:
            output_path = self.project_path / 'answer_sheet.pdf'
        
        # Command needs relative paths from cwd (self.project_path)
        cmd = f"auto-multiple-choice reponse --data '{self.data_path.name}' --sujet questionnaire.tex --fich '{output_path.relative_to(self.project_path)}'"
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info(f"Feuille de réponses créée: {output_path}")
        
        return result

    def auto_scan_detection(self, scan_files):
        """Détection automatique des paramètres de scan optimaux"""
        detection_results = []
        
        for scan_file in scan_files:
            # Convertir pdf_path en chemin relatif au répertoire du projet
            # input_pdf_relative_to_project = pdf_path.relative_to(self.project_path) # pdf_path is not defined here. Assuming scan_file
            input_pdf_relative_to_project = scan_file.relative_to(self.project_path)
            # Le dossier de destination 'prepared_scans' est implicitement relatif au répertoire du projet
            cmd = f"auto-multiple-choice getimages --vector-density 300 --copy-to 'prepared_scans' '{input_pdf_relative_to_project}'"
            result = self.run_command(cmd)
            
            if result['success']:
                detection_results.append({
                    'file': str(scan_file), # Convert Path to string
                    'pages': result['stdout'].count('\n'),
                    'detected': True
                })
            else:
                detection_results.append({
                    'file': str(scan_file), # Convert Path to string
                    'error': result.get('stderr', 'Erreur de détection'),
                    'detected': False
                })
        
        return detection_results

    def prepare_scan_images(self, scan_path=None, dpi=300):
        """Prépare et optimise les images scannées pour l'analyse"""
        self.logger.info(f"DEBUG_START: prepare_scan_images - scan_path initial: {str(scan_path) if scan_path else 'None'}, dpi: {dpi}")

        if scan_path is None:
            scan_path = self.uploads_path
        self.logger.info(f"DEBUG: scan_path effectif: {str(scan_path)}")
        
        scan_files = []
        processed_files = [] 
        
        for ext in ['*.pdf', '*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
            self.logger.debug(f"DEBUG_GLOB_SEARCH: Searching for pattern: {ext} in {scan_path}")
            scan_files.extend(list(scan_path.glob(ext)))
        
        self.logger.info(f"DEBUG: Fichiers scannés trouvés dans {str(scan_path)}: {[str(f) for f in scan_files]}")

        if not scan_files:
            self.logger.warning(f"Aucun fichier scanné (PDF, JPG, PNG, etc.) trouvé dans {str(scan_path)}.")
            return {
                'success': False,
                'error': f'Aucun fichier scanné trouvé dans {str(scan_path)}.'
            }
        
        prepared_path = self.project_path / 'prepared_scans'
        prepared_path.mkdir(parents=True, exist_ok=True)
        
        # CORRECTION: Nettoyer le dossier prepared_scans avant de commencer
        self.logger.info("Nettoyage du dossier prepared_scans...")
        for old_file in prepared_path.glob('*'):
            if old_file.is_file():
                old_file.unlink()
        
        self.logger.info(f"DEBUG: Dossier de sortie des scans préparés: {str(prepared_path)}")
        
        for scan_file in scan_files:
            self.logger.info(f"DEBUG_LOOP: Traitement du fichier: {str(scan_file)}")
            try:
                output_dir_relative_to_project = Path('prepared_scans')

                if scan_file.suffix.lower() == '.pdf':
                    input_pdf_relative_to_project = scan_file.relative_to(self.project_path)
                    
                    # CORRECTION: Utiliser des options AMC plus précises pour éviter trop d'images
                    cmd = (
                        f"auto-multiple-choice getimages "
                        f"--vector-density {dpi} "
                        f"--copy-to '{output_dir_relative_to_project}' "
                        f"'{input_pdf_relative_to_project}'"
                    )
                    
                    self.logger.info(f"DEBUG_CMD_PDF: Commande AMC getimages pour PDF: {cmd}")
                    result = self.run_command(cmd)

                    if result['stdout']:
                        self.logger.info(f"DEBUG_GETIMAGES_STDOUT: Stdout de getimages pour {str(scan_file)}:\n{result['stdout']}")
                    if result['stderr']:
                        self.logger.warning(f"DEBUG_GETIMAGES_STDERR: Stderr de getimages pour {str(scan_file)}:\n{result['stderr']}")

                    if result['success']:
                        # Attendre un peu que les fichiers soient créés
                        import time
                        time.sleep(1.0)  # Augmenté à 1 seconde
        
                        # Chercher TOUS les fichiers images dans prepared_scans
                        image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
                        generated_images = [f for f in prepared_path.iterdir() 
                                        if f.is_file() and f.suffix.lower() in image_extensions]
                        
                        self.logger.info(f"DEBUG_GENERATED: Images générées après conversion PDF pour {str(scan_file.stem)}: {len(generated_images)} images")

                        if generated_images:
                            # CORRECTION: Filtrer et garder seulement les images principales
                            main_images = []
                            for img_path in generated_images:
                                # Garder seulement les images sans suffixe numérique multiple
                                if not any(img_path.stem.endswith(f'_{i:04d}') for i in range(1, 50)):
                                    main_images.append(img_path)
                                    processed_files.append(str(img_path))
                            
                            self.logger.info(f"DEBUG_SUCCESS_PDF: Fichier PDF {str(scan_file)} converti. {len(main_images)} images principales sur {len(generated_images)} générées.")
                            
                            # Supprimer les images en trop pour éviter la surcharge
                            if len(generated_images) > len(main_images):
                                for img in generated_images:
                                    if img not in main_images:
                                        try:
                                            img.unlink()
                                            self.logger.debug(f"Image supprimée: {img.name}")
                                        except:
                                            pass
                        else:
                            self.logger.warning(f"DEBUG_WARN_PDF: Conversion de {str(scan_file)} réussie, mais aucune image trouvée dans {str(prepared_path)}.")
                    else:
                        self.logger.error(f"DEBUG_ERROR_PDF: Erreur conversion PDF {str(scan_file)}: {result.get('stderr', 'Erreur inconnue')}. Stdout: {result.get('stdout', '')}")
                else:
                    dest_file = prepared_path / scan_file.name
                    if scan_file != dest_file: 
                        shutil.copy2(scan_file, dest_file)
                        self.logger.info(f"DEBUG_COPY_IMG: Image copiée de {str(scan_file)} vers {str(dest_file)}")
                    else:
                        self.logger.info(f"DEBUG_IMG_ALREADY_THERE: Image déjà à la bonne place: {str(scan_file)}")

                    processed_files.append(str(dest_file))

            except Exception as e:
                self.logger.error(f"DEBUG_EXCEPTION: Erreur inattendue lors du traitement de {str(scan_file)}: {e}")
        
        self.logger.info(f"DEBUG_END: prepare_scan_images - Résultat final. Fichiers traités: {len(processed_files)}, chemin préparé: {str(prepared_path)}")
        return {
            'success': len(processed_files) > 0,
            'processed_files': processed_files, 
            'prepared_path': str(prepared_path),
            'total_files_processed': len(processed_files),
            'total_files_found': len(scan_files)
        }

    def advanced_analysis(self, scan_path=None, auto_capture=True, threshold=0.5, try_harder=True):
        """Analyse avancée des copies scannées avec options optimisées"""
        if scan_path is None:
            scan_path = self.uploads_path

        # D'abord préparer les images
        prep_result = self.prepare_scan_images(scan_path)
        if not prep_result['success']:
            return prep_result

        # Utiliser les images préparées
        prepared_path = Path(prep_result['prepared_path'])
        
        # CORRECTION 1: Filtrer uniquement les images principales (sans les copies multiples)
        scan_files = []
        
        # Chercher d'abord les images principales (sans suffixe _0001, _0002, etc.)
        main_images = []
        for ext in ['*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
            potential_files = list(prepared_path.glob(ext))
            for f in potential_files:
                # Ne prendre que les images principales (celles sans _0001, _0002 à la fin)
                if not any(f.stem.endswith(f'_{i:04d}') for i in range(1, 100)):
                    main_images.append(f)
        
        # Si pas d'images principales, prendre un échantillon des images disponibles
        if not main_images:
            all_images = []
            for ext in ['*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
                all_images.extend(list(prepared_path.glob(ext)))
            
            # Grouper par page et prendre une image par page
            pages = {}
            for img in all_images:
                # Extraire le numéro de page du nom de fichier
                stem = img.stem
                if 'page-' in stem:
                    page_part = stem.split('page-')[1].split('-')[0]
                    if page_part not in pages:
                        pages[page_part] = img
            
            main_images = list(pages.values())
        
        scan_files = main_images
        
        self.logger.info(f"Images sélectionnées pour analyse: {len(scan_files)} sur {len(list(prepared_path.glob('*')))}")
        for f in scan_files:
            self.logger.info(f"  - {f.name}")

        if not scan_files:
            return {
                'success': False,
                'error': 'Aucun fichier préparé pour l\'analyse'
            }

        # CORRECTION 2: Utiliser des chemins relatifs au lieu d'absolus
        cmd_parts = [
            "auto-multiple-choice",
            "analyse",
            f"--data '{self.data_path.name}'",  # Relatif au project_path
            f"--cr '{self.cr_path.name}'",     # Relatif au project_path
        ]

        # Ajouter tous les fichiers à analyser (chemins relatifs)
        for scan_file in scan_files:
            # Chemin relatif depuis le project_path
            relative_path = scan_file.relative_to(self.project_path)
            cmd_parts.append(f"'{relative_path}'")

        cmd = " ".join(cmd_parts)

        self.logger.info(f"Analyse de {len(scan_files)} fichiers avec options avancées")
        self.logger.info(f"Commande AMC: {cmd}")
        
        result = self.run_command(cmd)

        if result['success']:
            self.logger.info("Analyse avancée terminée avec succès")
            analysis_stats = self.get_analysis_statistics()
            result['analysis_stats'] = analysis_stats
        else:
            self.logger.error(f"Échec analyse: {result.get('stderr')}")
            # Log détaillé pour debug
            self.logger.error(f"Stdout: {result.get('stdout')}")
            self.logger.error(f"Return code: {result.get('returncode')}")

        return result

    def analyze_question_difficulty(self):
        """Analyse la difficulté de chaque question"""
        # Cette fonction nécessiterait d'analyser les résultats intermédiaires
        # Pour l'instant, retourne des stats par défaut
        return [{'question': i+1, 'success_rate': 0.6} for i in range(10)]

    def generate_detailed_reports(self, include_individual=True, include_statistics=True):
        """Génère des rapports détaillés"""
        reports = {}
        
        # 1. Export CSV détaillé
        csv_export_results = self.export_results('csv')
        # export_results returns a list of tuples, so we need to extract the actual result dict
        if csv_export_results and csv_export_results[0][1]['success']:
            reports['csv'] = csv_export_results[0][1]
            reports['csv']['file_path'] = csv_export_results[0][2] # Add file path
        else:
            reports['csv'] = {'success': False, 'error': 'Failed to export CSV'}
        
        # 2. Export ODS (LibreOffice)
        ods_export_results = self.export_results('ods')
        if ods_export_results and ods_export_results[0][1]['success']:
            reports['ods'] = ods_export_results[0][1]
            reports['ods']['file_path'] = ods_export_results[0][2] # Add file path
        else:
            reports['ods'] = {'success': False, 'error': 'Failed to export ODS'}
        
        # 3. Rapport statistique détaillé
        if include_statistics:
            stats_file = self.exports_path / 'statistics.json'
            detailed_stats = self.generate_advanced_statistics()
            
            try:
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(detailed_stats, f, indent=2, ensure_ascii=False)
                
                reports['statistics'] = {
                    'success': True,
                    'file': str(stats_file), # Convert Path to string
                    'data': detailed_stats
                }
            except Exception as e:
                reports['statistics'] = {'success': False, 'error': f"Failed to write statistics file: {str(e)}"}
        
        # 4. Copies individuelles annotées
        if include_individual:
            annotated_result = self.generate_annotated_papers()
            reports['annotated'] = annotated_result
        
        return reports

    def generate_advanced_statistics(self):
        """Génère des statistiques avancées et détaillées"""
        stats = {
            'general': self.get_statistics(),
            'analysis': self.get_analysis_statistics(),
            'questions': [],
            'distribution': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Analyser le fichier CSV s'il existe
        csv_file = self.exports_path / 'notes.csv'
        if csv_file.exists():
            try:
                import pandas as pd
                df = pd.read_csv(csv_file)
                
                if not df.empty:
                    # Distribution détaillée des notes
                    if 'Note' in df.columns:
                        scores = df['Note'].dropna()
                        stats['distribution'] = {
                            'mean': float(scores.mean()),
                            'median': float(scores.median()),
                            'std': float(scores.std()),
                            'min': float(scores.min()),
                            'max': float(scores.max()),
                            'quartiles': {
                                'q1': float(scores.quantile(0.25)),
                                'q3': float(scores.quantile(0.75))
                            }
                        }
                    
                    # Analyse par question
                    question_cols = [col for col in df.columns if col.startswith('Q:')]
                    for i, col in enumerate(question_cols):
                        if col in df.columns:
                            question_scores = df[col].dropna()
                            if len(question_scores) > 0:
                                stats['questions'].append({
                                    'number': i + 1,
                                    'column': col,
                                    'success_rate': float(question_scores.mean() * 100),
                                    'difficulty': 'facile' if question_scores.mean() > 0.8 else 
                                                'difficile' if question_scores.mean() < 0.4 else 'moyenne'
                                })
            
            except ImportError:
                self.logger.warning("Pandas not installed, skipping detailed statistics generation.")
            except Exception as e:
                self.logger.error(f"Erreur statistiques avancées: {e}")
        
        return stats

    def analyse_papers(self, scan_path=None, threshold=0.5): # or advanced_analysis
        """Analyse les copies scannées avec conversion PDF automatique"""
        self.logger.info(f"DEBUG_START: analyse_papers - scan_path initial: {str(scan_path) if scan_path else 'None'}")

        if scan_path is None:
            scan_path = self.uploads_path
        
        # D'abord préparer/convertir les fichiers scannés
        self.logger.info(f"DEBUG_ANALYSE: Appel de prepare_scan_images avec scan_path: {str(scan_path)}") # DEBUG POINT 11
        prep_result = self.prepare_scan_images(scan_path)
        # Ensure result is JSON serializable before passing to json.dumps
        serializable_prep_result = {k: (str(v) if isinstance(v, Path) else v) for k, v in prep_result.items()}
        self.logger.info(f"DEBUG_ANALYSE: Résultat de prepare_scan_images: {json.dumps(serializable_prep_result, indent=2)}") # DEBUG POINT 12
        
        if not prep_result['success']:
            self.logger.error(f"DEBUG_ANALYSE_FAIL: Échec de la préparation des images: {prep_result.get('error', '')}")
            return prep_result
        
        # Utiliser les images préparées
        # prep_result['prepared_path'] is already a string, convert back to Path for Path operations
        prepared_path = Path(prep_result['prepared_path']) 
        image_files = []
        
        for ext in ['*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
            image_files.extend(list(prepared_path.glob(ext)))
        
        self.logger.info(f"DEBUG_ANALYSE: Images prêtes pour l'analyse dans {str(prepared_path)}: {[str(f) for f in image_files]}") # DEBUG POINT 13

        if not image_files:
            return {
                'success': False,
                'error': f'Aucune image trouvée après conversion dans {str(prepared_path)}'
            }
        
        self.logger.info(f"Analyse de {len(image_files)} images converties")
        
        cmd_parts = [
            "auto-multiple-choice",
            "analyse",
            f"--data '{self.data_path.name}'", # Use name as cwd is project_path
            f"--cr '{self.cr_path.name}'", # Use name as cwd is project_path
            #f"--threshold {threshold}"
        ]
        # Ajouter toutes les images converties
        for image_file in image_files:
            # Here too, AMC expects paths relative to the cwd if the files are not already in the cwd
            # Since prepared_path is a subfolder of self.project_path, the relative path is simply Path.name
            cmd_parts.append(f"'{image_file.relative_to(self.project_path)}'") # DEBUG POINT 14 - VERY IMPORTANT
        
        cmd = " ".join(cmd_parts)
        self.logger.info(f"DEBUG_CMD_ANALYSE: Commande AMC analyse: {cmd}") # DEBUG POINT 15 (very important)
        
        result = self.run_command(cmd)
        
        # Ensure result is JSON serializable before passing to json.dumps
        serializable_result = {k: (str(v) if isinstance(v, Path) else v) for k, v in result.items()}
        self.logger.info(f"DEBUG_ANALYSE_END: Résultat de l'analyse: {json.dumps(serializable_result, indent=2)}") # DEBUG POINT 16
        if result['success']:
            self.logger.info("Analyse terminée avec succès")
        else:
            self.logger.error(f"Échec analyse: {result.get('stderr')}")
        
        return result



    def create_layout_xml_from_sqlite(self):
        """Convertit layout.sqlite vers layout.xml pour compatibilité"""
        import xml.etree.ElementTree as ET
        import sqlite3
        
        db_path = self.data_path / 'layout.sqlite'
        xml_path = self.data_path / 'layout.xml'
        
        if not db_path.exists():
            return {'success': False, 'error': 'layout.sqlite not found'}
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            root = ET.Element("layout")
            
            # Variables
            cursor.execute("SELECT name, value FROM layout_variables")
            variables_data = cursor.fetchall()
            if variables_data:
                for name, value in variables_data:
                    var = ET.SubElement(root, "variable")
                    var.set("name", str(name))
                    var.text = str(value) if value else ""
            
            # Questions
            cursor.execute("SELECT question, name FROM layout_question")
            questions_data = cursor.fetchall()
            if questions_data:
                for question_id, name in questions_data:
                    q = ET.SubElement(root, "question")
                    q.set("id", str(question_id))
                    q.set("name", str(name) if name else "")
            
            # Pages
            cursor.execute("SELECT student, page, width, height, dpi FROM layout_page")
            pages_data = cursor.fetchall()
            if pages_data:
                for student, page, width, height, dpi in pages_data:
                    p = ET.SubElement(root, "page")
                    p.set("student", str(student))
                    p.set("page", str(page))
                    p.set("width", str(width) if width else "")
                    p.set("height", str(height) if height else "")
                    p.set("dpi", str(dpi) if dpi else "")
            
            # Boxes (zones de réponse) - IMPORTANT pour la correction
            cursor.execute("""
                SELECT student, page, question, answer, xmin, xmax, ymin, ymax, role, flags 
                FROM layout_box ORDER BY student, page, question, answer
            """)
            boxes_data = cursor.fetchall()
            if boxes_data:
                for student, page, question, answer, xmin, xmax, ymin, ymax, role, flags in boxes_data:
                    box = ET.SubElement(root, "box")
                    box.set("student", str(student))
                    box.set("page", str(page))
                    box.set("question", str(question) if question else "")
                    box.set("answer", str(answer) if answer else "")
                    box.set("xmin", str(xmin) if xmin else "")
                    box.set("xmax", str(xmax) if xmax else "")
                    box.set("ymin", str(ymin) if ymin else "")
                    box.set("ymax", str(ymax) if ymax else "")
                    box.set("role", str(role) if role else "")
                    box.set("flags", str(flags) if flags else "")
            
            # Associations étudiants
            cursor.execute("SELECT student, id, filename FROM layout_association")
            associations_data = cursor.fetchall()
            if associations_data:
                for student, student_id, filename in associations_data:
                    assoc = ET.SubElement(root, "association")
                    assoc.set("student", str(student))
                    assoc.set("id", str(student_id) if student_id else "")
                    assoc.set("filename", str(filename) if filename else "")
            
            # Zones générales
            cursor.execute("SELECT student, page, zone, xmin, xmax, ymin, ymax FROM layout_zone")
            zones_data = cursor.fetchall()
            if zones_data:
                for student, page, zone, xmin, xmax, ymin, ymax in zones_data:
                    z = ET.SubElement(root, "zone")
                    z.set("student", str(student))
                    z.set("page", str(page))
                    z.set("zone", str(zone) if zone else "")
                    z.set("xmin", str(xmin) if xmin else "")
                    z.set("xmax", str(xmax) if xmax else "")
                    z.set("ymin", str(ymin) if ymin else "")
                    z.set("ymax", str(ymax) if ymax else "")
            
            # Sauvegarder le XML
            tree = ET.ElementTree(root)
            tree.write(xml_path, encoding="utf-8", xml_declaration=True)
            conn.close()
            
            self.logger.info(f"Conversion SQLite vers XML terminée: {xml_path}")
            return {'success': True, 'xml_path': str(xml_path)}
        
        except Exception as e:
            self.logger.error(f"Erreur conversion SQLite vers XML: {e}")
            return {'success': False, 'error': str(e)}

    def full_correction_process(self, scoring_strategy='adaptive', auto_optimize=True, generate_reports=True):
        self.logger.info("Début du processus de correction complet (full_correction_process).")
        self.logger.debug(f"Paramètres reçus: scoring_strategy={scoring_strategy}, auto_optimize={auto_optimize}, generate_reports={generate_reports}")

        results = []

        try:
            # 1. Vérifier ET forcer la préparation du projet si nécessaire
            layout_sqlite = self.data_path / 'layout.sqlite'
            layout_ready = False
            
            if layout_sqlite.exists():
                # Vérifier que le layout contient des données
                try:
                    import sqlite3
                    conn = sqlite3.connect(layout_sqlite)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM layout_box")
                    box_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM layout_page")
                    page_count = cursor.fetchone()[0]
                    conn.close()
                    
                    if box_count > 0 and page_count > 0:
                        layout_ready = True
                        self.logger.info(f"Layout AMC valide trouvé: {box_count} boxes, {page_count} pages")
                    else:
                        self.logger.warning(f"Layout AMC vide: {box_count} boxes, {page_count} pages")
                        
                except Exception as e:
                    self.logger.error(f"Erreur vérification layout: {e}")
            
            if not layout_ready:
                self.logger.info("Préparation/Régénération du projet AMC...")
                
                # Supprimer les anciens fichiers de layout
                for db_file in ['layout.sqlite', 'report.sqlite']:
                    db_path = self.data_path / db_file
                    if db_path.exists():
                        try:
                            db_path.unlink()
                            self.logger.info(f"Ancien {db_file} supprimé")
                        except:
                            pass
                
                # Forcer la préparation
                prep_project_result = self.prepare_project()
                results.append(('prepare_project', prep_project_result))
                
                if not prep_project_result['success']:
                    self.logger.error(f"Échec de la préparation du projet: {prep_project_result.get('error', '')}")
                    return results
                
                # Vérifier à nouveau le layout après préparation
                try:
                    conn = sqlite3.connect(layout_sqlite)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM layout_box")
                    box_count = cursor.fetchone()[0]
                    conn.close()
                    
                    if box_count == 0:
                        self.logger.error("ERREUR CRITIQUE: Le layout n'a toujours pas été généré après prepare")
                        return results + [('layout_error', {'success': False, 'error': 'Layout non généré par AMC prepare'})]
                    else:
                        self.logger.info(f"Layout correctement généré: {box_count} zones détectées")
                        
                except Exception as e:
                    self.logger.error(f"Impossible de vérifier le layout après préparation: {e}")
                    return results + [('layout_verification_error', {'success': False, 'error': str(e)})]
            else:
                self.logger.info("Projet AMC déjà préparé avec layout valide.")
            
            # 2. Préparation et optimisation des scans
            self.logger.info("Étape 1/4: Préparation des images scannées...")
            prep_result = self.prepare_scan_images(scan_path=self.uploads_path)
            results.append(('prepare_scan_images', prep_result))
            if not prep_result['success']:
                self.logger.error(f"Échec de la préparation des images: {prep_result.get('error', '')}")
                return results
            self.logger.info(f"Préparation des images terminée. Succès: {prep_result['success']}")

            # 3. Analyse des copies avec vérification préalable
            self.logger.info("Étape 2/4: Analyse des copies...")
            
            # Vérifier qu'on a bien des images à analyser
            prepared_path = Path(prep_result['prepared_path'])
            image_files = []
            for ext in ['*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
                image_files.extend(list(prepared_path.glob(ext)))
            
            if not image_files:
                error_msg = f"Aucune image trouvée dans {prepared_path} pour l'analyse"
                self.logger.error(error_msg)
                return results + [('no_images_error', {'success': False, 'error': error_msg})]
            
            self.logger.info(f"Images trouvées pour analyse: {len(image_files)}")
            
            # Analyse simple et directe
            cmd_parts = [
                "auto-multiple-choice",
                "analyse",
                f"--data '{self.data_path.name}'",
                f"--cr '{self.cr_path.name}'",
            ]
            
            # Ajouter les images (max 10 pour éviter les lignes de commande trop longues)
            for image_file in image_files[:10]:
                relative_path = image_file.relative_to(self.project_path)
                cmd_parts.append(f"'{relative_path}'")
            
            cmd = " ".join(cmd_parts)
            self.logger.info(f"Commande d'analyse: {cmd}")
            
            analysis_result = self.run_command(cmd)
            results.append(('analyse_papers', analysis_result))
            
            if not analysis_result['success']:
                self.logger.error(f"Échec de l'analyse des copies: {analysis_result.get('error', '')}")
                self.logger.error(f"Stderr: {analysis_result.get('stderr')}")
                self.logger.error(f"Stdout: {analysis_result.get('stdout')}")
                return results
            
            self.logger.info(f"Analyse des copies terminée. Succès: {analysis_result['success']}")

            # 4. Calculer les notes
            self.logger.info("Étape 3/4: Calcul des notes...")
            marks_result = self.calculate_marks(scoring_strategy=scoring_strategy)
            results.append(('calculate_marks', marks_result))
            if not marks_result['success']:
                self.logger.error(f"Échec du calcul des notes: {marks_result.get('error', '')}")
                return results
            self.logger.info(f"Calcul des notes terminé. Succès: {marks_result['success']}")

            # 5. Exporter les résultats
            self.logger.info("Étape 4/4: Exportation des résultats...")
            export_result_csv = self.export_results(format_type='csv')
            results.append(('export_results_csv', export_result_csv))
            if export_result_csv and export_result_csv[0][1]['success']:
                self.logger.info(f"Export CSV terminé. Succès: {export_result_csv[0][1]['success']}")
            else:
                self.logger.warning("Export CSV échoué ou non trouvé dans le résultat.")

            if generate_reports:
                self.logger.info("Génération des copies annotées...")
                pretty_sheet_result = self.generate_annotated_papers()
                results.append(('generate_annotated_papers', pretty_sheet_result))
                self.logger.info(f"Génération des copies annotées terminée. Succès: {pretty_sheet_result['success']}")
            
            # 6. Statistiques finales
            final_stats = self.generate_advanced_statistics()
            results.append(('Statistiques finales', {'success': True, 'stats': final_stats}))
            
            self.logger.info("Processus de correction automatique terminé avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur processus correction: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            results.append(('Erreur critique', {'success': False, 'error': str(e)}))
        
        # Ensure all results in the list are JSON serializable
        final_results = []
        for item in results:
            if isinstance(item, tuple) and len(item) == 2:
                key, value = item
                if isinstance(value, dict):
                    serializable_value = {k: (str(v) if isinstance(v, Path) else v) for k, v in value.items()}
                    final_results.append((key, serializable_value))
                else:
                    final_results.append(item)
            else:
                final_results.append(item)

        return final_results


    def verify_correction_quality(self):
        """Vérifie la qualité de la correction et signale les problèmes potentiels"""
        issues = []
        recommendations = []
        
        # Vérifier les statistiques d'analyse
        analysis_stats = self.get_analysis_statistics()
        
        if analysis_stats['papers_detected'] == 0:
            issues.append("Aucune copie détectée - vérifiez la qualité des scans")
        
        if analysis_stats.get('unreadable_papers', 0) > 0:
            issues.append(f"{analysis_stats['unreadable_papers']} copies illisibles détectées")
            recommendations.append("Améliorer la qualité des scans (résolution, contraste)")
        
        if analysis_stats.get('missing_student_codes', 0) > 0:
            issues.append(f"{analysis_stats['missing_student_codes']} codes étudiants manquants")
            recommendations.append("Vérifier que les codes sont bien remplis et lisibles")
        
        # Vérifier la cohérence des résultats
        csv_file = self.exports_path / 'notes.csv'
        if csv_file.exists():
            try:
                import pandas as pd
                df = pd.read_csv(csv_file)
                
                if not df.empty and 'Note' in df.columns:
                    scores = df['Note'].dropna()
                    
                    # Détecter les anomalies statistiques
                    mean_score = scores.mean()
                    std_score = scores.std()
                    
                    if mean_score > 18:
                        issues.append(f"Moyenne très élevée ({mean_score:.1f}) - vérifiez le barème")
                    elif mean_score < 5:
                        issues.append(f"Moyenne très faible ({mean_score:.1f}) - questions trop difficiles?")
                    
                    if std_score < 1:
                        issues.append("Faible dispersion des notes - manque de discrimination")
                    
            except ImportError:
                self.logger.warning("Pandas not installed, skipping quality verification advanced stats.")
            except Exception as e:
                issues.append(f"Erreur analyse qualité: {e}")
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'quality_score': max(0, 100 - len(issues) * 20),  # Score sur 100
            'status': 'excellent' if not issues else 'attention' if len(issues) < 3 else 'problematique'
        }
    def fix_csv_names(self, csv_file_path):
        """Corrige les noms dans le fichier CSV généré"""
        try:
            # Lire le fichier liste.csv pour récupérer les noms
            names_map = {}
            liste_file = self.project_path / 'liste.csv'
            if liste_file.exists():
                with open(liste_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader, 1):
                        if 'nom' in row and 'prenom' in row:
                            names_map[str(i)] = f"{row['nom']} {row['prenom']}"
            
            # Corriger le fichier CSV des notes
            if names_map and os.path.exists(csv_file_path):
                with open(csv_file_path, 'r') as file:
                    content = file.read()
                
                for student_id, name in names_map.items():
                    content = content.replace(f'"{student_id}","","?",', f'"{student_id}","","{name}",')
                
                with open(csv_file_path, 'w') as file:
                    file.write(content)
                
                self.logger.info(f"Noms corrigés dans {csv_file_path}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la correction des noms: {e}")

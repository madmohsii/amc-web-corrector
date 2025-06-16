import os
import subprocess
import json
import shutil
from pathlib import Path
import logging
import csv

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

    def _generate_latex_header_french(self, title, subject, duration, instructions, csv_filename=None):
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
        
        \AMCaddpagesto{{4}}
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
                            instructions=None, csv_filename="liste.csv"):
        """Crée un fichier LaTeX AMC à partir de données structurées selon le format français"""
        
        print(f"Création template LaTeX avec {len(questions_data)} questions")
        
        if instructions is None:
            instructions = ("Vous ne devez cocher qu'une seule case. 1 point par bonne réponse. "
                          "-0.5 point par mauvaise réponse ou si plusieurs cases sont cochées. "
                          "0 point si aucune case n'est cochée pour la même question.")
        
        # Créer automatiquement un fichier CSV minimal si nécessaire
        self._ensure_csv_exists(csv_filename)
        
        # 1. En-tête LaTeX
        latex_content = self._generate_latex_header_french(title, subject, duration, instructions, csv_filename)
        
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
            print("Fichier LaTeX sauvegardé avec succès")
            
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
        
        # IMPORTANT : Utiliser AMC prepare au lieu de pdflatex
        # Cette commande génère les PDFs avec les marques AMC correctes
        abs_latex_file = latex_file.resolve()
        abs_project_path = self.project_path.resolve()
        
        # Commande AMC prepare avec les bons paramètres
        cmd = f"""auto-multiple-choice prepare \
            --mode s \
            --prefix '{abs_project_path}' \
            --filter plain \
            --out-sujet DOC-sujet.pdf \
            --out-corrige DOC-corrige.pdf \
            --out-catalog DOC-catalog.pdf \
            '{abs_latex_file.name}'"""
        
        self.logger.info(f"Exécution AMC prepare : {cmd}")
        
        result = self.run_command(cmd)
        
        if result['success'] or result['returncode'] == 0:
            self.logger.info("AMC prepare terminé")
            
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
                    'stderr': result.get('stderr', '')
                }
        
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
    
    def _fallback_pdflatex_compilation(self, latex_file):
        """Compilation de secours avec pdflatex"""
        self.logger.info("Tentative de compilation directe avec pdflatex...")
        
        abs_latex_file = latex_file.resolve()
        abs_project_path = self.project_path.resolve()
        
        # Compiler 2 fois pour résoudre les références
        for i in range(2):
            cmd = f"pdflatex -interaction=nonstopmode -output-directory '{abs_project_path}' '{abs_latex_file}'"
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

    # ... Le reste du code reste identique ...

    
    
    def calculate_marks(self, scoring_strategy='default'):
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
            cmd = f"auto-multiple-choice export --data {self.data_path} --module CSV --fich-noms '' --o '{csv_file}'"
            result = self.run_command(cmd)
            results.append(('CSV', result, csv_file))
        
        if format_type in ['ods', 'all']:
            # Export OpenDocument
            ods_file = self.exports_path / 'notes.ods'
            cmd = f"auto-multiple-choice export --data {self.data_path} --module ODS --fich-noms '' --o '{ods_file}'"
            result = self.run_command(cmd)
            results.append(('ODS', result, ods_file))
        
        return results
    
    def generate_annotated_papers(self):
        """Génère les copies annotées"""
        annotated_dir = self.exports_path / 'annotated'
        annotated_dir.mkdir(exist_ok=True)
        
        cmd = f"auto-multiple-choice annote --data {self.data_path} --cr {self.cr_path} --fich-noms '' --projet '{annotated_dir}'"
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info("Copies annotées générées")
        
        return result
    
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

    def full_process(self, questions_data=None, students_data=None, 
                    title="QCM", subject="", duration="60 minutes",
                    scoring_strategy='french', scan_path=None):
        """Processus complet de A à Z selon le format français"""
        results = []
        
        # 1. Créer le questionnaire complet si questions fournies
        if questions_data:
            try:
                latex_file = self.create_latex_template(
                    questions_data, title, subject, duration
                )
                results.append(('Questionnaire créé', {'success': True}, latex_file))
            except Exception as e:
                return [('Erreur création questionnaire', {'success': False, 'error': str(e)})]
        
        # 2. Préparer le projet
        result = self.prepare_project()
        results.append(('Préparation AMC', result))
        if not result['success']:
            return results
        
        # 3. Analyser les copies (optionnel si pas de scans)
        if scan_path or (self.uploads_path.exists() and any(self.uploads_path.iterdir())):
            result = self.analyse_papers(scan_path)
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
        else:
            results.append(('Analyse des copies', {'success': True, 'info': 'Pas de copies à analyser'}))
        
        return results

    def create_complete_questionnaire(self, questions_data, students_data=None, 
                                     title="QCM", subject="", duration="60 minutes", 
                                     instructions=None, csv_filename="liste.csv"):
        """Alias pour create_latex_template - compatibilité avec l'ancien code"""
        return self.create_latex_template(
            questions_data, title, subject, duration, instructions, csv_filename
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
    
    # Améliorations à ajouter à votre amc_manager.py

def create_answer_sheet(self, output_path=None):
    """Crée la feuille de réponses pour la correction"""
    if output_path is None:
        output_path = self.project_path / 'answer_sheet.pdf'
    
    cmd = f"auto-multiple-choice reponse --data '{self.data_path}' --sujet questionnaire.tex --fich '{output_path}'"
    result = self.run_command(cmd)
    
    if result['success']:
        self.logger.info(f"Feuille de réponses créée: {output_path}")
    
    return result

def auto_scan_detection(self, scan_files):
    """Détection automatique des paramètres de scan optimaux"""
    detection_results = []
    
    for scan_file in scan_files:
        cmd = f"auto-multiple-choice getimages --vector-density 300 --list-pages '{scan_file}'"
        result = self.run_command(cmd)
        
        if result['success']:
            detection_results.append({
                'file': scan_file,
                'pages': result['stdout'].count('\n'),
                'detected': True
            })
        else:
            detection_results.append({
                'file': scan_file,
                'error': result.get('stderr', 'Erreur de détection'),
                'detected': False
            })
    
    return detection_results

def prepare_scan_images(self, scan_path=None, dpi=300):
    """Prépare et optimise les images scannées pour l'analyse"""
    if scan_path is None:
        scan_path = self.uploads_path
    
    scan_files = []
    processed_files = []
    
    # Chercher tous les fichiers scannés
    for ext in ['*.pdf', '*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
        scan_files.extend(list(scan_path.glob(ext)))
    
    if not scan_files:
        return {
            'success': False,
            'error': f'Aucun fichier scanné trouvé dans {scan_path}'
        }
    
    # Créer dossier pour les images préparées
    prepared_path = self.project_path / 'prepared_scans'
    prepared_path.mkdir(exist_ok=True)
    
    for scan_file in scan_files:
        try:
            if scan_file.suffix.lower() == '.pdf':
                # Convertir PDF en images individuelles
                cmd = f"auto-multiple-choice getimages --vector-density {dpi} --copy-to '{prepared_path}' '{scan_file}'"
            else:
                # Copier et optimiser les images
                import shutil
                dest_file = prepared_path / scan_file.name
                shutil.copy2(scan_file, dest_file)
                cmd = f"echo 'Image copiée: {dest_file}'"
            
            result = self.run_command(cmd)
            if result['success']:
                processed_files.append(scan_file)
                self.logger.info(f"Fichier préparé: {scan_file}")
            else:
                self.logger.error(f"Erreur préparation {scan_file}: {result.get('stderr')}")
        
        except Exception as e:
            self.logger.error(f"Erreur traitement {scan_file}: {e}")
    
    return {
        'success': len(processed_files) > 0,
        'processed_files': processed_files,
        'prepared_path': prepared_path,
        'total_files': len(scan_files)
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
    prepared_path = prep_result['prepared_path']
    scan_files = list(prepared_path.glob('*'))
    
    if not scan_files:
        return {
            'success': False,
            'error': 'Aucun fichier préparé pour l\'analyse'
        }
    
    # Commande d'analyse avec options avancées
    cmd_parts = [
        "auto-multiple-choice",
        "analyse",
        f"--data '{self.data_path}'",
        f"--cr '{self.cr_path}'",
        f"--threshold {threshold}"
    ]
    
    if auto_capture:
        cmd_parts.append("--auto-capture")
    
    if try_harder:
        cmd_parts.append("--try-harder")
    
    # Ajouter tous les fichiers à analyser
    for scan_file in scan_files:
        cmd_parts.append(f"'{scan_file}'")
    
    cmd = " ".join(cmd_parts)
    
    self.logger.info(f"Analyse de {len(scan_files)} fichiers avec options avancées")
    result = self.run_command(cmd)
    
    if result['success']:
        self.logger.info("Analyse avancée terminée avec succès")
        
        # Vérifier les résultats d'analyse
        analysis_stats = self.get_analysis_statistics()
        result['analysis_stats'] = analysis_stats
    else:
        self.logger.error(f"Échec analyse: {result.get('stderr')}")
    
    return result

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
        cmd = f"auto-multiple-choice export --data '{self.data_path}' --module CSV --fich-noms '' --stats-only"
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

def smart_scoring(self, strategy='adaptive', bonus_malus=None):
    """Système de notation intelligent avec différentes stratégies"""
    
    scoring_strategies = {
        'french_standard': {'b': 1, 'm': -0.5, 'p': -0.5},  # Standard français
        'no_negative': {'b': 1, 'm': 0, 'p': 0},           # Pas de points négatifs
        'harsh': {'b': 1, 'm': -1, 'p': -0.25},            # Pénalité forte
        'bonus': {'b': 1.2, 'm': -0.3, 'p': 0},            # Bonus pour bonnes réponses
        'adaptive': None  # Sera calculé automatiquement
    }
    
    if strategy == 'adaptive':
        # Calculer automatiquement selon la difficulté des questions
        analysis_stats = self.get_analysis_statistics()
        if analysis_stats['papers_detected'] > 0:
            # Analyser les taux de réussite pour adapter le barème
            question_stats = self.analyze_question_difficulty()
            avg_difficulty = sum(q['success_rate'] for q in question_stats) / len(question_stats) if question_stats else 0.5
            
            if avg_difficulty > 0.8:  # Questions faciles
                bonus_malus = {'b': 1, 'm': -0.75, 'p': -0.5}
            elif avg_difficulty < 0.4:  # Questions difficiles
                bonus_malus = {'b': 1.5, 'm': -0.25, 'p': 0}
            else:  # Difficulté moyenne
                bonus_malus = {'b': 1, 'm': -0.5, 'p': -0.25}
        else:
            bonus_malus = scoring_strategies['french_standard']
    else:
        bonus_malus = bonus_malus or scoring_strategies.get(strategy, scoring_strategies['french_standard'])
    
    # Formatter le barème pour AMC
    bareme_str = f"(b={bonus_malus['b']},m={bonus_malus['m']},p={bonus_malus['p']})"
    
    cmd = f"auto-multiple-choice note --data '{self.data_path}' --bareme '{bareme_str}'"
    result = self.run_command(cmd)
    
    if result['success']:
        self.logger.info(f"Notation terminée avec barème: {bareme_str}")
        result['scoring_used'] = bonus_malus
    
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
    csv_result = self.export_results('csv')
    reports['csv'] = csv_result
    
    # 2. Export ODS (LibreOffice)
    ods_result = self.export_results('ods')
    reports['ods'] = ods_result
    
    # 3. Rapport statistique détaillé
    if include_statistics:
        stats_file = self.exports_path / 'statistics.json'
        detailed_stats = self.generate_advanced_statistics()
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_stats, f, indent=2, ensure_ascii=False)
        
        reports['statistics'] = {
            'success': True,
            'file': stats_file,
            'data': detailed_stats
        }
    
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
        
        except Exception as e:
            self.logger.error(f"Erreur statistiques avancées: {e}")
    
    return stats

def full_correction_process(self, scan_path=None, scoring_strategy='adaptive', 
                           generate_reports=True, auto_optimize=True):
    """Processus complet de correction automatique optimisé"""
    results = []
    
    try:
        # 1. Vérifier la préparation du projet
        if not (self.data_path / 'scoring.xml').exists():
            prep_result = self.prepare_project()
            results.append(('Préparation projet', prep_result))
            if not prep_result['success']:
                return results
        
        # 2. Préparation et optimisation des scans
        if auto_optimize:
            prep_result = self.prepare_scan_images(scan_path)
            results.append(('Préparation scans', prep_result))
            if not prep_result['success']:
                return results
        
        # 3. Analyse avancée des copies
        analysis_result = self.advanced_analysis(scan_path, auto_capture=True, try_harder=True)
        results.append(('Analyse copies', analysis_result))
        if not analysis_result['success']:
            return results
        
        # 4. Notation intelligente
        scoring_result = self.smart_scoring(scoring_strategy)
        results.append(('Calcul notes', scoring_result))
        if not scoring_result['success']:
            return results
        
        # 5. Génération des rapports
        if generate_reports:
            reports_result = self.generate_detailed_reports()
            results.append(('Génération rapports', {'success': True, 'reports': reports_result}))
        
        # 6. Statistiques finales
        final_stats = self.generate_advanced_statistics()
        results.append(('Statistiques finales', {'success': True, 'stats': final_stats}))
        
        self.logger.info("Processus de correction automatique terminé avec succès")
        
    except Exception as e:
        self.logger.error(f"Erreur processus correction: {e}")
        results.append(('Erreur critique', {'success': False, 'error': str(e)}))
    
    return results

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
                
        except Exception as e:
            issues.append(f"Erreur analyse qualité: {e}")
    
    return {
        'issues': issues,
        'recommendations': recommendations,
        'quality_score': max(0, 100 - len(issues) * 20),  # Score sur 100
        'status': 'excellent' if not issues else 'attention' if len(issues) < 3 else 'problematique'
    }
def prepare_scan_images(self, scan_path=None, dpi=300):
    """Prépare et optimise les images scannées pour l'analyse"""
    if scan_path is None:
        scan_path = self.uploads_path
    
    scan_files = []
    processed_files = []
    
    # Chercher tous les fichiers scannés
    for ext in ['*.pdf', '*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
        scan_files.extend(list(scan_path.glob(ext)))
    
    if not scan_files:
        return {
            'success': False,
            'error': f'Aucun fichier scanné trouvé dans {scan_path}'
        }
    
    # Créer dossier pour les images préparées
    prepared_path = self.project_path / 'prepared_scans'
    prepared_path.mkdir(exist_ok=True)
    
    for scan_file in scan_files:
        try:
            if scan_file.suffix.lower() == '.pdf':
                # Convertir PDF en images individuelles avec getimages
                self.logger.info(f"Conversion PDF vers images: {scan_file}")
                cmd = f"auto-multiple-choice getimages --vector-density {dpi} --copy-to '{prepared_path}' '{scan_file}'"
                result = self.run_command(cmd)
                
                if result['success']:
                    processed_files.append(scan_file)
                    self.logger.info(f"PDF converti avec succès: {scan_file}")
                else:
                    self.logger.error(f"Erreur conversion PDF {scan_file}: {result.get('stderr')}")
            else:
                # Copier les images directement
                import shutil
                dest_file = prepared_path / scan_file.name
                shutil.copy2(scan_file, dest_file)
                processed_files.append(scan_file)
                self.logger.info(f"Image copiée: {scan_file}")
        
        except Exception as e:
            self.logger.error(f"Erreur traitement {scan_file}: {e}")
    
    return {
        'success': len(processed_files) > 0,
        'processed_files': processed_files,
        'prepared_path': prepared_path,
        'total_files': len(scan_files)
    }

def analyse_papers(self, scan_path=None, threshold=0.5):
    """Analyse les copies scannées avec conversion PDF automatique"""
    if scan_path is None:
        scan_path = self.uploads_path
    
    # D'abord préparer/convertir les fichiers scannés
    prep_result = self.prepare_scan_images(scan_path)
    if not prep_result['success']:
        return prep_result
    
    # Utiliser les images préparées
    prepared_path = prep_result['prepared_path']
    image_files = []
    
    # Chercher les images converties (pas les PDF)
    for ext in ['*.jpg', '*.png', '*.jpeg', '*.tiff', '*.tif']:
        image_files.extend(list(prepared_path.glob(ext)))
    
    if not image_files:
        return {
            'success': False,
            'error': f'Aucune image trouvée après conversion dans {prepared_path}'
        }
    
    self.logger.info(f"Analyse de {len(image_files)} images converties")
    
    # Commande d'analyse avec les images converties
    cmd = f"auto-multiple-choice analyse --data '{self.data_path}' --cr '{self.cr_path}' --auto-capture --threshold {threshold}"
    
    # Ajouter toutes les images converties
    for image_file in image_files:
        cmd += f" '{image_file}'"
    
    result = self.run_command(cmd)
    
    if result['success']:
        self.logger.info(f"Analyse de {len(image_files)} images terminée")
        result['images_analyzed'] = len(image_files)
        result['conversion_info'] = prep_result
    
    return result
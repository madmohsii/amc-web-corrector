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
    
    def create_latex_template(self, questions_data, title="QCM", subject="", duration="60 minutes", 
                            instructions=None, csv_filename="liste.csv"):
        """Crée un fichier LaTeX AMC à partir de données structurées selon le format français"""
        
        if instructions is None:
            instructions = ("Vous ne devez cocher qu'une seule case. 1 point par bonne réponse. "
                          "-0.5 point par mauvaise réponse ou si plusieurs cases sont cochées. "
                          "0 point si aucune case n'est cochée pour la même question.")
        
        latex_content = self._generate_latex_header_french(title, subject, duration, instructions, csv_filename)
        
        # Générer les questions selon le format français
        for question in questions_data:
            latex_content += self._generate_question_latex_french(question)
        
        latex_content += self._generate_latex_footer_french(csv_filename)
        
        # Sauvegarder le fichier
        latex_file = self.project_path / 'questionnaire.tex'
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        return latex_file
    
    
    def _generate_latex_header_french(self, title, subject, duration, instructions, csv_filename=None):
    
    
    # Version avec CSV et codes pré-cochés
        if csv_filename is not None and os.path.exists(self.project_path / csv_filename):
            return f"""\\documentclass[12pt,a4paper]{{article}}

\\usepackage{{csvsimple,graphicx,pifont}}%
\\usepackage[francais,bloc]{{automultiplechoice}}
\\usepackage[utf8]{{inputenc}}    
\\usepackage[T1]{{fontenc}}
\\usepackage{{geometry}}

\\usepackage{{verbatimbox}}
\\usepackage{{tcolorbox}}

\\newtcolorbox{{codebox}}{{colback=gray!5!white, colframe=black, boxrule=0.5mm, arc=3mm, width=\\linewidth}}

% Configuration de la géométrie
\\geometry{{hmargin=2cm,top=4cm,bottom=2cm}}

\\newcommand{{\\sujet}}{{
	\\exemplaire{{1}}{{%
		% En-tête avec code élève PRÉ-COCHÉ automatiquement
		\\noindent
		\\begin{{minipage}}[t]{{0.3\\textwidth}}
			\\textbf{{Code élève}}\\\\[0.3cm]
			% Code élève PRÉ-COCHÉ basé sur l'ID du CSV
			\\AMCcode{{etudiant}}{{\\id}}
		\\end{{minipage}}%
		\\hfill
		\\begin{{minipage}}[t]{{0.65\\textwidth}}
			\\framebox[\\textwidth]{{%
				\\begin{{minipage}}{{0.95\\textwidth}}
					\\centering
					\\textbf{{Nom et prénom :}} \\nom{{}} \\prenom{{}}\\\\[0.5cm]
					\\dotfill\\\\[0.5cm]
					\\dotfill
				\\end{{minipage}}
			}}
		\\end{{minipage}}
		
		\\vspace{{1cm}}
		
		\\begin{{center}}
			\\textbf{{{title}}}\\\\[0.3cm]
			{subject}\\\\[0.2cm]
			Durée : {duration}.\\\\[0.5cm]
			\\textbf{{{instructions}}}
		\\end{{center}}
		
		\\vspace{{1cm}}
		
		\\restituegroupe{{CN}}
		\\AMCassociation{{\\id}}
		\\AMCaddpagesto{{4}}
	    }}
    }}

\\begin{{document}}
	\\AMCrandomseed{{1237893}}
	\\def\\AMCformQuestion#1{{{{\\sc Question #1 :}}}}
	\\setdefaultgroupmode{{withoutreplacement}}

	% Génération automatique des copies avec codes pré-cochés
	\\csvreader[head to column names]{{{csv_filename}}}{{}}{{%
		\\sujet
	    }}

\\end{{document}}

"""
        else:
        # Version sans CSV avec code élève vide (à remplir manuellement)
            return f"""\\documentclass[12pt,a4paper]{{article}}

\\usepackage{{graphicx,pifont}}%
\\usepackage[francais,bloc]{{automultiplechoice}}
\\usepackage[utf8]{{inputenc}}    
\\usepackage[T1]{{fontenc}}
\\usepackage{{geometry}}

\\usepackage{{verbatimbox}}
\\usepackage{{tcolorbox}}

\\newtcolorbox{{codebox}}{{colback=gray!5!white, colframe=black, boxrule=0.5mm, arc=3mm, width=\\linewidth}}

% Configuration de la géométrie
\\geometry{{hmargin=2cm,top=4cm,bottom=2cm}}

\\newcommand{{\\sujet}}{{
	\\exemplaire{{1}}{{%
		% En-tête avec code élève VIDE (à remplir manuellement)
		\\noindent
		\\begin{{minipage}}[t]{{0.3\\textwidth}}
			\\textbf{{Code élève}}\\\\[0.3cm]
			% Code élève avec 2 chiffres VIDES
			\\AMCcode{{etudiant}}{{2}}
		\\end{{minipage}}%
		\\hfill
		\\begin{{minipage}}[t]{{0.65\\textwidth}}
			\\framebox[\\textwidth]{{%
				\\begin{{minipage}}{{0.95\\textwidth}}
					\\centering
					\\textbf{{Nom et prénom :}}\\\\[0.5cm]
					\\dotfill\\\\[0.5cm]
					\\dotfill
				\\end{{minipage}}
			}}
		\\end{{minipage}}
		
		\\vspace{{1cm}}
		
		\\begin{{center}}
			\\textbf{{{title}}}\\\\[0.3cm]
			{subject}\\\\[0.2cm]
			Durée : {duration}.\\\\[0.5cm]
			\\textbf{{{instructions}}}
		\\end{{center}}
		
		\\vspace{{1cm}}
		
		\\restituegroupe{{CN}}
		\\AMCrandomseed{{1237893}}
		\\AMCaddpagesto{{4}}
	    }}
    }}

\\begin{{document}}
	\\AMCrandomseed{{1237893}}
	\\def\\AMCformQuestion#1{{{{\\sc Question #1 :}}}}
	\\setdefaultgroupmode{{withoutreplacement}}

    """
    
    def _generate_question_latex_french(self, question):
    
        question_id = question.get('id', 'q1')
        question_text = question['text']
        choices = question['choices']
    
        latex = f"""% {question.get('comment', 'Question générée')}
    \\element{{CN}}{{
	    \\begin{{question}}{{{question_id}}}\\scoring{{b=1,m=-.5,p=-0.5}}
		    {question_text}
		    \\begin{{reponseshoriz}}
    """
    
        for choice in choices:
            if choice.get('correct', False):
                latex += f"\t\t\t\\bonne{{{choice['text']}}}\n"
            else:
                latex += f"\t\t\t\\mauvaise{{{choice['text']}}}\n"
    
        latex += "\t\t\\end{reponseshoriz}\n\t\\end{question}\n}\n\n"
        return latex
    
    def _generate_latex_footer_french(self, csv_filename=None):
    
    
    # Vérifier explicitement si le CSV existe et contient des données
        if csv_filename is not None:
            csv_path = self.project_path / csv_filename
            if csv_path.exists():
                try:
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        import csv
                        reader = csv.DictReader(f)
                        csv_data = list(reader)
                        if len(csv_data) > 0:
                        # Version avec CSV - génération multiple
                            print(f"Footer: Utilisation du CSV avec {len(csv_data)} élèves")
                            return f"""
    %% GÉNÉRATION DES COPIES AVEC CSV %%
    \\csvreader[head to column names]{{{csv_filename}}}{{}}{{\\sujet}}

    \\end{{document}}
    """
                except Exception as e:
                    print(f"Erreur lecture CSV dans footer: {e}")
    
    # Version sans CSV - copie unique
        print("Footer: Mode copie unique")
        return f"""
    %% GÉNÉRATION D'UNE COPIE SIMPLE %%
    \\sujet

    \\end{{document}}
    """
    
    def create_student_list_csv(self, students_data=None, csv_filename="liste.csv"):
        """Crée le fichier CSV des étudiants"""
        csv_file = self.project_path / csv_filename
        
        if students_data is None:
            # CSV par défaut avec un seul ID
            students_data = [{'id': '1'}]
        
        # Écrire le CSV
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if students_data:
                fieldnames = students_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for student in students_data:
                    writer.writerow(student)
        
        self.logger.info(f"Fichier CSV créé: {csv_file}")
        return csv_file
    
    def create_complete_questionnaire(self, questions_data, students_data=None, title="QCM", subject="", duration="60 minutes", csv_filename="liste.csv"):
    
        print(f"=== Création questionnaire dans {self.project_path} ===")
        print(f"Nombre de questions: {len(questions_data)}")
        print(f"Titre: {title}")

    # Vérifier explicitement si le CSV existe
        csv_path = self.project_path / csv_filename
        csv_exists = csv_path.exists()
        print(f"Vérification CSV: {csv_path} - Existe: {csv_exists}")
    
        if csv_exists:
        # Lire le contenu du CSV pour voir s'il contient des données
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    import csv
                    reader = csv.DictReader(f)
                    csv_data = list(reader)
                    print(f"CSV trouvé avec {len(csv_data)} élèves")
                    for student in csv_data:
                        print(f"  - {student.get('prenom', '')} {student.get('nom', '')} (code: {student.get('code', '')})")
            except Exception as e:
                print(f"Erreur lecture CSV: {e}")
                csv_exists = False
    
    # Créer le fichier LaTeX
        print("Création du fichier LaTeX...")
    
    # FORCER l'utilisation du CSV si il existe et contient des données
        use_csv = csv_exists and len(csv_data) > 0 if csv_exists else False
        print(f"Utilisation du CSV: {use_csv}")
    
        latex_file = self.create_latex_template(
            questions_data, title, subject, duration, 
            csv_filename=csv_filename if use_csv else None
        )

        print(f"Fichier LaTeX créé: {latex_file}")

    # Vérifier que le fichier a bien été créé
        if latex_file.exists():
            file_size = latex_file.stat().st_size
            print(f"Fichier vérifié - Taille: {file_size} bytes")
        
        # Lire et afficher un extrait pour debug
            with open(latex_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Début du contenu:\n{content[:500]}...")
            
            # Vérifier si csvreader est présent
                if 'csvreader' in content:
                    print("✅ Template utilise bien csvreader (mode multi-copies)")
                else:
                    print("❌ Template en mode copie unique")
        else:
            print("ERREUR: Le fichier LaTeX n'a pas été créé!")
            raise Exception(f"Le fichier LaTeX n'a pas pu être créé: {latex_file}")

        return latex_file

    def create_latex_template(self, questions_data, title="QCM", subject="", duration="60 minutes", 
                        instructions=None, csv_filename=None):
    
    
            print(f"Création template LaTeX avec {len(questions_data)} questions")
    
            if instructions is None:
                instructions = ("Vous ne devez cocher qu'une seule case. 1 point par bonne réponse. "
                            "-0.5 point par mauvaise réponse ou si plusieurs cases sont cochées. "
                            "0 point si aucune case n'est cochée pour la même question.")
    
            latex_content = self._generate_latex_header_french(title, subject, duration, instructions, csv_filename)
    
    # Générer les questions selon le format français
            print("Génération des questions...")
            for i, question in enumerate(questions_data):
                print(f"  Question {i+1}: {question.get('text', '')[:50]}...")
                latex_content += self._generate_question_latex_french(question)
    
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
    
    def prepare_project(self, latex_file=None):
    
        if latex_file is None:
            latex_file = self.project_path / 'questionnaire.tex'
    
        if not latex_file.exists():
            return {
                'success': False,
                'error': f'Fichier LaTeX non trouvé: {latex_file}'
            }
    
        self.logger.info(f"Préparation du projet avec le fichier: {latex_file}")
    
    # Nettoyer les anciens fichiers de compilation
        extensions_to_clean = ['*.pdf', '*.aux', '*.log', '*.fls', '*.fdb_latexmk', '*.out']
        for ext in extensions_to_clean:
            for file in self.project_path.glob(ext):
                try:
                    file.unlink()
                    self.logger.info(f"Fichier nettoyé: {file}")
                except OSError as e:
                    self.logger.warning(f"Impossible de nettoyer {file}: {e}")
    
    # Vérifier que le répertoire data existe
        self.data_path.mkdir(parents=True, exist_ok=True)
    
    # Convertir en chemins absolus pour éviter les problèmes
        abs_latex_file = latex_file.resolve()
        abs_data_path = self.data_path.resolve()
    
    # Préparer les sujets avec la commande AMC (avec chemins absolus)
        cmd = f"auto-multiple-choice prepare --with pdflatex --filter latex --data '{abs_data_path}' '{abs_latex_file}'"
        self.logger.info(f"Exécution de la commande: {cmd}")
    
        result = self.run_command(cmd)
    
        if result['success']:
            self.logger.info("Compilation AMC réussie")
        
        # Chercher le PDF généré par AMC
            possible_pdf_names = [
                'amc-compiled.pdf',
                f'{latex_file.stem}.pdf',
                'questionnaire.pdf'
            ]
        
            pdf_found = False
            for pdf_name in possible_pdf_names:
                amc_pdf = self.project_path / pdf_name
                if amc_pdf.exists() and amc_pdf.stat().st_size > 1000:
                # Copier vers un nom standardisé
                    output_pdf = self.project_path / 'questionnaire_output.pdf'
                    try:
                        import shutil
                        shutil.copy2(amc_pdf, output_pdf)
                        self.logger.info(f"PDF copié: {amc_pdf} -> {output_pdf}")
                        pdf_found = True
                        break
                    except Exception as e:
                        self.logger.error(f"Erreur copie PDF: {e}")
        
            if not pdf_found:
                self.logger.warning("Aucun PDF valide trouvé après compilation")
            # Essayer une compilation directe avec pdflatex
                return self._fallback_pdflatex_compilation(latex_file)
        else:
            self.logger.error(f"Échec compilation AMC: {result.get('stderr', 'Erreur inconnue')}")
        # Essayer une compilation directe avec pdflatex
            return self._fallback_pdflatex_compilation(latex_file)
    
        return result
    
    def _fallback_pdflatex_compilation(self, latex_file):
    
        self.logger.info("Tentative de compilation directe avec pdflatex...")
    
    # Convertir en chemin absolu
        abs_latex_file = latex_file.resolve()
        abs_project_path = self.project_path.resolve()
    
    # Commande pdflatex directe avec chemins absolus
        cmd = f"pdflatex -interaction=nonstopmode -output-directory '{abs_project_path}' '{abs_latex_file}'"
        self.logger.info(f"Commande pdflatex: {cmd}")
    
        result = self.run_command(cmd)
    
    # IMPORTANT: Vérifier d'abord si le PDF existe, même en cas d'erreur LaTeX
        pdf_output = self.project_path / f"{latex_file.stem}.pdf"
        if pdf_output.exists() and pdf_output.stat().st_size > 1000:
        # PDF créé avec succès malgré les warnings/erreurs LaTeX
            standard_pdf = self.project_path / 'questionnaire_output.pdf'
            try:
                import shutil
                shutil.copy2(pdf_output, standard_pdf)
                self.logger.info(f"PDF de secours créé avec succès: {standard_pdf}")
                self.logger.info(f"Taille du PDF: {pdf_output.stat().st_size} bytes")
            
            # Succès même si LaTeX a retourné des warnings
                return {
                    'success': True,
                    'stdout': result['stdout'],
                    'stderr': result['stderr'],
                    'method': 'pdflatex_fallback',
                    'pdf_size': pdf_output.stat().st_size,
                    'warnings': 'PDF créé avec des warnings LaTeX (normal)'
                }
            except Exception as e:
                self.logger.error(f"Erreur copie PDF de secours: {e}")
    
    # Si vraiment aucun PDF n'a été créé
        if result['success']:
            return {
                'success': False,
                'error': 'PDF non généré malgré une compilation réussie',
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', ''),
            }
        else:
            return {
                'success': False,
                'error': 'Échec de compilation LaTeX (AMC et pdflatex)',
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', ''),
            }
    
    def analyse_papers(self, scan_path=None, threshold=0.5):
        """Analyse les copies scannées"""
        if scan_path is None:
            scan_path = self.uploads_path
        
        scan_files = []
        if isinstance(scan_path, str):
            scan_path = Path(scan_path)
        
        # Chercher les fichiers scannés
        for ext in ['*.pdf', '*.jpg', '*.png', '*.jpeg']:
            scan_files.extend(list(scan_path.glob(ext)))
        
        if not scan_files:
            return {
                'success': False,
                'error': f'Aucun fichier scanné trouvé dans {scan_path}'
            }
        
        # Commande d'analyse
        cmd = f"auto-multiple-choice analyse --data {self.data_path} --cr {self.cr_path} --auto-capture --threshold {threshold}"
        
        # Ajouter les fichiers scannés
        for scan_file in scan_files:
            cmd += f" '{scan_file}'"
        
        result = self.run_command(cmd)
        
        if result['success']:
            self.logger.info(f"Analyse de {len(scan_files)} fichiers terminée")
        
        return result
    
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
                latex_file = self.create_complete_questionnaire(
                    questions_data, students_data, title, subject, duration
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
            # Ajoutez les autres questions selon le même pattern...
        ]
        
        return self.create_complete_questionnaire(
            questions_data,
            title="BTS CIEL1 - Subnetting",
            subject="",
            duration="60 minutes"
        )
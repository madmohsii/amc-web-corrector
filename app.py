from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from dashboard import register_dashboard_routes
import os
import subprocess
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import shutil
from amc_manager import AMCManager
from sample_questions import SAMPLE_QUESTIONS, SCORING_STRATEGIES
from dashboard import register_dashboard_routes

app = Flask(__name__)
app.secret_key = 'votre-cle-secrete-ici'  # Changez ceci en production

# Configuration
UPLOAD_FOLDER = 'uploads'
AMC_PROJECTS_FOLDER = 'amc-projects'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Créér les dossiers nécessaires
for folder in [UPLOAD_FOLDER, AMC_PROJECTS_FOLDER, RESULTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Enregistrer les routes du dashboard
register_dashboard_routes(app, AMC_PROJECTS_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_amc_command(command, project_path):
    """Exécute une commande AMC et retourne le résultat"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=project_path
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'command': command
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'command': command
        }

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/download_qcm/<project_id>')
def download_qcm(project_id):
    """Télécharger le QCM en PDF"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        
        if not os.path.exists(project_path):
            flash('Projet non trouvé', 'error')
            return redirect(url_for('list_projects'))
        
        # Utiliser AMCManager pour générer le PDF
        amc = AMCManager(project_path)
        
        # Vérifier s'il y a un fichier LaTeX, sinon le créer
        latex_file = os.path.join(project_path, 'questionnaire.tex')
        if not os.path.exists(latex_file):
            # Créer un QCM de base s'il n'existe pas
            config_file = os.path.join(project_path, 'qcm_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    questions_data = config_data.get('questions', [])
                    title = config_data.get('title', 'QCM')
                    subject = config_data.get('subject', '')
                    duration = config_data.get('duration', '60 minutes')
                    
                    # Créer le questionnaire avec la configuration
                    amc.create_complete_questionnaire(
                        questions_data, 
                        title=title, 
                        subject=subject, 
                        duration=duration
                    )
            else:
                # Utiliser les questions d'exemple
                formatted_sample = []
                for i, q in enumerate(SAMPLE_QUESTIONS):
                    formatted_q = {
                        'id': f'q{i+1}',
                        'text': q.get('text', ''),
                        'choices': q.get('choices', []),
                        'comment': f'Question d\'exemple {i+1}'
                    }
                    formatted_sample.append(formatted_q)
                amc.create_complete_questionnaire(formatted_sample)
        
        # Nettoyer les anciens PDFs pour forcer la régénération
        pdf_files_to_clean = [
            'amc-compiled.pdf',
            'questionnaire_output.pdf', 
            'questionnaire.pdf'
        ]
        
        for pdf_file in pdf_files_to_clean:
            pdf_path = os.path.join(project_path, pdf_file)
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    print(f"Ancien PDF supprimé: {pdf_path}")
                except OSError as e:
                    print(f"Impossible de supprimer {pdf_path}: {e}")
        
        # Préparer le projet (compilation LaTeX vers PDF)
        print(f"Compilation du projet dans: {project_path}")
        result = amc.prepare_project()
        
        # Affichage des détails du résultat pour debug
        print(f"Résultat compilation: {result}")
        
        if not result['success']:
            error_msg = result.get('stderr', result.get('error', 'Erreur inconnue'))
            print(f"Erreur compilation LaTeX: {error_msg}")
            flash(f'Erreur compilation LaTeX: {error_msg}', 'error')
            
            # En cas d'échec, proposer le téléchargement du LaTeX
            if os.path.exists(latex_file):
                return send_file(latex_file, as_attachment=True, download_name=f'qcm_{project_id}.tex')
            else:
                flash('Aucun fichier à télécharger', 'error')
                return redirect(url_for('project_detail', project_id=project_id))
        
        # Chercher le PDF généré (avec plus de vérifications)
        possible_pdf_paths = [
            os.path.join(project_path, 'amc-compiled.pdf'),
            os.path.join(project_path, 'questionnaire_output.pdf'),
            os.path.join(project_path, 'questionnaire.pdf')
        ]
        
        pdf_file = None
        for pdf_path in possible_pdf_paths:
            print(f"Vérification du PDF: {pdf_path}")
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"Taille du fichier: {file_size} bytes")
                
                if file_size > 1000:  # Vérifier que le fichier n'est pas vide/corrompu
                    pdf_file = pdf_path
                    print(f"PDF trouvé et valide: {pdf_path}")
                    break
                else:
                    print(f"PDF trop petit, probablement corrompu: {pdf_path}")
        
        if pdf_file:
            # Créer un nom de fichier plus descriptif
            try:
                with open(os.path.join(project_path, 'project_info.json'), 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
                    project_name = project_info.get('name', 'qcm')
            except:
                project_name = 'qcm'
            
            # Nettoyer le nom pour éviter les caractères problématiques
            safe_project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            download_name = f"{safe_project_name}_{project_id}.pdf"
            
            print(f"Téléchargement du PDF: {pdf_file} -> {download_name}")
            return send_file(pdf_file, as_attachment=True, download_name=download_name)
        else:
            print("Aucun PDF valide trouvé")
            flash('PDF non généré ou corrompu', 'error')
            
            # Fallback vers le LaTeX si disponible
            if os.path.exists(latex_file):
                flash('Téléchargement du fichier LaTeX à la place', 'warning')
                return send_file(latex_file, as_attachment=True, download_name=f'qcm_{project_id}.tex')
            else:
                flash('Aucun fichier à télécharger', 'error')
                return redirect(url_for('project_detail', project_id=project_id))
            
    except Exception as e:
        print(f"Exception dans download_qcm: {str(e)}")
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

@app.route('/preview_qcm/<project_id>')
def preview_qcm(project_id):
    """Prévisualiser le QCM (génère le PDF et l'affiche dans le navigateur)"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        
        if not os.path.exists(project_path):
            flash('Projet non trouvé', 'error')
            return redirect(url_for('list_projects'))
        
        amc = AMCManager(project_path)
        
        # Générer le PDF si nécessaire
        result = amc.prepare_project()
        
        if result['success']:
            possible_pdf_paths = [
                os.path.join(project_path, 'amc-compiled.pdf'),
                os.path.join(project_path, 'questionnaire_output.pdf'),
                os.path.join(project_path, 'questionnaire.pdf')
            ]
            
            for pdf_path in possible_pdf_paths:
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                    return send_file(pdf_path, mimetype='application/pdf')
        
        flash('Impossible de générer la prévisualisation', 'error')
        return redirect(url_for('project_detail', project_id=project_id))
        
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

@app.route('/generate_pdf/<project_id>')
def generate_pdf(project_id):
    """Force la régénération du PDF"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        amc = AMCManager(project_path)
        
        # Nettoyer les anciens PDFs
        for pdf_file in ['amc-compiled.pdf', 'questionnaire_output.pdf', 'questionnaire.pdf']:
            pdf_path = os.path.join(project_path, pdf_file)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        
        # Régénérer
        result = amc.prepare_project()
        
        if result['success']:
            flash('PDF généré avec succès', 'success')
        else:
            flash(f'Erreur génération PDF: {result.get("stderr", "Erreur inconnue")}', 'error')
        
        return redirect(url_for('project_detail', project_id=project_id))
        
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

@app.route('/create_project', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        if not project_name:
            flash('Nom du projet requis', 'error')
            return redirect(url_for('create_project'))
        
        # Créer un ID unique pour le projet
        project_id = str(uuid.uuid4())[:8]
        project_path = os.path.join(AMC_PROJECTS_FOLDER, f"{project_name}_{project_id}")
        
        try:
            os.makedirs(project_path, exist_ok=True)
            
            # Créer la structure AMC avec AMCManager
            amc = AMCManager(project_path)
            
            # Sauvegarder les métadonnées du projet
            project_info = {
                'name': project_name,
                'id': project_id,
                'created': datetime.now().isoformat(),
                'path': project_path
            }
            
            with open(os.path.join(project_path, 'project_info.json'), 'w') as f:
                json.dump(project_info, f, indent=2)
            
            flash(f'Projet "{project_name}" créé avec succès!', 'success')
            return redirect(url_for('project_detail', project_id=f"{project_name}_{project_id}"))
            
        except Exception as e:
            flash(f'Erreur lors de la création du projet: {str(e)}', 'error')
    
    return render_template('create_project.html')

@app.route('/projects')
def list_projects():
    projects = []
    if os.path.exists(AMC_PROJECTS_FOLDER):
        for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
            project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
            info_file = os.path.join(project_path, 'project_info.json')
            
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r') as f:
                        project_info = json.load(f)
                        project_info['folder'] = project_folder
                        
                        # Vérifier si un PDF existe
                        pdf_exists = False
                        for pdf_name in ['amc-compiled.pdf', 'questionnaire_output.pdf', 'questionnaire.pdf']:
                            if os.path.exists(os.path.join(project_path, pdf_name)):
                                pdf_exists = True
                                break
                        project_info['pdf_ready'] = pdf_exists
                        
                        projects.append(project_info)
                except:
                    pass
    
    return render_template('projects.html', projects=projects)

@app.route('/project/<project_id>')
def project_detail(project_id):
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    info_file = os.path.join(project_path, 'project_info.json')
    
    if not os.path.exists(info_file):
        flash('Projet non trouvé', 'error')
        return redirect(url_for('list_projects'))
    
    with open(info_file, 'r') as f:
        project_info = json.load(f)
    
    # Vérifier les fichiers uploadés
    uploads_path = os.path.join(project_path, 'uploads')
    uploaded_files = []
    if os.path.exists(uploads_path):
        uploaded_files = os.listdir(uploads_path)
    
    # Vérifier si un PDF existe
    pdf_exists = False
    for pdf_name in ['amc-compiled.pdf', 'questionnaire_output.pdf', 'questionnaire.pdf']:
        if os.path.exists(os.path.join(project_path, pdf_name)):
            pdf_exists = True
            break
    
    # Vérifier si un LaTeX existe
    latex_exists = os.path.exists(os.path.join(project_path, 'questionnaire.tex'))
    
    return render_template('project_detail.html', 
                         project=project_info, 
                         project_id=project_id,
                         uploaded_files=uploaded_files,
                         pdf_exists=pdf_exists,
                         latex_exists=latex_exists)

@app.route('/upload/<project_id>', methods=['POST'])
def upload_file(project_id):
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        uploads_path = os.path.join(project_path, 'uploads')
        os.makedirs(uploads_path, exist_ok=True)
        
        file_path = os.path.join(uploads_path, filename)
        file.save(file_path)
        
        return jsonify({'success': True, 'filename': filename})
    
    return jsonify({'success': False, 'error': 'Type de fichier non autorisé'})

@app.route('/process/<project_id>')
def process_project(project_id):
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    uploads_path = os.path.join(project_path, 'uploads')
    
    if not os.path.exists(uploads_path) or not os.listdir(uploads_path):
        return jsonify({'success': False, 'error': 'Aucun fichier à traiter'})
    
    try:
        # Utiliser notre nouveau gestionnaire AMC
        amc = AMCManager(project_path)
        
        # Vérifier s'il y a un fichier LaTeX, sinon créer un exemple
        latex_file = os.path.join(project_path, 'questionnaire.tex')
        if not os.path.exists(latex_file):
            # Créer un QCM de test avec le bon format
            formatted_sample = []
            for i, q in enumerate(SAMPLE_QUESTIONS):
                formatted_q = {
                    'id': f'q{i+1}',
                    'text': q.get('text', ''),
                    'choices': q.get('choices', []),
                    'comment': f'Question d\'exemple {i+1}'
                }
                formatted_sample.append(formatted_q)
            amc.create_complete_questionnaire(formatted_sample)
        
        # Processus complet avec scoring français
        results = amc.full_process(scoring_strategy='french', scan_path=uploads_path)
        
        # Formater les résultats pour l'affichage
        formatted_results = []
        for step, result in results:
            formatted_results.append({
                'step': step,
                'success': result.get('success', False),
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', ''),
                'error': result.get('error', ''),
                'info': result.get('info', '')
            })
        
        return jsonify({
            'success': True, 
            'results': formatted_results,
            'statistics': amc.get_statistics()
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Erreur lors du traitement: {str(e)}'
        })

@app.route('/results/<project_id>')
def view_results(project_id):
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    results_path = os.path.join(project_path, 'cr')
    exports_path = os.path.join(project_path, 'exports')
    
    # Ici vous devriez parser les résultats AMC
    # Pour le moment, on affiche juste les fichiers générés
    
    results = []
    for path in [results_path, exports_path]:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith('.csv') or file.endswith('.pdf') or file.endswith('.ods'):
                    results.append(file)
    
    return render_template('results.html', 
                         project_id=project_id, 
                         results=results)

@app.route('/configure/<project_id>', methods=['GET', 'POST'])
def configure_project(project_id):
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    info_file = os.path.join(project_path, 'project_info.json')
    
    if not os.path.exists(info_file):
        flash('Projet non trouvé', 'error')
        return redirect(url_for('list_projects'))
    
    with open(info_file, 'r') as f:
        project_info = json.load(f)
    
    if request.method == 'POST':
        # Traiter la configuration du QCM
        questions_data = []
        
        # Récupérer les paramètres généraux
        title = request.form.get('title', 'QCM')
        subject = request.form.get('subject', '')
        duration = request.form.get('duration', '60 minutes')
        
        # Récupérer les questions du formulaire
        question_count = int(request.form.get('question_count', 0))
        
        for i in range(question_count):
            question_text = request.form.get(f'question_{i}_text')
            if question_text:
                choices = []
                choice_count = int(request.form.get(f'question_{i}_choice_count', 0))
                
                for j in range(choice_count):
                    choice_text = request.form.get(f'question_{i}_choice_{j}_text')
                    is_correct = request.form.get(f'question_{i}_choice_{j}_correct') == 'on'
                    
                    if choice_text:
                        choices.append({
                            'text': choice_text,
                            'correct': is_correct
                        })
                
                questions_data.append({
                    'id': f'q{i+1}',
                    'text': question_text,
                    'choices': choices,
                    'comment': f'Question {i+1}'
                })
        
        # Sauvegarder la configuration
        config_file = os.path.join(project_path, 'qcm_config.json')
        config = {
            'title': title,
            'subject': subject,
            'duration': duration,
            'questions': questions_data
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # Créer le fichier LaTeX avec AMCManager
        try:
            amc = AMCManager(project_path)
            latex_file = amc.create_complete_questionnaire(
                questions_data, 
                title=title, 
                subject=subject, 
                duration=duration
            )
            flash('Configuration du QCM sauvegardée avec succès!', 'success')
        except Exception as e:
            flash(f'Erreur lors de la création du LaTeX: {str(e)}', 'error')
        
        return redirect(url_for('project_detail', project_id=project_id))
    
    # Charger la configuration existante si elle existe
    config_file = os.path.join(project_path, 'qcm_config.json')
    existing_config = {
        'title': 'QCM',
        'subject': '',
        'duration': '60 minutes',
        'questions': []
    }
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            existing_config = json.load(f)
    
    return render_template('configure_qcm.html', 
                         project=project_info, 
                         project_id=project_id,
                         existing_config=existing_config,
                         sample_questions=SAMPLE_QUESTIONS,
                         scoring_strategies=SCORING_STRATEGIES)

@app.route('/api/project/<project_id>/files')
def api_project_files(project_id):
    """API pour récupérer la liste des fichiers d'un projet"""
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    uploads_path = os.path.join(project_path, 'uploads')
    
    files = []
    if os.path.exists(uploads_path):
        files = os.listdir(uploads_path)
    
    return jsonify(files)

@app.route('/api/export/<project_id>/<format_type>')
def api_export_results(project_id, format_type):
    """API pour exporter les résultats"""
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    
    if format_type == 'csv':
        csv_file = os.path.join(project_path, 'exports', 'notes.csv')
        if os.path.exists(csv_file):
            return send_file(csv_file, as_attachment=True, download_name=f'notes_{project_id}.csv')
        else:
            return jsonify({'success': False, 'error': 'Fichier CSV non trouvé'}), 404
    
    return jsonify({'success': False, 'error': 'Format non supporté'}), 400

@app.route('/delete/<project_id>/<filename>', methods=['DELETE'])
def delete_file(project_id, filename):
    """Supprimer un fichier uploadé"""
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    file_path = os.path.join(project_path, 'uploads', secure_filename(filename))
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Fichier non trouvé'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/students/<project_id>', methods=['GET', 'POST'])
def manage_students(project_id):
    """Gérer la liste des élèves avec leurs codes"""
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    info_file = os.path.join(project_path, 'project_info.json')
    
    if not os.path.exists(info_file):
        flash('Projet non trouvé', 'error')
        return redirect(url_for('list_projects'))
    
    with open(info_file, 'r') as f:
        project_info = json.load(f)
    
    if request.method == 'POST':
        # Traiter l'ajout/modification des élèves
        students_data = []
        
        # Récupérer le nombre d'élèves
        student_count = int(request.form.get('student_count', 0))
        
        for i in range(student_count):
            nom = request.form.get(f'student_{i}_nom', '').strip()
            prenom = request.form.get(f'student_{i}_prenom', '').strip()
            code = request.form.get(f'student_{i}_code', '').strip()
            
            if nom and prenom:  # Au minimum nom et prénom requis
                student = {
                    'id': code if code else str(i+1).zfill(3),  # Code ou numéro auto
                    'nom': nom,
                    'prenom': prenom,
                    'code': code if code else str(i+1).zfill(3)
                }
                students_data.append(student)
        
        # Sauvegarder la liste des élèves
        students_file = os.path.join(project_path, 'students.json')
        with open(students_file, 'w', encoding='utf-8') as f:
            json.dump(students_data, f, indent=2, ensure_ascii=False)
        
        # Créer le CSV AMC
        if students_data:
            amc = AMCManager(project_path)
            amc.create_student_list_csv(students_data)
            flash(f'{len(students_data)} élèves ajoutés avec succès!', 'success')
        else:
            flash('Aucun élève valide ajouté', 'warning')
        
        return redirect(url_for('manage_students', project_id=project_id))
    
    # Charger la liste existante
    students_file = os.path.join(project_path, 'students.json')
    existing_students = []
    if os.path.exists(students_file):
        with open(students_file, 'r', encoding='utf-8') as f:
            existing_students = json.load(f)
    
    return render_template('manage_students.html', 
                         project=project_info,
                         project_id=project_id,
                         students=existing_students)

# Fonction améliorée pour créer le CSV avec codes
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



# Nouvelles routes à ajouter à votre app.py

@app.route('/correct/<project_id>', methods=['GET', 'POST'])
def correct_project(project_id):
    """Interface de correction automatique"""
    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
    info_file = os.path.join(project_path, 'project_info.json')
    
    if not os.path.exists(info_file):
        flash('Projet non trouvé', 'error')
        return redirect(url_for('list_projects'))
    
    with open(info_file, 'r') as f:
        project_info = json.load(f)
    
    if request.method == 'POST':
        try:
            amc = AMCManager(project_path)
            
            # Récupérer les paramètres de correction
            scoring_strategy = request.form.get('scoring_strategy', 'adaptive')
            auto_optimize = request.form.get('auto_optimize') == 'on'
            generate_reports = request.form.get('generate_reports', 'on') == 'on'
            
            # Lancer le processus de correction complet
            results = amc.full_correction_process(
                scoring_strategy=scoring_strategy,
                auto_optimize=auto_optimize,
                generate_reports=generate_reports
            )
            
            # Vérifier la qualité de la correction
            quality_check = amc.verify_correction_quality()
            
            return render_template('correction_results.html',
                                 project=project_info,
                                 project_id=project_id,
                                 results=results,
                                 quality_check=quality_check)
        
        except Exception as e:
            flash(f'Erreur lors de la correction: {str(e)}', 'error')
            return redirect(url_for('project_detail', project_id=project_id))
    
    # GET: Afficher l'interface de configuration de correction
    uploads_path = os.path.join(project_path, 'uploads')
    uploaded_files = []
    if os.path.exists(uploads_path):
        uploaded_files = [f for f in os.listdir(uploads_path) 
                         if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.tiff'))]
    
    # Vérifier si le questionnaire est prêt
    latex_exists = os.path.exists(os.path.join(project_path, 'questionnaire.tex'))
    data_prepared = os.path.exists(os.path.join(project_path, 'data'))
    
    scoring_options = {
        'adaptive': 'Adaptatif (recommandé)',
        'french_standard': 'Standard français (1/-0.5/-0.5)',
        'no_negative': 'Sans points négatifs (1/0/0)',
        'harsh': 'Pénalité forte (1/-1/-0.25)',
        'bonus': 'Avec bonus (1.2/-0.3/0)'
    }
    
    return render_template('configure_correction.html',
                         project=project_info,
                         project_id=project_id,
                         uploaded_files=uploaded_files,
                         latex_exists=latex_exists,
                         data_prepared=data_prepared,
                         scoring_options=scoring_options)

@app.route('/api/correction/start/<project_id>', methods=['POST'])
def api_start_correction(project_id):
    """API pour démarrer la correction en arrière-plan"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        amc = AMCManager(project_path)
        
        # Récupérer les paramètres JSON
        params = request.get_json() or {}
        scoring_strategy = params.get('scoring_strategy', 'adaptive')
        auto_optimize = params.get('auto_optimize', True)
        
        # Démarrer le processus
        results = amc.full_correction_process(
            scoring_strategy=scoring_strategy,
            auto_optimize=auto_optimize
        )
        
        # Calculer le statut global
        success_count = sum(1 for _, result in results if result.get('success', False))
        total_steps = len(results)
        overall_success = success_count == total_steps
        
        return jsonify({
            'success': overall_success,
            'results': [
                {
                    'step': step,
                    'success': result.get('success', False),
                    'message': result.get('stdout', result.get('info', '')),
                    'error': result.get('stderr', result.get('error', ''))
                }
                for step, result in results
            ],
            'statistics': amc.generate_advanced_statistics() if overall_success else None
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/correction/quality/<project_id>')
def api_correction_quality(project_id):
    """API pour vérifier la qualité de la correction"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        amc = AMCManager(project_path)
        
        quality_check = amc.verify_correction_quality()
        return jsonify(quality_check)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/correction/preview/<project_id>')
def api_correction_preview(project_id):
    """API pour prévisualiser les paramètres de correction"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        uploads_path = os.path.join(project_path, 'uploads')
        
        # Compter les fichiers à traiter
        scan_files = []
        if os.path.exists(uploads_path):
            for ext in ['*.pdf', '*.jpg', '*.jpeg', '*.png', '*.tiff']:
                scan_files.extend(Path(uploads_path).glob(ext))
        
        # Estimer le temps de traitement (approximatif)
        estimated_time = len(scan_files) * 30  # 30 secondes par fichier en moyenne
        
        return jsonify({
            'success': True,
            'scan_files_count': len(scan_files),
            'estimated_time_seconds': estimated_time,
            'scan_files': [f.name for f in scan_files],
            'project_ready': os.path.exists(os.path.join(project_path, 'data'))
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/download_results/<project_id>/<format>')
def download_results(project_id, format):
    """Télécharger les résultats dans différents formats"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        exports_path = os.path.join(project_path, 'exports')
        
        if format == 'csv':
            file_path = os.path.join(exports_path, 'notes.csv')
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True, 
                               download_name=f'notes_{project_id}.csv')
        
        elif format == 'ods':
            file_path = os.path.join(exports_path, 'notes.ods')
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True,
                               download_name=f'notes_{project_id}.ods')
        
        elif format == 'statistics':
            file_path = os.path.join(exports_path, 'statistics.json')
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True,
                               download_name=f'statistiques_{project_id}.json')
        
        elif format == 'annotated':
            # Créer un ZIP avec toutes les copies annotées
            annotated_dir = os.path.join(exports_path, 'annotated')
            if os.path.exists(annotated_dir):
                zip_path = os.path.join(exports_path, f'copies_annotees_{project_id}.zip')
                
                import zipfile
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(annotated_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, annotated_dir)
                            zipf.write(file_path, arcname)
                
                return send_file(zip_path, as_attachment=True,
                               download_name=f'copies_annotees_{project_id}.zip')
        
        flash(f'Format {format} non disponible ou fichier non trouvé', 'error')
        return redirect(url_for('project_detail', project_id=project_id))
    
    except Exception as e:
        flash(f'Erreur téléchargement: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

@app.route('/reprocess/<project_id>')
def reprocess_project(project_id):
    """Relancer le processus de correction avec de nouveaux paramètres"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        
        # Nettoyer les anciens résultats
        paths_to_clean = [
            os.path.join(project_path, 'cr'),
            os.path.join(project_path, 'exports')
        ]
        
        for path in paths_to_clean:
            if os.path.exists(path):
                shutil.rmtree(path)
                os.makedirs(path, exist_ok=True)
        
        flash('Projet nettoyé, vous pouvez relancer la correction', 'info')
        return redirect(url_for('correct_project', project_id=project_id))
    
    except Exception as e:
        flash(f'Erreur nettoyage: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

@app.route('/scan_check/<project_id>')
def scan_check(project_id):
    """Vérifier la qualité des scans avant correction"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        uploads_path = os.path.join(project_path, 'uploads')
        
        if not os.path.exists(uploads_path):
            return jsonify({'success': False, 'error': 'Dossier uploads non trouvé'})
        
        amc = AMCManager(project_path)
        
        # Analyser les fichiers scannés
        scan_files = []
        for ext in ['*.pdf', '*.jpg', '*.jpeg', '*.png', '*.tiff']:
            scan_files.extend(Path(uploads_path).glob(ext))
        
        if not scan_files:
            return jsonify({'success': False, 'error': 'Aucun fichier scanné trouvé'})
        
        # Détecter les propriétés des scans
        detection_results = amc.auto_scan_detection(scan_files)
        
        return jsonify({
            'success': True,
            'files_count': len(scan_files),
            'detection_results': detection_results,
            'recommendations': [
                'Utilisez une résolution de 300 DPI minimum',
                'Assurez-vous que les codes étudiants sont bien lisibles',
                'Évitez les reflets et ombres sur les copies',
                'Alignez correctement les copies avant scan'
            ]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    


# Routes API supplémentaires à ajouter à app.py

@app.route('/api/optimize/<project_id>', methods=['POST'])
def api_optimize_project(project_id):
    """API pour optimiser les paramètres d'un projet"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        
        if not os.path.exists(project_path):
            return jsonify({'success': False, 'error': 'Projet non trouvé'}), 404
        
        # Importer l'optimiseur
        from correction_optimizer import CorrectionOptimizer
        
        amc = AMCManager(project_path)
        optimizer = CorrectionOptimizer()
        
        # Récupérer les paramètres de la requête
        params = request.get_json() or {}
        quick_mode = params.get('quick_optimization', True)
        
        # Chercher les fichiers scannés
        uploads_path = os.path.join(project_path, 'uploads')
        scan_files = []
        if os.path.exists(uploads_path):
            for ext in ['*.pdf', '*.jpg', '*.jpeg', '*.png', '*.tiff']:
                scan_files.extend(Path(uploads_path).glob(ext))
        
        if not scan_files:
            return jsonify({
                'success': False, 
                'error': 'Aucun fichier scanné trouvé pour optimisation'
            }), 400
        
        # Lancer l'optimisation
        if quick_mode:
            # Optimisation rapide - seulement les seuils
            threshold_result = optimizer.optimize_threshold_parameters(
                amc, scan_files, step=0.2  # Moins de tests pour être plus rapide
            )
            
            results = {}
            if threshold_result:
                results['threshold'] = threshold_result
            
            # Générer des recommandations simples
            recommendations = []
            if threshold_result and threshold_result.score < 0.7:
                recommendations.append("Qualité de scan perfectible - vérifiez résolution et contraste")
            if threshold_result and threshold_result.parameters['threshold'] > 0.8:
                recommendations.append("Seuil élevé requis - alignement des copies à améliorer")
        else:
            # Optimisation complète
            results = optimizer.run_full_optimization(amc, scan_files)
            recommendations = optimizer.generate_recommendations(results)
        
        return jsonify({
            'success': True,
            'results': {
                key: {
                    'parameters': result.parameters,
                    'score': result.score,
                    'processing_time': result.processing_time,
                    'quality_metrics': result.quality_metrics
                }
                for key, result in results.items()
            },
            'recommendations': recommendations,
            'optimization_type': 'quick' if quick_mode else 'complete'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur optimisation: {str(e)}'
        }), 500

@app.route('/api/correction/status/<project_id>')
def api_correction_status(project_id):
    """API pour obtenir le statut de correction d'un projet"""
    try:
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        
        if not os.path.exists(project_path):
            return jsonify({'success': False, 'error': 'Projet non trouvé'}), 404
        
        # Vérifier les étapes de correction
        status = {
            'questionnaire_ready': os.path.exists(os.path.join(project_path, 'questionnaire.tex')),
            'project_prepared': os.path.exists(os.path.join(project_path, 'data')),
            'scans_uploaded': False,
            'analysis_completed': False,
            'scoring_completed': False,
            'exports_generated': False,
            'last_correction': None,
            'scan_count': 0,
            'correction_quality': None
        }
        
        # Vérifier les scans
        uploads_path = os.path.join(project_path, 'uploads')
        if os.path.exists(uploads_path):
            scan_files = [f for f in os.listdir(uploads_path) 
                         if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.tiff'))]
            status['scans_uploaded'] = len(scan_files) > 0
            status['scan_count'] = len(scan_files)
        
        # Vérifier l'analyse
        cr_path = os.path.join(project_path, 'cr')
        if os.path.exists(cr_path) and os.listdir(cr_path):
            status['analysis_completed'] = True
        
        # Vérifier la notation
        exports_path = os.path.join(project_path, 'exports')
        csv_file = os.path.join(exports_path, 'notes.csv')
        if os.path.exists(csv_file):
            status['scoring_completed'] = True
            status['exports_generated'] = True
            
            # Date de dernière correction
            status['last_correction'] = datetime.fromtimestamp(
                os.path.getmtime(csv_file)
            ).isoformat()
            
            # Évaluer la qualité de correction
            try:
                amc = AMCManager(project_path)
                quality_check = amc.verify_correction_quality()
                status['correction_quality'] = quality_check['status']
            except:
                status['correction_quality'] = 'unknown'
        
        # Calculer le pourcentage de progression
        steps_completed = sum([
            status['questionnaire_ready'],
            status['project_prepared'], 
            status['scans_uploaded'],
            status['analysis_completed'],
            status['scoring_completed']
        ])
        status['completion_percentage'] = (steps_completed / 5) * 100
        
        return jsonify({
            'success': True,
            'status': status
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur statut: {str(e)}'
        }), 500

@app.route('/api/correction/batch-process', methods=['POST'])
def api_batch_correction():
    """API pour corriger plusieurs projets en lot"""
    try:
        data = request.get_json()
        project_ids = data.get('project_ids', [])
        correction_params = data.get('params', {})
        
        if not project_ids:
            return jsonify({'success': False, 'error': 'Aucun projet spécifié'}), 400
        
        results = []
        
        for project_id in project_ids:
            project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
            
            if not os.path.exists(project_path):
                results.append({
                    'project_id': project_id,
                    'success': False,
                    'error': 'Projet non trouvé'
                })
                continue
            
            try:
                amc = AMCManager(project_path)
                
                # Vérifier que le projet est prêt
                status_response = api_correction_status(project_id)
                status_data = json.loads(status_response.data)
                
                if not status_data['success']:
                    results.append({
                        'project_id': project_id,
                        'success': False,
                        'error': 'Impossible de vérifier le statut'
                    })
                    continue
                
                project_status = status_data['status']
                if not (project_status['questionnaire_ready'] and 
                       project_status['project_prepared'] and 
                       project_status['scans_uploaded']):
                    results.append({
                        'project_id': project_id,
                        'success': False,
                        'error': 'Projet non prêt pour correction'
                    })
                    continue
                
                # Lancer la correction
                correction_results = amc.full_correction_process(
                    scoring_strategy=correction_params.get('scoring_strategy', 'adaptive'),
                    auto_optimize=correction_params.get('auto_optimize', True),
                    generate_reports=correction_params.get('generate_reports', True)
                )
                
                # Vérifier le succès global
                success_count = sum(1 for _, result in correction_results if result.get('success', False))
                overall_success = success_count == len(correction_results)
                
                results.append({
                    'project_id': project_id,
                    'success': overall_success,
                    'steps_completed': success_count,
                    'total_steps': len(correction_results),
                    'details': correction_results if not overall_success else None
                })
                
            except Exception as e:
                results.append({
                    'project_id': project_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Résumé global
        successful_corrections = sum(1 for r in results if r['success'])
        
        return jsonify({
            'success': True,
            'summary': {
                'total_projects': len(project_ids),
                'successful_corrections': successful_corrections,
                'failed_corrections': len(project_ids) - successful_corrections,
                'success_rate': (successful_corrections / len(project_ids)) * 100
            },
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur correction en lot: {str(e)}'
        }), 500

@app.route('/api/stats/global-correction')
def api_global_correction_stats():
    """API pour les statistiques globales de correction"""
    try:
        from dashboard import get_correction_statistics
        
        stats = get_correction_statistics()
        
        # Ajouter des métriques supplémentaires
        total_projects = 0
        corrected_projects = 0
        
        if os.path.exists(AMC_PROJECTS_FOLDER):
            for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
                project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
                if os.path.isdir(project_path):
                    total_projects += 1
                    
                    # Vérifier si corrigé
                    csv_file = os.path.join(project_path, 'exports', 'notes.csv')
                    if os.path.exists(csv_file):
                        corrected_projects += 1
        
        stats['total_projects_created'] = total_projects
        stats['corrected_projects'] = corrected_projects
        stats['correction_adoption_rate'] = (corrected_projects / total_projects * 100) if total_projects > 0 else 0
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur statistiques: {str(e)}'
        }), 500

@app.route('/api/export/batch-results', methods=['POST'])
def api_batch_export():
    """API pour exporter les résultats de plusieurs projets"""
    try:
        data = request.get_json()
        project_ids = data.get('project_ids', [])
        export_format = data.get('format', 'csv')
        
        if not project_ids:
            return jsonify({'success': False, 'error': 'Aucun projet spécifié'}), 400
        
        # Créer un fichier ZIP avec tous les exports
        import zipfile
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                for project_id in project_ids:
                    project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
                    
                    # Chercher le fichier d'export
                    if export_format == 'csv':
                        export_file = os.path.join(project_path, 'exports', 'notes.csv')
                    elif export_format == 'ods':
                        export_file = os.path.join(project_path, 'exports', 'notes.ods')
                    else:
                        continue
                    
                    if os.path.exists(export_file):
                        # Ajouter au ZIP avec un nom descriptif
                        arc_name = f"{project_id}_notes.{export_format}"
                        zipf.write(export_file, arc_name)
            
            # Envoyer le fichier ZIP
            return send_file(
                tmp_file.name, 
                as_attachment=True, 
                download_name=f'corrections_batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
                mimetype='application/zip'
            )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur export en lot: {str(e)}'
        }), 500

# Route pour la page de correction en lot
@app.route('/batch-correction')
def batch_correction_page():
    """Page pour la correction en lot de plusieurs projets"""
    # Récupérer tous les projets disponibles
    projects = []
    if os.path.exists(AMC_PROJECTS_FOLDER):
        for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
            project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
            info_file = os.path.join(project_path, 'project_info.json')
            
            if os.path.exists(info_file):
                try:
                    with open(info_file, 'r') as f:
                        project_info = json.load(f)
                    
                    # Vérifier le statut du projet
                    project_info['folder'] = project_folder
                    
                    # Statut de correction
                    csv_file = os.path.join(project_path, 'exports', 'notes.csv')
                    project_info['is_corrected'] = os.path.exists(csv_file)
                    
                    # Vérifier si prêt pour correction
                    latex_exists = os.path.exists(os.path.join(project_path, 'questionnaire.tex'))
                    data_prepared = os.path.exists(os.path.join(project_path, 'data'))
                    uploads_path = os.path.join(project_path, 'uploads')
                    has_scans = os.path.exists(uploads_path) and any(
                        f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.tiff'))
                        for f in os.listdir(uploads_path)
                    )
                    
                    project_info['ready_for_correction'] = latex_exists and data_prepared and has_scans
                    
                    projects.append(project_info)
                except:
                    continue
    
    # Trier par date de création (plus récent en premier)
    projects.sort(key=lambda x: x.get('created', ''), reverse=True)
    
    return render_template('batch_correction.html', projects=projects)

# Fonction utilitaire pour nettoyer les anciens fichiers temporaires
def cleanup_temp_files():
    """Nettoie les fichiers temporaires anciens"""
    import tempfile
    import time
    
    temp_dir = tempfile.gettempdir()
    current_time = time.time()
    
    # Supprimer les fichiers de plus de 24h
    for filename in os.listdir(temp_dir):
        if filename.startswith('tmp') and filename.endswith('.zip'):
            file_path = os.path.join(temp_dir, filename)
            try:
                if current_time - os.path.getmtime(file_path) > 86400:  # 24h
                    os.remove(file_path)
            except:
                pass

# Ajouter un endpoint de maintenance
@app.route('/api/maintenance/cleanup')
def api_cleanup():
    """API pour nettoyer les fichiers temporaires"""
    try:
        cleanup_temp_files()
        return jsonify({'success': True, 'message': 'Nettoyage effectué'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/help')
def help_page():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
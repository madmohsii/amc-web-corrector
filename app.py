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

# Créer les dossiers nécessaires
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
            
            # Créer la structure AMC
            data_path = os.path.join(project_path, 'data')
            cr_path = os.path.join(project_path, 'cr')
            
            os.makedirs(data_path, exist_ok=True)
            os.makedirs(cr_path, exist_ok=True)
            
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
    
    return render_template('project_detail.html', 
                         project=project_info, 
                         project_id=project_id,
                         uploaded_files=uploaded_files)

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
            # Créer un QCM de test
            amc.create_latex_template(SAMPLE_QUESTIONS)
        
        # Processus complet
        results = amc.full_process(scoring_strategy='default')
        
        # Formater les résultats pour l'affichage
        formatted_results = []
        for step, result in results:
            formatted_results.append({
                'step': step,
                'success': result.get('success', False),
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', ''),
                'error': result.get('error', '')
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
    
    # Ici vous devriez parser les résultats AMC
    # Pour le moment, on affiche juste les fichiers générés
    
    results = []
    if os.path.exists(results_path):
        for file in os.listdir(results_path):
            if file.endswith('.csv') or file.endswith('.pdf'):
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
                    'text': question_text,
                    'choices': choices
                })
        
        # Sauvegarder la configuration
        config_file = os.path.join(project_path, 'qcm_config.json')
        with open(config_file, 'w') as f:
            json.dump(questions_data, f, indent=2)
        
        # Créer le fichier LaTeX
        try:
            amc = AMCManager(project_path)
            latex_file = amc.create_latex_template(questions_data)
            flash('Configuration du QCM sauvegardée avec succès!', 'success')
        except Exception as e:
            flash(f'Erreur lors de la création du LaTeX: {str(e)}', 'error')
        
        return redirect(url_for('project_detail', project_id=project_id))
    
    # Charger la configuration existante si elle existe
    config_file = os.path.join(project_path, 'qcm_config.json')
    existing_config = []
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
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

@app.route('/help')
def help_page():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

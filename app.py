from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import subprocess
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import shutil

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
    return render_template('index.html')

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
    
    # Exemple de traitement AMC basique
    commands = [
        # Ici vous devrez adapter selon votre fichier source LaTeX
        f"auto-multiple-choice prepare --mode s --prefix {project_id} --data {os.path.join(project_path, 'data')}",
        f"auto-multiple-choice analyse --projet {os.path.join(project_path, 'data')} --cr {os.path.join(project_path, 'cr')} --auto-capture",
        f"auto-multiple-choice note --data {os.path.join(project_path, 'data')} --bareme default"
    ]
    
    results = []
    for cmd in commands:
        result = run_amc_command(cmd, project_path)
        results.append(result)
        if not result['success']:
            break
    
    return jsonify({'success': True, 'results': results})

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

if __name__ == '__main__':
    app.run(debug=True)

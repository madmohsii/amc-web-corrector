from flask import render_template, jsonify, request
import os
import json
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
from pathlib import Path

def register_dashboard_routes(app, AMC_PROJECTS_FOLDER):
    """Enregistre les routes du dashboard"""
    
    @app.route('/dashboard')
    def dashboard():
        """Page principale du dashboard avec statistiques"""
        stats = get_global_statistics()
        recent_projects = get_recent_projects()
        return render_template('dashboard.html', 
                             stats=stats, 
                             recent_projects=recent_projects)
    
    @app.route('/api/stats/overview')
    def api_stats_overview():
        """API pour les statistiques générales"""
        return jsonify(get_global_statistics())
    
    @app.route('/api/stats/project/<project_id>')
    def api_stats_project(project_id):
        """API pour les statistiques d'un projet spécifique"""
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        return jsonify(get_project_statistics(project_path))
    
    @app.route('/api/chart/scores/<project_id>')
    def api_chart_scores(project_id):
        """API pour les données de graphique des scores"""
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        return jsonify(get_scores_distribution(project_path))
    
    @app.route('/api/chart/questions/<project_id>')
    def api_chart_questions(project_id):
        """API pour l'analyse par question"""
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        return jsonify(get_questions_analysis(project_path))

def get_global_statistics():
    """Calcule les statistiques globales de tous les projets"""
    from app import AMC_PROJECTS_FOLDER
    
    stats = {
        'total_projects': 0,
        'total_students': 0,
        'total_papers_processed': 0,
        'average_success_rate': 0,
        'projects_this_month': 0,
        'recent_activity': []
    }
    
    if not os.path.exists(AMC_PROJECTS_FOLDER):
        return stats
    
    projects_data = []
    current_month = datetime.now().replace(day=1)
    
    for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
        info_file = os.path.join(project_path, 'project_info.json')
        
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    project_info = json.load(f)
                
                stats['total_projects'] += 1
                
                # Vérifier si créé ce mois
                created_date = datetime.fromisoformat(project_info['created'].replace('Z', '+00:00'))
                if created_date >= current_month:
                    stats['projects_this_month'] += 1
                
                # Analyser les résultats s'ils existent
                project_stats = get_project_statistics(project_path)
                if project_stats:
                    stats['total_students'] += project_stats.get('total_papers', 0)
                    stats['total_papers_processed'] += project_stats.get('total_papers', 0)
                    
                    if project_stats.get('average_score', 0) > 0:
                        projects_data.append(project_stats['average_score'])
                
                # Activité récente
                stats['recent_activity'].append({
                    'project_name': project_info['name'],
                    'created': project_info['created'],
                    'id': project_folder
                })
                
            except Exception as e:
                continue
    
    # Calculer le taux de réussite moyen
    if projects_data:
        stats['average_success_rate'] = sum(projects_data) / len(projects_data)
    
    # Trier l'activité récente
    stats['recent_activity'] = sorted(
        stats['recent_activity'], 
        key=lambda x: x['created'], 
        reverse=True
    )[:5]
    
    return stats

def get_recent_projects(limit=5):
    """Récupère les projets récents"""
    from app import AMC_PROJECTS_FOLDER
    
    if not os.path.exists(AMC_PROJECTS_FOLDER):
        return []
    
    projects = []
    for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
        info_file = os.path.join(project_path, 'project_info.json')
        
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    project_info = json.load(f)
                project_info['folder'] = project_folder
                project_info['has_results'] = os.path.exists(os.path.join(project_path, 'exports', 'notes.csv'))
                projects.append(project_info)
            except:
                continue
    
    return sorted(projects, key=lambda x: x['created'], reverse=True)[:limit]

def get_project_statistics(project_path):
    """Calcule les statistiques détaillées d'un projet"""
    stats = {
        'total_papers': 0,
        'average_score': 0,
        'min_score': 0,
        'max_score': 0,
        'success_rate': 0,  # Pourcentage >= 10/20
        'questions_count': 0,
        'difficult_questions': [],
        'score_distribution': {}
    }
    
    # Chercher le fichier CSV des résultats
    csv_file = os.path.join(project_path, 'exports', 'notes.csv')
    
    if not os.path.exists(csv_file):
        return stats
    
    try:
        df = pd.read_csv(csv_file)
        
        if df.empty:
            return stats
        
        # Statistiques de base
        if 'Note' in df.columns:
            scores = df['Note'].dropna()
            if len(scores) > 0:
                stats['total_papers'] = len(scores)
                stats['average_score'] = float(scores.mean())
                stats['min_score'] = float(scores.min())
                stats['max_score'] = float(scores.max())
                
                # Taux de réussite (supposons 10/20 comme seuil)
                passing_threshold = 10
                passing_students = len(scores[scores >= passing_threshold])
                stats['success_rate'] = (passing_students / len(scores)) * 100
                
                # Distribution des scores par tranches
                bins = [0, 5, 10, 15, 20]
                score_counts = pd.cut(scores, bins=bins, include_lowest=True).value_counts()
                stats['score_distribution'] = {
                    '0-5': int(score_counts.iloc[0]) if len(score_counts) > 0 else 0,
                    '5-10': int(score_counts.iloc[1]) if len(score_counts) > 1 else 0,
                    '10-15': int(score_counts.iloc[2]) if len(score_counts) > 2 else 0,
                    '15-20': int(score_counts.iloc[3]) if len(score_counts) > 3 else 0
                }
        
        # Analyser les questions individuelles
        question_cols = [col for col in df.columns if col.startswith('Q:')]
        stats['questions_count'] = len(question_cols)
        
        difficult_questions = []
        for i, col in enumerate(question_cols):
            if col in df.columns:
                question_scores = df[col].dropna()
                if len(question_scores) > 0:
                    avg_score = question_scores.mean()
                    if avg_score < 0.5:  # Questions avec moins de 50% de réussite
                        difficult_questions.append({
                            'number': i + 1,
                            'column': col,
                            'success_rate': float(avg_score * 100)
                        })
        
        stats['difficult_questions'] = sorted(difficult_questions, key=lambda x: x['success_rate'])[:5]
        
    except Exception as e:
        print(f"Erreur analyse statistiques: {e}")
    
    return stats

def get_scores_distribution(project_path):
    """Données pour le graphique de distribution des scores"""
    csv_file = os.path.join(project_path, 'exports', 'notes.csv')
    
    if not os.path.exists(csv_file):
        return {'labels': [], 'data': []}
    
    try:
        df = pd.read_csv(csv_file)
        
        if 'Note' in df.columns:
            scores = df['Note'].dropna()
            
            # Créer des bins pour l'histogramme
            bins = range(0, 21, 2)  # 0-2, 2-4, 4-6, ..., 18-20
            hist, bin_edges = pd.cut(scores, bins=bins, retbins=True, include_lowest=True).value_counts().sort_index(), bins
            
            labels = [f"{int(bins[i])}-{int(bins[i+1])}" for i in range(len(bins)-1)]
            data = [int(count) for count in hist[0]]
            
            return {
                'labels': labels,
                'data': data,
                'backgroundColor': ['rgba(102, 126, 234, 0.7)'] * len(data)
            }
    except Exception as e:
        print(f"Erreur distribution scores: {e}")
    
    return {'labels': [], 'data': []}

def get_questions_analysis(project_path):
    """Données pour l'analyse par question"""
    csv_file = os.path.join(project_path, 'exports', 'notes.csv')
    
    if not os.path.exists(csv_file):
        return {'labels': [], 'data': []}
    
    try:
        df = pd.read_csv(csv_file)
        
        question_cols = [col for col in df.columns if col.startswith('Q:')]
        
        if question_cols:
            labels = [f"Q{i+1}" for i in range(len(question_cols))]
            data = []
            
            for col in question_cols:
                if col in df.columns:
                    question_scores = df[col].dropna()
                    if len(question_scores) > 0:
                        success_rate = question_scores.mean() * 100
                        data.append(float(success_rate))
                    else:
                        data.append(0)
            
            return {
                'labels': labels,
                'data': data,
                'backgroundColor': [
                    'rgba(40, 167, 69, 0.7)' if score >= 70 else
                    'rgba(255, 193, 7, 0.7)' if score >= 50 else
                    'rgba(220, 53, 69, 0.7)'
                    for score in data
                ]
            }
    except Exception as e:
        print(f"Erreur analyse questions: {e}")
    
    return {'labels': [], 'data': []}

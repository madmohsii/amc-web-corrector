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

# Améliorations à ajouter au dashboard.py

def get_correction_statistics():
    """Calcule les statistiques globales de correction"""
    from app import AMC_PROJECTS_FOLDER
    
    stats = {
        'total_corrections': 0,
        'total_students_corrected': 0,
        'average_correction_time': 0,
        'most_difficult_questions': [],
        'correction_success_rate': 0,
        'recent_corrections': []
    }
    
    if not os.path.exists(AMC_PROJECTS_FOLDER):
        return stats
    
    correction_times = []
    all_difficult_questions = []
    successful_corrections = 0
    
    for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
        
        # Vérifier si le projet a été corrigé
        exports_path = os.path.join(project_path, 'exports')
        csv_file = os.path.join(exports_path, 'notes.csv')
        
        if os.path.exists(csv_file):
            stats['total_corrections'] += 1
            successful_corrections += 1
            
            try:
                # Analyser les résultats
                import pandas as pd
                df = pd.read_csv(csv_file)
                
                if not df.empty and 'Note' in df.columns:
                    stats['total_students_corrected'] += len(df)
                
                # Questions difficiles
                question_cols = [col for col in df.columns if col.startswith('Q:')]
                for i, col in enumerate(question_cols):
                    if col in df.columns:
                        question_scores = df[col].dropna()
                        if len(question_scores) > 0:
                            success_rate = question_scores.mean()
                            if success_rate < 0.5:  # Questions < 50% de réussite
                                all_difficult_questions.append({
                                    'project': project_folder,
                                    'question': i + 1,
                                    'success_rate': success_rate,
                                    'difficulty_score': 1 - success_rate
                                })
                
                # Temps de correction (estimation basée sur les métadonnées)
                info_file = os.path.join(project_path, 'project_info.json')
                if os.path.exists(info_file):
                    with open(info_file, 'r') as f:
                        project_info = json.load(f)
                    
                    # Estimer le temps basé sur la taille du projet
                    uploads_path = os.path.join(project_path, 'uploads')
                    if os.path.exists(uploads_path):
                        file_count = len([f for f in os.listdir(uploads_path) 
                                        if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png'))])
                        estimated_time = file_count * 2  # 2 minutes par fichier (estimation)
                        correction_times.append(estimated_time)
                
            except Exception as e:
                continue
    
    # Calculer les moyennes
    if correction_times:
        stats['average_correction_time'] = sum(correction_times) / len(correction_times)
    
    if stats['total_corrections'] > 0:
        stats['correction_success_rate'] = (successful_corrections / stats['total_corrections']) * 100
    
    # Top des questions difficiles
    all_difficult_questions.sort(key=lambda x: x['difficulty_score'], reverse=True)
    stats['most_difficult_questions'] = all_difficult_questions[:10]
    
    return stats

def get_project_correction_status(project_path):
    """Détermine le statut de correction d'un projet"""
    status = {
        'has_questionnaire': False,
        'has_scans': False,
        'is_corrected': False,
        'correction_quality': 'unknown',
        'student_count': 0,
        'average_score': 0,
        'needs_attention': False,
        'last_correction': None
    }
    
    # Vérifier questionnaire
    if os.path.exists(os.path.join(project_path, 'questionnaire.tex')):
        status['has_questionnaire'] = True
    
    # Vérifier scans
    uploads_path = os.path.join(project_path, 'uploads')
    if os.path.exists(uploads_path):
        scan_files = [f for f in os.listdir(uploads_path) 
                     if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png', '.tiff'))]
        status['has_scans'] = len(scan_files) > 0
    
    # Vérifier correction
    csv_file = os.path.join(project_path, 'exports', 'notes.csv')
    if os.path.exists(csv_file):
        status['is_corrected'] = True
        
        try:
            import pandas as pd
            df = pd.read_csv(csv_file)
            
            if not df.empty and 'Note' in df.columns:
                scores = df['Note'].dropna()
                status['student_count'] = len(scores)
                status['average_score'] = float(scores.mean())
                
                # Déterminer la qualité
                if status['average_score'] > 15:
                    status['correction_quality'] = 'excellent'
                elif status['average_score'] > 10:
                    status['correction_quality'] = 'good'
                elif status['average_score'] > 5:
                    status['correction_quality'] = 'average'
                else:
                    status['correction_quality'] = 'poor'
                    status['needs_attention'] = True
                
                # Vérifier anomalies
                std_score = scores.std()
                if std_score < 1 or status['average_score'] < 3:
                    status['needs_attention'] = True
            
            # Date de dernière correction
            status['last_correction'] = datetime.fromtimestamp(
                os.path.getmtime(csv_file)
            ).isoformat()
            
        except Exception as e:
            status['needs_attention'] = True
    
    return status

def generate_correction_report():
    """Génère un rapport global des corrections"""
    from app import AMC_PROJECTS_FOLDER
    
    report = {
        'summary': get_correction_statistics(),
        'projects': [],
        'alerts': [],
        'recommendations': [],
        'generated_at': datetime.now().isoformat()
    }
    
    if not os.path.exists(AMC_PROJECTS_FOLDER):
        return report
    
    projects_needing_attention = []
    
    for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
        info_file = os.path.join(project_path, 'project_info.json')
        
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    project_info = json.load(f)
                
                project_status = get_project_correction_status(project_path)
                
                project_data = {
                    'name': project_info['name'],
                    'id': project_folder,
                    'created': project_info['created'],
                    'status': project_status
                }
                
                report['projects'].append(project_data)
                
                # Détecter les alertes
                if project_status['needs_attention']:
                    projects_needing_attention.append(project_data)
                
                if project_status['has_questionnaire'] and project_status['has_scans'] and not project_status['is_corrected']:
                    report['alerts'].append({
                        'type': 'ready_for_correction',
                        'project': project_info['name'],
                        'message': 'Projet prêt pour correction automatique'
                    })
                
                if project_status['is_corrected'] and project_status['correction_quality'] == 'poor':
                    report['alerts'].append({
                        'type': 'poor_results',
                        'project': project_info['name'],
                        'message': f'Résultats faibles (moyenne: {project_status["average_score"]:.1f})'
                    })
                
            except Exception as e:
                continue
    
    # Générer des recommandations
    if len(projects_needing_attention) > 0:
        report['recommendations'].append(
            f'{len(projects_needing_attention)} projet(s) nécessitent une attention particulière'
        )
    
    if report['summary']['correction_success_rate'] < 80:
        report['recommendations'].append(
            'Taux de réussite des corrections faible - vérifiez la qualité des scans'
        )
    
    if report['summary']['average_correction_time'] > 10:
        report['recommendations'].append(
            'Temps de correction élevé - considérez l\'optimisation des images'
        )
    
    return report

# Nouvelles routes pour le dashboard amélioré
def register_advanced_dashboard_routes(app, AMC_PROJECTS_FOLDER):
    """Enregistre les routes avancées du dashboard"""
    
    @app.route('/api/dashboard/correction-stats')
    def api_correction_stats():
        """API pour les statistiques de correction"""
        return jsonify(get_correction_statistics())
    
    @app.route('/api/dashboard/correction-report')
    def api_correction_report():
        """API pour le rapport complet de correction"""
        return jsonify(generate_correction_report())
    
    @app.route('/api/dashboard/project-status/<project_id>')
    def api_project_status(project_id):
        """API pour le statut détaillé d'un projet"""
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_id)
        if os.path.exists(project_path):
            return jsonify(get_project_correction_status(project_path))
        else:
            return jsonify({'error': 'Projet non trouvé'}), 404
    
    @app.route('/dashboard/advanced')
    def advanced_dashboard():
        """Dashboard avancé avec focus sur la correction"""
        correction_report = generate_correction_report()
        return render_template('advanced_dashboard.html', report=correction_report)

# Fonctions utilitaires pour l'analyse avancée
def analyze_correction_patterns():
    """Analyse les patterns de correction pour optimisation"""
    from app import AMC_PROJECTS_FOLDER
    
    patterns = {
        'common_errors': [],
        'optimization_suggestions': [],
        'quality_trends': {},
        'processing_efficiency': {}
    }
    
    # Analyser les erreurs communes
    error_counts = defaultdict(int)
    
    for project_folder in os.listdir(AMC_PROJECTS_FOLDER):
        project_path = os.path.join(AMC_PROJECTS_FOLDER, project_folder)
        
        # Chercher les logs d'erreur dans les métadonnées
        stats_file = os.path.join(project_path, 'exports', 'statistics.json')
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
                
                # Analyser les erreurs d'analyse
                analysis_stats = stats.get('analysis', {})
                if analysis_stats.get('unreadable_papers', 0) > 0:
                    error_counts['unreadable_papers'] += 1
                
                if analysis_stats.get('missing_student_codes', 0) > 0:
                    error_counts['missing_codes'] += 1
                
            except Exception:
                continue
    
    # Convertir en suggestions
    for error_type, count in error_counts.items():
        if count > 0:
            if error_type == 'unreadable_papers':
                patterns['optimization_suggestions'].append(
                    f'{count} projets avec copies illisibles - améliorer qualité scan'
                )
            elif error_type == 'missing_codes':
                patterns['optimization_suggestions'].append(
                    f'{count} projets avec codes manquants - sensibiliser étudiants'
                )
    
    return patterns

def get_system_performance_metrics():
    """Récupère les métriques de performance du système"""
    metrics = {
        'total_processing_time': 0,
        'average_time_per_student': 0,
        'success_rate': 0,
        'error_rate': 0,
        'most_efficient_settings': {},
        'bottlenecks': []
    }
    
    # Ces métriques pourraient être collectées via des logs
    # ou des mesures en temps réel lors des corrections
    
    return metrics

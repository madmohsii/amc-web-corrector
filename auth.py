# auth.py - Système d'authentification
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

auth_bp = Blueprint('auth', __name__)
USER_DB = 'amc_users.db'

class User:
    def __init__(self, id, username, email, role='teacher'):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

def get_user_by_id(user_id):
    """Récupérer un utilisateur par ID"""
    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, role FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect(USER_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role, password_hash FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[4], password):
            user = User(user_data[0], user_data[1], user_data[2], user_data[3])
            login_user(user)
            flash(f'Connexion réussie ! Bienvenue {user.username}', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        
        if len(username) < 3:
            flash('Le nom d\'utilisateur doit contenir au moins 3 caractères', 'danger')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères', 'danger')
            return render_template('auth/register.html')
        
        conn = sqlite3.connect(USER_DB)
        cursor = conn.cursor()
        
        try:
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, 'teacher'))
            
            conn.commit()
            user_id = cursor.lastrowid
            
            user = User(user_id, username, email, 'teacher')
            login_user(user)
            
            flash(f'Compte créé avec succès ! Bienvenue {username}', 'success')
            return redirect(url_for('dashboard'))
            
        except sqlite3.IntegrityError:
            flash('Nom d\'utilisateur ou email déjà utilisé', 'danger')
        finally:
            conn.close()
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'Déconnexion réussie. À bientôt {username} !', 'info')
    return redirect(url_for('auth.login'))

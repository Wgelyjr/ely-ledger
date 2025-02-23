from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    entries = db.relationship('JournalEntry', backref='author', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    theme = db.Column(db.String(50), default='light')
    entries_per_page = db.Column(db.Integer, default=10)

class JournalEntry(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    mood = db.Column(db.String(50))
    tags = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'mood': self.mood,
            'tags': self.tags,
            'user_id': self.user_id
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        settings = UserSettings(user=user)
        
        db.session.add(user)
        db.session.add(settings)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    if request.method == 'POST':
        settings = current_user.settings
        settings.theme = request.form.get('theme', 'light')
        settings.entries_per_page = int(request.form.get('entries_per_page', 10))
        db.session.commit()
        flash('Settings updated successfully')
        return redirect(url_for('user_settings'))
    return render_template('settings.html')

@app.route('/')
@login_required
def index():
    entries = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.created_at.desc()).all()
    return render_template('index.html', entries=entries)

@app.route('/entry/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    if request.method == 'POST':
        entry = JournalEntry(
            title=request.form['title'],
            content=request.form['content'],
            mood=request.form.get('mood'),
            tags=request.form.get('tags'),
            user_id=current_user.id
        )
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('new_entry.html')

@app.route('/entry/<int:id>')
@login_required
def view_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    return render_template('view_entry.html', entry=entry)

@app.route('/entry/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    if request.method == 'POST':
        entry.title = request.form['title']
        entry.content = request.form['content']
        entry.mood = request.form.get('mood')
        entry.tags = request.form.get('tags')
        db.session.commit()
        return redirect(url_for('view_entry', id=entry.id))
    return render_template('edit_entry.html', entry=entry)

@app.route('/entry/<int:id>/delete', methods=['POST'])
@login_required
def delete_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/api/search')
@login_required
def search_entries():
    query = request.args.get('q', '')
    entries = JournalEntry.query.filter(
        db.and_(
            JournalEntry.user_id == current_user.id,
            db.or_(
                JournalEntry.title.ilike(f'%{query}%'),
                JournalEntry.content.ilike(f'%{query}%'),
                JournalEntry.tags.ilike(f'%{query}%')
            )
        )
    ).order_by(JournalEntry.created_at.desc()).all()
    return jsonify([entry.to_dict() for entry in entries])

@app.route('/api/settings/theme', methods=['POST'])
@login_required
def update_theme():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    theme = request.json.get('theme')
    if theme not in ['light', 'dark']:
        return jsonify({'error': 'Invalid theme'}), 400

    current_user.settings.theme = theme
    db.session.commit()
    return jsonify({'theme': theme})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    mood = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    ai_summary = db.Column(db.Text)  # For future AI summarization feature

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'mood': self.mood,
            'tags': self.tags,
            'ai_summary': self.ai_summary
        }

@app.route('/')
def index():
    entries = JournalEntry.query.order_by(JournalEntry.created_at.desc()).all()
    return render_template('index.html', entries=entries)

@app.route('/entry/new', methods=['GET', 'POST'])
def new_entry():
    if request.method == 'POST':
        entry = JournalEntry(
            title=request.form['title'],
            content=request.form['content'],
            mood=request.form.get('mood'),
            tags=request.form.get('tags')
        )
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('new_entry.html')

@app.route('/entry/<int:id>')
def view_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    return render_template('view_entry.html', entry=entry)

@app.route('/entry/<int:id>/edit', methods=['GET', 'POST'])
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
def delete_entry(id):
    entry = JournalEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('index'))

# API endpoints for future AI features
@app.route('/api/entries')
def api_entries():
    entries = JournalEntry.query.order_by(JournalEntry.created_at.desc()).all()
    return jsonify([entry.to_dict() for entry in entries])

@app.route('/api/entry/<int:id>/summary', methods=['POST'])
def generate_summary(id):
    # Placeholder for future AI summary generation
    return jsonify({'message': 'AI summary generation coming soon'})

@app.route('/api/search')
def search_entries():
    # Placeholder for future AI-powered search
    query = request.args.get('q', '')
    return jsonify({'message': 'AI-powered search coming soon', 'query': query})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0")

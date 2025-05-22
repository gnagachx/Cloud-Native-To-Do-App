from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime
import re
import bleach
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# SQLite Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Task Model
class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    due_date = db.Column(db.String(10))  # YYYY-MM-DD, optional
    category = db.Column(db.String(50), default='General')
    type = db.Column(db.String(20), default='task')  # 'task' or 'daily_goal'
    notes = db.Column(db.Text)  # Notes field

# Helper function to render notes with clickable hyperlinks
def render_notes(notes):
    if not notes:
        return ''
    try:
        # Replace [text](url) with <a> tags
        pattern = r'\[([^\]]+)\]\((https?://[^\s)]+)\)'
        html = re.sub(pattern, r'<a href="\2" target="_blank">\1</a>', notes)
        logger.debug(f"Processed HTML: {html}")
        
        # Sanitize HTML
        allowed_tags = ['a']
        allowed_attributes = {'a': ['href', 'target']}
        cleaned_html = bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=['http', 'https']
        )
        logger.debug(f"Cleaned HTML: {cleaned_html}")
        
        # Wrap in <p> if no block-level tags (for consistent styling)
        if not cleaned_html.startswith('<p>'):
            cleaned_html = f'<p>{cleaned_html}</p>'
        
        # Verify links are present
        if '<a href=' not in cleaned_html and '[http' in notes:
            logger.warning(f"Links not rendered in notes: {notes}")
            return f'<p>{notes}</p>'
        return cleaned_html
    except Exception as e:
        logger.error(f"Error rendering notes: {notes}, Error: {str(e)}")
        return f'<p>{notes}</p>'

# Create database tables and initialize default daily goals
with app.app_context():
    db.create_all()
    today = datetime.now().strftime('%Y-%m-%d')
    default_goals = [
        {'title': 'Learning Spanish', 'notes': 'Practice on [Duolingo](https://www.duolingo.com)'},
        {'title': 'Completed Python 100 pages', 'notes': 'Read [Python Docs](https://docs.python.org/3/)'},
        {'title': 'Prepared DevOps Interview questions', 'notes': 'Review [AWS Guide](https://aws.amazon.com)'}
    ]
    for goal in default_goals:
        if not Task.query.filter_by(type='daily_goal', title=goal['title'], created_date=today).first():
            task_id = str(uuid.uuid4())
            task = Task(
                id=task_id,
                title=goal['title'],
                created_date=today,
                type='daily_goal',
                notes=goal['notes']
            )
            db.session.add(task)
    db.session.commit()

# API Routes
@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        title=data['title'],
        created_date=datetime.now().strftime('%Y-%m-%d'),
        due_date=data.get('due_date'),
        category=data.get('category', 'General'),
        type=data.get('type', 'task'),
        notes=data.get('notes')
    )
    db.session.add(task)
    db.session.commit()
    logger.debug(f"API Added {task.type}: {task.__dict__}")
    return jsonify({
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'created_date': task.created_date,
        'due_date': task.due_date,
        'category': task.category,
        'type': task.type,
        'notes': task.notes
    }), 201

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    date_filter = request.args.get('date')
    type_filter = request.args.get('type', 'task')
    query = Task.query.filter_by(type=type_filter)
    if date_filter:
        query = query.filter_by(created_date=date_filter)
    tasks = [{
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'created_date': task.created_date,
        'due_date': task.due_date,
        'category': task.category,
        'type': task.type,
        'notes': task.notes
    } for task in query.all()]
    logger.debug(f"API Listing {type_filter}s: {tasks}")
    return jsonify(tasks), 200

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify({
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'created_date': task.created_date,
        'due_date': task.due_date,
        'category': task.category,
        'type': task.type,
        'notes': task.notes
    }), 200

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    data = request.get_json()
    if 'title' in data:
        task.title = data['title']
    if 'completed' in data:
        task.completed = data['completed']
    if 'due_date' in data:
        task.due_date = data['due_date']
    if 'category' in data:
        task.category = data['category']
    if 'notes' in data:
        task.notes = data['notes']
    db.session.commit()
    logger.debug(f"API Updated {task.type}: {task.__dict__}")
    return jsonify({
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'created_date': task.created_date,
        'due_date': task.due_date,
        'category': task.category,
        'type': task.type,
        'notes': task.notes
    }), 200

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    logger.debug(f"API Deleted {task.type}: {task.__dict__}")
    return jsonify({'message': 'Task deleted'}), 200

# UI Routes
@app.route('/')
def index():
    date_filter = request.args.get('date')
    goal_date_filter = request.args.get('goal_date')
    search_query = request.args.get('search')
    sort_by = request.args.get('sort', 'created_date')

    # Tasks
    task_query = Task.query.filter_by(type='task')
    if date_filter:
        task_query = task_query.filter_by(created_date=date_filter)
    if search_query:
        task_query = task_query.filter(Task.title.ilike(f'%{search_query}%'))
    if sort_by == 'due_date':
        task_query = task_query.order_by(Task.due_date)
    elif sort_by == 'category':
        task_query = task_query.order_by(Task.category)
    else:
        task_query = task_query.order_by(Task.created_date)
    tasks = task_query.all()

    # Daily Goals
    goal_query = Task.query.filter_by(type='daily_goal')
    if goal_date_filter:
        goal_query = goal_query.filter_by(created_date=goal_date_filter)
    goals = goal_query.all()

    # Debug data
    logger.debug(f"Tasks type: {type(tasks)}, Length: {len(tasks)}")
    logger.debug(f"Goals type: {type(goals)}, Length: {len(goals)}")
    logger.debug(f"Rendering tasks: {[{'id': t.id, 'title': t.title} for t in tasks]}")
    logger.debug(f"Rendering daily goals: {[{'id': g.id, 'title': g.title} for g in goals]}")

    return render_template(
        'index.html',
        tasks=tasks,
        goals=goals,
        selected_date=date_filter,
        selected_goal_date=goal_date_filter,
        search_query=search_query,
        sort_by=sort_by,
        now=datetime.now(),
        render_notes=render_notes
    )

@app.route('/add', methods=['POST'])
def add_task():
    title = request.form.get('title')
    created_date = request.form.get('created_date') or datetime.now().strftime('%Y-%m-%d')
    due_date = request.form.get('due_date')
    category = request.form.get('category', 'General')
    type_ = request.form.get('type', 'task')
    notes = request.form.get('notes')
    if title:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title,
            created_date=created_date,
            due_date=due_date,
            category=category,
            type=type_,
            notes=notes
        )
        db.session.add(task)
        db.session.commit()
        logger.debug(f"Added {type_}: {task.__dict__}")
    else:
        logger.debug("No title provided")
    if type_ == 'daily_goal':
        return redirect(url_for('index', goal_date=created_date))
    return redirect(url_for('index', date=created_date))

@app.route('/toggle/<task_id>')
def toggle_task(task_id):
    task = Task.query.get(task_id)
    date_filter = request.args.get('date')
    goal_date_filter = request.args.get('goal_date')
    if task:
        task.completed = not task.completed
        db.session.commit()
        logger.debug(f"Toggled {task.type}: {task.__dict__}")
    if task and task.type == 'daily_goal':
        return redirect(url_for('index', goal_date=goal_date_filter, date=date_filter))
    return redirect(url_for('index', date=date_filter))

@app.route('/edit/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form.get('title')
        due_date = request.form.get('due_date')
        category = request.form.get('category')
        notes = request.form.get('notes')
        if title:
            task.title = title
            task.due_date = due_date
            task.category = category
            task.notes = notes
            db.session.commit()
            logger.debug(f"Edited {task.type}: {task.__dict__}")
        if task.type == 'daily_goal':
            return redirect(url_for('index', goal_date=task.created_date))
        return redirect(url_for('index', date=task.created_date))
    return render_template('edit.html', task=task)

@app.route('/delete/<task_id>')
def delete_task_ui(task_id):
    task = Task.query.get(task_id)
    date_filter = request.args.get('date')
    goal_date_filter = request.args.get('goal_date')
    if task:
        db.session.delete(task)
        db.session.commit()
        logger.debug(f"Deleted {task.type}: {task.__dict__}")
    if task and task.type == 'daily_goal':
        return redirect(url_for('index', goal_date=goal_date_filter, date=date_filter))
    return redirect(url_for('index', date=date_filter))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
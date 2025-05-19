from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

app = Flask(__name__)

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

# Create database tables
with app.app_context():
    db.create_all()

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
        category=data.get('category', 'General')
    )
    db.session.add(task)
    db.session.commit()
    print(f"API Added task: {task.__dict__}")  # Debug
    return jsonify({
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'created_date': task.created_date,
        'due_date': task.due_date,
        'category': task.category
    }), 201

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    date_filter = request.args.get('date')
    query = Task.query
    if date_filter:
        query = query.filter_by(created_date=date_filter)
    tasks = [{
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'created_date': task.created_date,
        'due_date': task.due_date,
        'category': task.category
    } for task in query.all()]
    print(f"API Listing tasks: {tasks}")  # Debug
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
        'category': task.category
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
    db.session.commit()
    print(f"API Updated task: {task.__dict__}")  # Debug
    return jsonify({
        'id': task.id,
        'title': task.title,
        'completed': task.completed,
        'created_date': task.created_date,
        'due_date': task.due_date,
        'category': task.category
    }), 200

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    print(f"API Deleted task: {task.__dict__}")  # Debug
    return jsonify({'message': 'Task deleted'}), 200

# UI Routes
@app.route('/')
def index():
    date_filter = request.args.get('date')
    search_query = request.args.get('search')
    sort_by = request.args.get('sort', 'created_date')
    query = Task.query
    if date_filter:
        query = query.filter_by(created_date=date_filter)
    if search_query:
        query = query.filter(Task.title.ilike(f'%{search_query}%'))
    if sort_by == 'due_date':
        query = query.order_by(Task.due_date)
    if sort_by == 'notes':
        query = query.order_by(Task.notes)
    elif sort_by == 'category':
        query = query.order_by(Task.category)
    else:
        query = query.order_by(Task.created_date)
    tasks = query.all()
    print(f"Rendering tasks: {[{t.id: t.title} for t in tasks]}")  # Debug
    return render_template(
        'index.html',
        tasks=tasks,
        selected_date=date_filter,
        search_query=search_query,
        sort_by=sort_by,
        now=datetime.now()
    )

@app.route('/add', methods=['POST'])
def add_task():
    title = request.form.get('title')
    created_date = request.form.get('created_date') or datetime.now().strftime('%Y-%m-%d')
    due_date = request.form.get('due_date')
    category = request.form.get('category', 'General')
    if title:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title,
            created_date=created_date,
            due_date=due_date,
            category=category
        )
        db.session.add(task)
        db.session.commit()
        print(f"Added task: {task.__dict__}")  # Debug
    else:
        print("No title provided")  # Debug
    return redirect(url_for('index', date=created_date))

@app.route('/toggle/<task_id>')
def toggle_task(task_id):
    task = Task.query.get(task_id)
    date_filter = request.args.get('date')
    if task:
        task.completed = not task.completed
        db.session.commit()
        print(f"Toggled task: {task.__dict__}")  # Debug
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
        if title:
            task.title = title
            task.due_date = due_date
            task.notes = notes
            task.category = category
            db.session.commit()
            print(f"Edited task: {task.__dict__}")  # Debug
        return redirect(url_for('index', date=task.created_date))
    return render_template('edit.html', task=task)

@app.route('/delete/<task_id>')
def delete_task_ui(task_id):
    date_filter = request.args.get('date')
    task = Task.query.get(task_id)
    if task:
        db.session.delete(task)
        db.session.commit()
        print(f"Deleted task: {task.__dict__}")  # Debug
    return redirect(url_for('index', date=date_filter))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
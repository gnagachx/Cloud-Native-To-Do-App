from flask import Flask, request, jsonify, render_template, redirect, url_for

import uuid

app = Flask(__name__)


tasks = {}  # In-memory storage

# API Routes
@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    task_id = str(uuid.uuid4())
    tasks[task_id] = {'id': task_id, 'title': data['title'], 'completed': False}
    return jsonify(tasks[task_id]), 201

@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    return jsonify(list(tasks.values())), 200

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task), 200

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    data = request.get_json()
    if 'title' in data:
        task['title'] = data['title']
    if 'completed' in data:
        task['completed'] = data['completed']
    return jsonify(task), 200

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    deleted_task = tasks.pop(task_id)
    return jsonify(deleted_task), 200

# UI Routes
@app.route('/')
def index():
    return render_template('index.html', tasks=tasks.values())

@app.route('/add', methods=['POST'])
def add_task():
    title = request.form.get('title')
    if title:
        task_id = str(uuid.uuid4())
        tasks[task_id] = {'id': task_id, 'title': title, 'completed': False}
    return redirect(url_for('index'))

@app.route('/toggle/<task_id>')
def toggle_task(task_id):
    task = tasks.get(task_id)
    if task:
        task['completed'] = not task['completed']
    return redirect(url_for('index'))

@app.route('/edit/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task = tasks.get(task_id)
    if not task:
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form.get('title')
        if title:
            task['title'] = title
        return redirect(url_for('index'))
    return render_template('edit.html', task=task)

@app.route('/delete/<task_id>')
def delete_task_ui(task_id):
    tasks.pop(task_id, None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
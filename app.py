import os
import json
import shutil
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Helper function to load/save JSON
def load_json(filename):
    with open(os.path.join(DATA_FOLDER, filename), 'r') as f:
        return json.load(f)

def save_json(filename, data):
    with open(os.path.join(DATA_FOLDER, filename), 'w') as f:
        json.dump(data, f, indent=4)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files', methods=['GET', 'POST'])
def file_manager():
    if request.method == 'POST':
        action = request.form.get('action')
        target_dir = request.form.get('target_dir', '')
        full_target_dir = os.path.join(app.config['UPLOAD_FOLDER'], target_dir)
        
        if action == 'upload':
            if 'file' in request.files:
                file = request.files['file']
                if file.filename:
                    filename = secure_filename(file.filename)
                    os.makedirs(full_target_dir, exist_ok=True)
                    file.save(os.path.join(full_target_dir, filename))
        
        elif action == 'create_dir':
            new_dir = request.form.get('new_dir')
            if new_dir:
                os.makedirs(os.path.join(full_target_dir, secure_filename(new_dir)), exist_ok=True)
                
        elif action == 'delete':
            target_path = request.form.get('target_path')
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], target_path)
            if os.path.exists(full_path):
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
        return redirect(url_for('file_manager'))

    # Generate file tree
    tree = []
    # Using os.walk to get a structured flow
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        # Calculate depth by counting separators in the relative path
        rel_path = os.path.relpath(root, app.config['UPLOAD_FOLDER'])
        
        # level 0 is root, level 1 is first subfolder, etc.
        level = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
        
        # Add the directory itself
        display_name = os.path.basename(root) if rel_path != '.' else "uploads/"
        tree.append({
            "path": "" if rel_path == '.' else rel_path, 
            "type": "dir", 
            "name": display_name, 
            "level": level
        })

        # Add files within this directory
        for file in files:
            file_rel_path = os.path.join(rel_path, file) if rel_path != '.' else file
            tree.append({
                "path": file_rel_path, 
                "type": "file", 
                "name": file, 
                "level": level + 1
            })

    # Get list of directories for the upload dropdown
    directories = [''] + [os.path.relpath(r, app.config['UPLOAD_FOLDER']) for r, d, f in os.walk(app.config['UPLOAD_FOLDER']) if os.path.relpath(r, app.config['UPLOAD_FOLDER']) != '.']

    return render_template('file_manager.html', tree=tree, directories=directories)

@app.route('/editor/<json_file>', methods=['GET', 'POST'])
def editor(json_file):
    if json_file not in ['config.json', 'status.json']:
        return "Invalid file", 400
        
    if request.method == 'POST':
        try:
            new_data = json.loads(request.form.get('json_data'))
            save_json(json_file, new_data)
            return redirect(url_for('editor', json_file=json_file))
        except json.JSONDecodeError:
            return "Invalid JSON format!", 400
            
    data = load_json(json_file)
    return render_template('json_editor.html', filename=json_file, json_data=json.dumps(data, indent=4))

@app.route('/vtt')
def vtt():
    return render_template('vtt.html')

# --- API ENDPOINTS FOR THE VTT ---

@app.route('/api/config')
def get_config():
    return jsonify(load_json('config.json'))

@app.route('/api/status')
def get_status():
    return jsonify(load_json('status.json'))

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status():
    if request.method == 'POST':
        # Receive updated JSON from the VTT page
        new_data = request.json
        # save_json automatically formats it with indent=4 (pretty print)
        save_json('status.json', new_data)
        return jsonify({"status": "success"})
    
    # GET request behavior
    return jsonify(load_json('status.json'))

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
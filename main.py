import os
import uuid
import datetime
import base64
import requests
import tempfile
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, session, url_for
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 配置
app.secret_key = os.environ.get("SECRET_KEY", "my-fixed-secret-key-2026")
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=30)
)

# 环境变量
ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASS = os.environ.get("ADMIN_PASS")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "vercel")

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
CDN_BASE = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@{GITHUB_BRANCH}"
CACHE_DIR = tempfile.gettempdir()

def format_size(size):
    if size is None: return "未知"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024: return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if ADMIN_USER and ADMIN_PASS and not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 路由逻辑 ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session.permanent = True; session['logged_in'] = True; return redirect('/')
        return render_template('login.html', error="密码错误")
    return render_template('login.html')

@app.route('/logout')
def logout(): session.pop('logged_in', None); return redirect('/login')

@app.route('/')
@login_required
def home():
    if not GITHUB_TOKEN or not GITHUB_REPO: return "GitHub Token or Repo not set in Env!"
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        # 加时间戳防缓存
        r = requests.get(f"{GITHUB_API_BASE}?ref={GITHUB_BRANCH}&t={datetime.datetime.now().timestamp()}", headers=headers)
        
        if r.status_code != 200: 
            return f"连接 GitHub 失败: {r.status_code} <br> {r.text}"
            
        files_data = r.json()
        images = []
        if isinstance(files_data, list):
            for item in files_data:
                if item['type'] == 'file' and item['name'].lower().endswith(('.png','.jpg','.jpeg','.gif','.webp','.bmp')):
                    raw_url = f"{CDN_BASE}/{item['name']}"
                    images.append({
                        "name": item['name'],
                        "raw_url": raw_url,
                        "view_url": f"/view/{item['name']}",
                        "real_url": raw_url,
                        "size_fmt": format_size(item['size'])
                    })
        images.reverse()
        # 这里直接调用独立的 HTML 文件
        return render_template('index.html', images=images)
    except Exception as e: return f"System Error: {str(e)}"

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    files = request.files.getlist('files')
    count = 0
    errors = []
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    for file in files:
        if not file.filename: continue
        ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
        name = f"{uuid.uuid4().hex[:4]}{ext}"
        try:
            file_content = base64.b64encode(file.read()).decode('utf-8')
            data = {"message": f"Up {name}", "content": file_content, "branch": GITHUB_BRANCH}
            r = requests.put(f"{GITHUB_API_BASE}/{name}", json=data, headers=headers)
            if r.status_code in [200, 201]: count += 1
            else: errors.append(f"{file.filename}: {r.status_code}")
        except Exception as e: errors.append(str(e))
    
    if count > 0: return jsonify({"status": "success", "count": count})
    else: return jsonify({"status": "error", "error": str(errors)})

@app.route('/delete', methods=['POST'])
@login_required
def delete_file():
    name = request.form.get('filename')
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(f"{GITHUB_API_BASE}/{name}?ref={GITHUB_BRANCH}", headers=headers)
        if r.status_code != 200: return jsonify({"error": "File not found"})
        sha = r.json()['sha']
        data = {"message": f"Del {name}", "sha": sha, "branch": GITHUB_BRANCH}
        requests.delete(f"{GITHUB_API_BASE}/{name}", json=data, headers=headers)
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)})

@app.route('/view/<path:filename>')
def view_image(filename):
    real_url = f"{CDN_BASE}/{filename}"
    return f'<html><body style="margin:0;background:#000;display:flex;justify-content:center;align-items:center;height:100vh"><img src="{real_url}" style="max-width:100%;max-height:100%"></body></html>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)

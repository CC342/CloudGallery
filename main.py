import os
import datetime
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
GITHUB_REPO= vercel

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"

# 🔥 核心修改：链接前缀留空，或者设为你的 Worker 域名 + /file
# 建议：留空字符串，这样前端会自动拼接当前域名
CDN_BASE = "/file" 

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

# ================= 路由 =================

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
    if not GITHUB_TOKEN or not GITHUB_REPO: return "错误: 环境变量未设置"
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(f"{GITHUB_API_BASE}?ref={GITHUB_BRANCH}&t={datetime.datetime.now().timestamp()}", headers=headers)
        
        if r.status_code != 200: return f"连接 GitHub 失败: {r.status_code} <br> {r.text}"
            
        files_data = r.json()
        images = []
        if isinstance(files_data, list):
            for item in files_data:
                if item['type'] == 'file' and item['name'].lower().endswith(('.png','.jpg','.jpeg','.gif','.webp','.bmp')):
                    # 这里生成的链接就是 /file/xxx.jpg
                    # 浏览器会自动拼成 https://你的域名.com/file/xxx.jpg
                    raw_url = f"{CDN_BASE}/{item['name']}"
                    images.append({
                        "name": item['name'],
                        "raw_url": raw_url,
                        "view_url": f"/view/{item['name']}",
                        "size_fmt": format_size(item['size'])
                    })
        
        # 排序：文件名反转
        images.sort(key=lambda x: x['name'])
        images.reverse()
        
        config = {
            "token": GITHUB_TOKEN,
            "repo": GITHUB_REPO,
            "branch": GITHUB_BRANCH,
            "api_base": GITHUB_API_BASE
        }
        return render_template('index.html', images=images, config=config)
        
    except Exception as e: return f"System Error: {str(e)}"

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    # 后端不再处理上传，保留此接口防报错，实际走前端直传
    return jsonify({"status": "error", "error": "Use frontend upload"})

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
    # 预览也走 Worker 代理
    real_url = f"/file/{filename}"
    return f'<html><body style="margin:0;background:#000;display:flex;justify-content:center;align-items:center;height:100vh"><img src="{real_url}" style="max-width:100%;max-height:100%"></body></html>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)

import os
import datetime
import requests
import tempfile
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, session, url_for, render_template_string
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
GITHUB_BRANCH = "main"

# 🔥 新增：定义图片存放的文件夹名称
GITHUB_FOLDER = "images"

# API 基地址指向该文件夹
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"

# 代理前缀
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
        
        # 如果文件夹不存在(404)，说明还没传图，给个空列表
        if r.status_code == 404:
            files_data = []
        elif r.status_code != 200: 
            return f"连接 GitHub 失败: {r.status_code} <br> {r.text}"
        else:
            files_data = r.json()

        images = []
        if isinstance(files_data, list):
            for item in files_data:
                if item['type'] == 'file' and item['name'].lower().endswith(('.png','.jpg','.jpeg','.gif','.webp','.bmp')):
                    # 🔥 修改：构造链接时带上文件夹路径
                    # 最终链接类似: /file/images/xxxx.jpg
                    raw_url = f"{CDN_BASE}/{GITHUB_FOLDER}/{item['name']}"
                    
                    images.append({
                        "name": item['name'],
                        "raw_url": raw_url,
                        "view_url": f"/view/{item['name']}",
                        "size_fmt": format_size(item['size'])
                    })
        
        images.sort(key=lambda x: x['name'])
        images.reverse()
        
        config = {
            "token": GITHUB_TOKEN,
            "repo": GITHUB_REPO,
            "branch": GITHUB_BRANCH,
            "api_base": GITHUB_API_BASE # 这里传给前端的就是带 images 的 API 地址
        }
        
        # 读取 HTML 模板
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return render_template_string(html_content, images=images, config=config)
        
    except Exception as e: return f"System Error: {str(e)}"

# 这个接口虽然不用，但也更新一下防止报错
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    return jsonify({"status": "error", "error": "Use frontend upload"})

@app.route('/delete', methods=['POST'])
@login_required
def delete_file():
    name = request.form.get('filename') # 前端传来的只是文件名，如 abcd.jpg
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        # 🔥 修改：操作 API 时，加上文件夹路径
        target_path = f"{GITHUB_FOLDER}/{name}"
        
        # 1. 获取 SHA
        r = requests.get(f"{GITHUB_API_BASE}/{name}?ref={GITHUB_BRANCH}", headers=headers)
        if r.status_code != 200: return jsonify({"error": "File not found"})
        sha = r.json()['sha']
        
        # 2. 删除
        data = {"message": f"Del {target_path}", "sha": sha, "branch": GITHUB_BRANCH}
        # 注意：GitHub API 删除的 URL 必须包含完整路径
        del_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{target_path}"
        
        requests.delete(del_url, json=data, headers=headers)
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)})

@app.route('/view/<path:filename>')
def view_image(filename):
    # 🔥 修改：预览时也要加上文件夹路径
    real_url = f"/file/{GITHUB_FOLDER}/{filename}"
    return f'<html><body style="margin:0;background:#000;display:flex;justify-content:center;align-items:center;height:100vh"><img src="{real_url}" style="max-width:100%;max-height:100%"></body></html>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)

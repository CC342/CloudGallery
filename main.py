import os
import time
import uuid
import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template_string, redirect, session, url_for
from flask_cors import CORS
from huggingface_hub import HfApi, CommitOperationDelete
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = "my-fixed-secret-key-2026"
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=30)
)

HF_TOKEN = os.environ.get("HF_TOKEN")
DATASET_NAME = os.environ.get("DATASET_NAME")
SPACE_HOST = os.environ.get("SPACE_HOST", "localhost:7860")
BASE_URL = f"https://{SPACE_HOST}" if "localhost" not in SPACE_HOST else f"http://{SPACE_HOST}"
ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASS = os.environ.get("ADMIN_PASS")

if HF_TOKEN: api = HfApi(token=HF_TOKEN)
CACHE_DIR = "/app/cache"
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)

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

# 1. 登录页面
LOGIN_TEMPLATE = """<!DOCTYPE html><html><head><title>登录</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{margin:0;height:100vh;display:flex;justify-content:center;align-items:center;font-family:-apple-system,sans-serif;background:url('https://images.unsplash.com/photo-1519681393784-d120267933ba?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed;background-size:cover}.glass-box{width:300px;padding:40px 30px;text-align:center;background:rgba(255,255,255,0.1);backdrop-filter:blur(25px);-webkit-backdrop-filter:blur(25px);border-radius:24px;border:1px solid rgba(255,255,255,0.2);box-shadow:0 8px 32px 0 rgba(0,0,0,0.1);color:white}h2{margin:0 0 25px 0;font-weight:500}input{width:100%;padding:14px;margin:10px 0;border-radius:12px;border:1px solid rgba(255,255,255,0.3);background:rgba(255,255,255,0.15);color:white;outline:none;transition:0.3s;box-sizing:border-box}input:focus{background:rgba(255,255,255,0.25);border-color:rgba(255,255,255,0.8)}button{width:100%;padding:14px;margin-top:20px;background:rgba(255,255,255,0.9);color:#333;border:none;border-radius:12px;font-weight:bold;cursor:pointer;transition:0.3s}button:hover{background:white;transform:translateY(-2px)}.err{color:#ffcccc;background:rgba(255,0,0,0.2);padding:5px;border-radius:5px;font-size:14px;margin-bottom:10px}</style></head><body><div class="glass-box"><h2>CloudGallery</h2>{% if error %}<div class="err">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Username" required><input type="password" name="password" placeholder="Password" required><button type="submit">Sign In</button></form></div></body></html>"""

# 2. 全屏查看 (备用)
VIEW_TEMPLATE = """<!DOCTYPE html><html><head><title>查看</title><style>body{margin:0;background:#000;display:flex;justify-content:center;align-items:center;height:100vh;overflow:hidden}img{width:100%;height:100%;object-fit:contain}</style></head><body><img src="{{ real_url }}"></body></html>"""

# =========================================================
# 🎨 3. 主页模板 (V11.0 纯净白透版)
# =========================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的图床</title>
    <style>
        * { box-sizing: border-box; }
        :root { --primary: #3b82f6; --bg: #f8fafc; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            background-color: var(--bg); color: #333; margin: 0; padding: 20px; 
            overflow-x: hidden;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        .top-nav { display: flex; justify-content: flex-end; margin-bottom: 10px; }
        .logout-btn { text-decoration: none; color: #ef4444; font-size: 13px; padding: 6px 12px; background: white; border: 1px solid #fee2e2; border-radius: 20px; transition: 0.2s; }
        .logout-btn:hover { background: #fef2f2; border-color: #fecaca; }
        
        .upload-section { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; margin-bottom: 30px; margin-top: 10px; }
        .upload-wrapper { position: relative; display: inline-block; overflow: hidden; }
        .btn { background: white; border: 2px solid var(--primary); color: var(--primary); padding: 10px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.3s; }
        .btn:hover { background: var(--primary); color: white; }
        .upload-wrapper input { position: absolute; left: 0; top: 0; font-size: 100px; opacity: 0; cursor: pointer; }
        #status { margin-top: 15px; color: #666; font-size: 14px; }

        .gallery-header { display: flex; justify-content: space-between; margin-bottom: 20px; align-items: center; }
        .refresh-btn { background: none; border: none; cursor: pointer; color: #64748b; font-size: 14px; display: flex; align-items: center; gap: 5px; }
        .refresh-btn:hover { color: var(--primary); }
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05); position: relative; transition: 0.2s; }
        .card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        .img-container { height: 160px; overflow: hidden; background: #eee; display: flex; align-items: center; justify-content: center; cursor: zoom-in; }
        .img-container img { width: 100%; height: 100%; object-fit: cover; }
        .card-body { padding: 12px; display: flex; flex-direction: column; gap: 6px; }
        .file-name { font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: bold; }
        .meta-info { font-size: 10px; color: #999; display: flex; justify-content: space-between; }
        .copy-btn { background: #f1f5f9; border: none; padding: 6px; border-radius: 4px; color: #475569; font-size: 12px; cursor: pointer; width: 100%; margin-top: 5px; }
        .copy-btn:hover { background: #e2e8f0; color: #0f172a; }
        .copy-btn.primary { background: #eff6ff; color: #2563eb; }
        .delete-btn { position: absolute; top: 5px; right: 5px; background: rgba(255,255,255,0.9); color: red; border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; opacity: 0; font-weight: bold; transition: 0.2s; }
        .card:hover .delete-btn { opacity: 1; }

        /* ================= LIGHTBOX (白透版) ================= */
        .lightbox-overlay {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000;
            background-color: rgba(255, 255, 255, 0.4); 
            backdrop-filter: blur(25px); 
            -webkit-backdrop-filter: blur(25px);
            flex-direction: column; justify-content: center; align-items: center;
        }

        .lb-main { 
            flex: 1; width: 100%; display: flex; justify-content: center; align-items: center; 
            overflow: hidden; position: relative; 
        }
        
        .lb-img { 
            max-width: 70%; max-height: 70%; 
            object-fit: contain; transition: transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            cursor: grab; border-radius: 8px;
            box-shadow: 0 30px 80px rgba(0,0,0,0.25);
        }

        .floating-close { 
            position: absolute; top: 20px; right: 20px; 
            width: 40px; height: 40px; border-radius: 50%; 
            background: rgba(0,0,0,0.05); color: #333; 
            display: flex; justify-content: center; align-items: center; 
            font-size: 24px; cursor: pointer; z-index: 1020; transition:0.2s; 
        }
        .floating-close:hover { background: rgba(0,0,0,0.1); }

        .lb-bottom-container { 
            width: 100%; display: flex; justify-content: center; 
            position: absolute; bottom: 130px;
            pointer-events: none; z-index: 1010;
        }
        
        .lb-controls {
            background: rgba(255, 255, 255, 0.7); 
            backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px);
            padding: 8px 20px; border-radius: 50px; 
            border: 1px solid rgba(0,0,0,0.05); 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            display: flex; gap: 15px; pointer-events: auto; align-items: center;
        }
        .lb-ctl-btn { 
            background: transparent; border: none; 
            color: #333; 
            font-size: 16px; cursor: pointer; padding: 5px 10px; border-radius: 20px; transition: 0.2s; 
        }
        .lb-ctl-btn:hover { background: rgba(0,0,0,0.05); }
        .divider { width: 1px; background: rgba(0,0,0,0.1); height: 20px; }

        .filmstrip-container {
            position: absolute; bottom: 30px; width: 100%;
            display: flex; justify-content: center; z-index: 1005;
        }

        .filmstrip { 
            height: 70px; width: auto; max-width: 90vw;
            background: rgba(255, 255, 255, 0.6); 
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            border-radius: 35px; border: 1px solid rgba(255,255,255,0.5);
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            display: flex; align-items: center; gap: 12px; padding: 0 20px; 
            overflow-x: auto; scrollbar-width: none;
        }
        .filmstrip::-webkit-scrollbar { display: none; }
        
        .thumb { 
            width: 44px; height: 44px; border-radius: 10px; 
            object-fit: cover; cursor: pointer; flex-shrink: 0;
            opacity: 0.5; transform: scale(0.9); filter: grayscale(0.2);
            transition: all 0.3s ease; border: 2px solid transparent;
        }
        .thumb:hover { opacity: 0.9; }
        
        .thumb.active { 
            opacity: 1; filter: grayscale(0); transform: scale(1.1); 
            border: 2px solid #3b82f6; 
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
        }

        @media (max-width: 600px) { .gallery-grid { grid-template-columns: repeat(2, 1fr); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="top-nav"><a href="/logout" class="logout-btn">🔴 退出</a></div>
        <div class="upload-section">
            <h2 style="margin-top:0;">☁️ CloudGallery</h2>
            <div class="upload-wrapper">
                <button class="btn">＋ 上传图片 (多选)</button>
                <input type="file" id="fileInput" accept="image/*" multiple onchange="handleUpload()">
            </div>
            <div id="status">准备就绪</div>
        </div>
        <div class="gallery-header">
            <h3 style="margin:0">🖼️ 图片列表</h3>
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新</button>
        </div>
        <div class="gallery-grid">
            {% for img in images %}
            <div class="card" id="card-{{ loop.index0 }}">
                <div class="img-container" onclick="openViewer({{ loop.index0 }})">
                    <img src="{{ img.real_url }}" loading="lazy" onload="updateRes(this)">
                </div>
                <button class="delete-btn" onclick="deleteImage('{{ img.name }}', {{ loop.index0 }})">×</button>
                <div class="card-body">
                    <div class="file-name" title="{{ img.name }}">{{ img.name }}</div>
                    <div class="meta-info"><span>{{ img.size_fmt }}</span><span class="res-tag">...</span></div>
                    <button class="copy-btn primary" onclick="copyLink(this, '{{ img.view_url }}')">📋 复制链接</button>
                    <button class="copy-btn" onclick="copyMarkdown(this, '{{ img.name }}', '{{ img.real_url }}')">📝 复制 Markdown</button>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <div id="lightbox" class="lightbox-overlay" onclick="closeViewer(event)">
        <div class="floating-close" onclick="closeViewer()">×</div>
        
        <div class="lb-main">
            <img id="lb-img" class="lb-img" onclick="event.stopPropagation()">
        </div>

        <div class="lb-bottom-container">
            <div class="lb-controls" onclick="event.stopPropagation()">
                <button class="lb-ctl-btn" onclick="zoom(-0.2)" title="缩小">－</button>
                <button class="lb-ctl-btn" onclick="resetZoom()" title="1:1" style="font-size:14px">1:1</button>
                <button class="lb-ctl-btn" onclick="zoom(0.2)" title="放大">＋</button>
                <span class="divider"></span>
                <button class="lb-ctl-btn" onclick="copyCurrentLink()" title="复制链接">🔗</button>
            </div>
        </div>

        <div class="filmstrip-container">
            <div class="filmstrip" id="filmstrip" onclick="event.stopPropagation()"></div>
        </div>
    </div>

    <script>
        const galleryData = [
            {% for img in images %}
            { name: "{{img.name}}", url: "{{img.real_url}}", view_url: "{{img.view_url}}" },
            {% endfor %}
        ];
        let curIdx = 0, scale = 1;

        async function handleUpload() {
            const inp = document.getElementById('fileInput');
            if (!inp.files.length) return;
            document.getElementById('status').innerText = `🚀 上传 ${inp.files.length} 张...`;
            const fd = new FormData();
            for (let f of inp.files) fd.append('files', f);
            try {
                const res = await fetch('/upload', { method: 'POST', body: fd });
                const d = await res.json();
                if(d.status==='success') setTimeout(()=>location.reload(), 1000);
            } catch(e) {}
        }

        async function deleteImage(name, idx) {
            if(!confirm('删除？')) return;
            const fd = new FormData(); fd.append('filename', name);
            const res = await fetch('/delete', { method: 'POST', body: fd });
            if ((await res.json()).status === 'success') document.getElementById('card-'+idx).remove();
        }

        function openViewer(idx) {
            curIdx = idx;
            const lb = document.getElementById('lightbox');
            const fs = document.getElementById('filmstrip');
            fs.innerHTML = '';
            galleryData.forEach((img, i) => {
                const t = document.createElement('img');
                t.src = img.url; t.className = `thumb ${i===idx?'active':''}`;
                t.onclick = () => showImage(i);
                fs.appendChild(t);
            });
            lb.style.display = 'flex';
            setTimeout(() => lb.style.opacity = '1', 10);
            showImage(idx);
        }

        function showImage(idx) {
            curIdx = idx; scale = 1;
            const img = document.getElementById('lb-img');
            img.src = galleryData[idx].url;
            img.style.transform = `scale(1)`;
            document.querySelectorAll('.thumb').forEach((t, i) => {
                t.className = `thumb ${i===idx?'active':''}`;
                if(i===idx) t.scrollIntoView({behavior:"smooth", inline:"center"});
            });
        }

        function closeViewer(e) { 
            if(!e || e.target === e.currentTarget || e.target.classList.contains('floating-close')) {
                document.getElementById('lightbox').style.display = 'none'; 
            }
        }
        function zoom(d) { scale += d; if(scale<0.1) scale=0.1; document.getElementById('lb-img').style.transform = `scale(${scale})`; }
        function resetZoom() { scale = 1; document.getElementById('lb-img').style.transform = `scale(1)`; }
        function copyCurrentLink() { copyLink(null, galleryData[curIdx].view_url); alert('已复制'); }
        function updateRes(img) { if(img.naturalWidth) img.closest('.card').querySelector('.res-tag').innerText = img.naturalWidth+'x'+img.naturalHeight; }
        function copyLink(btn, txt) { navigator.clipboard.writeText(txt); if(btn){let t=btn.innerText;btn.innerText='✅';setTimeout(()=>btn.innerText=t,1500);} }
        function copyMarkdown(btn, n, u) { copyLink(btn, `![${n}](${u})`); }
        
        document.getElementById('lb-img').addEventListener('wheel', function(e) {
            e.preventDefault(); e.deltaY < 0 ? zoom(0.1) : zoom(-0.1);
        }, { passive: false });
    </script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session.permanent = True; session['logged_in'] = True; return redirect('/')
        return render_template_string(LOGIN_TEMPLATE, error="Error")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout(): session.pop('logged_in', None); return redirect('/login')

@app.route('/')
@login_required
def home():
    if not HF_TOKEN: return "Missing Env"
    try:
        tree = api.list_repo_tree(repo_id=DATASET_NAME, repo_type="dataset", token=HF_TOKEN, recursive=False)
        images = []
        for item in tree:
            if item.path.lower().endswith(('.png','.jpg','.jpeg','.gif','.webp','.bmp')):
                images.append({
                    "name": item.path,
                    "real_url": f"https://huggingface.co/datasets/{DATASET_NAME}/resolve/main/{item.path}",
                    "view_url": f"{BASE_URL}/view/{item.path}",
                    "size_fmt": format_size(item.size) if hasattr(item, 'size') else "?"
                })
        images.reverse()
        return render_template_string(HTML_TEMPLATE, images=images, dataset_name=DATASET_NAME)
    except: return "Error loading images"

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    files = request.files.getlist('files')
    count = 0
    for file in files:
        if not file.filename: continue
        # 核心修改：使用 4 位随机字符
        ext = os.path.splitext(file.filename)[1].lower()
        if not ext: ext = ".jpg"
        name = f"{uuid.uuid4().hex[:4]}{ext}"
        
        path = os.path.join(CACHE_DIR, name)
        try:
            file.save(path)
            api.upload_file(path_or_fileobj=path, path_in_repo=name, repo_id=DATASET_NAME, repo_type="dataset", token=HF_TOKEN)
            os.remove(path)
            count += 1
        except: pass
    return jsonify({"status": "success", "count": count})

@app.route('/delete', methods=['POST'])
@login_required
def delete_file():
    name = request.form.get('filename')
    try:
        api.create_commit(repo_id=DATASET_NAME, repo_type="dataset", operations=[CommitOperationDelete(path_in_repo=name)], commit_message=f"Del {name}")
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)})

@app.route('/view/<path:filename>')
def view_image(filename):
    return render_template_string(VIEW_TEMPLATE, real_url=f"https://huggingface.co/datasets/{DATASET_NAME}/resolve/main/{filename}")

if __name__ == '__main__': app.run(host='0.0.0.0', port=7860)

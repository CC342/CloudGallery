import os
import uuid
import datetime
import base64
import requests
import tempfile  # <--- 新增这行
from functools import wraps
from flask import Flask, request, jsonify, render_template_string, redirect, session, url_for
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- 配置区域 ---
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
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

# GitHub API & CDN
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
CDN_BASE = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@{GITHUB_BRANCH}"

# 关键修改：使用系统临时目录 (Vercel 唯一允许写入的地方)
CACHE_DIR = tempfile.gettempdir()

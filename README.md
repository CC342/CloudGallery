# ☁️ CloudGallery (云图床)

> 基于 Hugging Face Datasets 的无限容量、高颜值、私有化图床系统。

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces)
[![Python](https://img.shields.io/badge/Python-Flask-green)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**CloudGallery** 是一个轻量级的图床应用，专为部署在 **Hugging Face Spaces** 而设计。它利用 **Hugging Face Datasets** 作为后端存储，实现了理论上的无限免费存储空间。前端采用极简的 iOS 风格设计，支持磨砂玻璃特效、悬浮预览和多图上传。

---

## ✨ 功能亮点

* **♾️ 无限存储**：直接对接 Hugging Face Datasets，免费且无需担心容量限制。
* **🎨 极致 UI**：
    * **iOS 风格预览**：悬浮式 Lightbox，带底部 Dock 栏（Filmstrip）。
    * **磨砂玻璃 (Glassmorphism)**：全站采用半透明模糊背景，通透有质感。
    * **暗黑/亮色适配**：纯净的半透明视觉体验。
* **🚀 高效上传**：
    * 支持**批量多选上传**。
    * 自动生成 **4位极简短文件名** (如 `a9b2.jpg`)，防止文件名冗长。
* **🔒 安全保护**：
    * 内置账号密码登录系统。
    * 全屏查看链接可公开分享，但上传/删除需鉴权。
* **🛠️ 实用工具**：
    * 一键复制直链 / Markdown 链接。
    * 在线图片删除（后端同步删除）。
    * 图片详细信息显示（分辨率、大小）。
    * 无限自由缩放查看细节。

---

## 📸 界面预览

![登入界面](https://huggingface.co/datasets/cody89/imagehost/resolve/main/b5dc.png)

![主界面](https://cody89-imagehost.hf.space/view/0e53.png)

![预览页面](https://cody89-imagehost.hf.space/view/3306.png)

---

## 🚀 部署指南 (Hugging Face Spaces)

这是最推荐的部署方式，完全免费。

### 1. 准备工作
* 注册一个 [Hugging Face](https://huggingface.co/) 账号。
* 创建一个 **Dataset** (数据集)：
    * 点击 New Dataset。
    * Name: 例如 `my-images`。
    * Type: **Private** (推荐，保护隐私)。
* 获取 **Access Token**：
    * 进入 Settings -> Access Tokens。
    * 创建一个新 Token，权限必须选 **Write** (写入权限)。

### 2. 创建 Space
1.  点击 **New Space**。
2.  **SDK** 选择 **Docker**。
3.  **Template** 选择 **Blank**。

### 3. 上传代码
将本项目中的 `main.py` 和 `Dockerfile` 上传到 Space 的 Files 中。

**Dockerfile 内容示例：**
```dockerfile
FROM python:3.9-slim
WORKDIR /cloudgallery
# 安装依赖
RUN pip install --no-cache-dir flask flask-cors huggingface_hub gunicorn
# 复制所有文件
COPY . .
# 创建缓存目录
RUN mkdir -p /cloudgallery/cache && chmod 777 /cloudgallery/cache
# 启动
CMD ["python", "main.py"]
```

### 4. 配置环境变量 (Settings)

进入 Space 的 **Settings** -> **Variables and secrets**，添加以下变量：

| 类型 | 变量名 | 描述 | 示例值 |
| --- | --- | --- | --- |
| **Secret** | `HF_TOKEN` | 你的 Hugging Face Write Token | `hf_xxxx...` |
| **Secret** | `ADMIN_USER` | 后台登录账号 | `admin` |
| **Secret** | `ADMIN_PASS` | 后台登录密码 | `password123` |
| **Variable** | `DATASET_NAME` | 你的数据集名称 (格式: 用户名/数据集名) | `username/my-images` |

*(可选)* `main.py` 代码中默认生成了固定的 `SECRET_KEY`。为了更安全，你可以手动修改代码中的 `app.secret_key`。

### 5. 重启并使用

配置完成后，Space 会自动重建。等待上方变成 **Running** (绿色)，即可点击 App 进行访问。

---


## 🤝 贡献

欢迎提交 Issue 或 Pull Request 来改进这个项目！

## 📄 开源协议

本项目基于 [MIT License](https://www.google.com/search?q=LICENSE) 开源。

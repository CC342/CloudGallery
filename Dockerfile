# 使用轻量级 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /main

# 安装必要的系统库（可选，防止某些图片库报错）
# RUN apt-get update && apt-get install -y libgl1-mesa-glx

# 1. 安装 Python 依赖
# 我们直接在这里运行 pip，省去 requirements.txt 文件
RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    huggingface_hub \
    gunicorn \
    requests

# 2. 复制当前目录的所有文件到容器
COPY . .

# 3. 创建缓存目录并设置权限（重要！防止 Permission Denied）
RUN mkdir -p /main/cache && chmod 777 /main/cache

# 4. 暴露 HG 默认端口
ENV PORT=7860
EXPOSE 7860

# 5. 启动命令
CMD ["python", "main.py"]

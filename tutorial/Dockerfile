FROM pytorch/pytorch:2.11.0-cuda12.8-cudnn9-devel
COPY requirements.txt .
ENV UV_SYSTEM_PYTHON=1
ENV UV_BREAK_SYSTEM_PACKAGES=1
RUN uv pip install --no-cache-dir -r requirements.txt

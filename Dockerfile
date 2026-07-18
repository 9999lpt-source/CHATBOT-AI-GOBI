# Sử dụng bản Python gọn nhẹ nhưng đầy đủ để build các thư viện C như miniaudio
FROM python:3.11-slim

# Cài đặt các công cụ biên dịch cần thiết cho miniaudio trên môi trường Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc bên trong container
WORKDIR /app

# Copy danh sách thư viện vào trước để tận dụng cache của Docker khi build
COPY requirements.txt .

# Tiến hành cài đặt chính xác các phiên bản thư viện của ông LPT
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code nguồn của project vào container
COPY . .

# Mở cổng 8000 để tiếp nhận kết nối từ ESP32
EXPOSE 8000

# Lệnh khởi chạy server FastAPI với chế độ Unbuffered để xả log liên tục
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
# Sử dụng Python image làm base
FROM python:3.9-slim

# Đặt thư mục làm việc
WORKDIR /app

# Copy tất cả file vào container
COPY . /app

# Cài đặt các thư viện từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Mở cổng 5000
EXPOSE 5000

# Lệnh khởi động ứng dụng
CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]

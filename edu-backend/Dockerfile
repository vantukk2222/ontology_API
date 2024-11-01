# Sử dụng Python 3.10 hoặc cao hơn làm base image
FROM python:3.10-slim

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

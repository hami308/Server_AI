# chú thích 1. cách chạy dự án 
# chạy dự án weather-server-ai
# -> chạy trong môi trường ảo venv310 (chứa python 3.10 ) : -> venv310\Scripts\activate
# -> python app.py
# -> deactivate tắt môi trường ảo

# chú thích 2. deploy lên render 
# bước 1 : chuẩn bị code 
# -> 1.1: Tạo file requirements.txt : chứa các thư viện 
# -> 1.1: Tạo file runtime.txt : chứa phiên bản python 
# -> 1.3: Tạo file .gitignore : chứa các mục không cần đẩy lên github

# bước 2 : push code lên github 
# git init
# git add . (Các file đẩy lên github bao gồm config, data, models, services, app.py, README.md, requirements.txt, runtime.txt, .gitignore (không quan trọng))
# Cách an toàn nhất - add từng nhóm
git add app.py requirements.txt runtime.txt README.md .gitignore
git add config/
git add data/models/
git add services/
git add models/
# git commit -m "Deploy dự án lên server"
# git remote add origin Link_github
# git push -u origin main 

# bước 3 : Tạo tài khoản Render bằng tài khoản github
# 1.1 : Truy câp  https://render.com
# 1.2 : Đăng ký bằng github account
# 1.3 : Authorize Render truy cập Github repos

# bước 4 : Tạo web service
# 4.1 : Trong Render Dashboard
#     -> Click "New +" -> "Web service " 
#     -> connect Github repository của bạn 
#     -> click "Connect" next to repo
# 4.2 : Cấu hình service 
#     -> Name: your-app-name
#     -> Region: Oregon (US West) - gần VN nhất
#     -> Branch: main
#     -> Root Directory: (để trống)
#     -> Runtime: Python 3
#     -> Build Command: pip install -r requirements.txt
#     -> Start Command: python app.py

# bước 5 : Environment variables
# 5.1 : Trong Render Dashboard
#     -> Click tab "Environment"
#     -> add các biến môi trường trong file .env

# bước 6 : Deploy 
#     -> click "create web service"
#     -> Render sẽ tự động :
#          -> clone code thừ github 
#          -> Tạo virtual environment 
#          -> cài đặt dependencies
#          -> chạy app

# bước 7 : kiểm tra kết quả
# 7.1 : Truy cập vào URL của web service
# 7.2 : kiểm tra kết quả


# chú thich 3: giải thích các file 
# data : chứa các file model dự báo dự báo nhiệt độ và % mưa
# config : Định nghĩa tên các json trên firebase
# models : Chạy dự đoán dự báo nhiệt độ và % mưa tả về kết quả
# services : truy cập firebase lấy dữ liệu về dự báo 
# app.py : file chính chạy server
# README.md : file hướng dẫn sử dụng


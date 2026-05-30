import os
import time  # Thêm thư viện quản lý thời gian thực phục vụ tính toán vòng đời Cache

# 1. NẠP BIẾN MÔI TRƯỜNG (Dành riêng cho Local)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # Ép nạp đè biến môi trường mới nhất từ file .env
except ImportError:
    pass

from app import create_app
from app.models.setting_model import SettingModel 

# 2. KHỞI TẠO ỨNG DỤNG FLASK
app = create_app()

# Nâng hạn mức trần nhận dữ liệu của tệp tin đầu vào trong Flask lên 50MB
# Sửa tận gốc lỗi 413 Request Entity Too Large khi chạy Local/Gunicorn mà không có Nginx
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


# ═══════════════════════════════════════════════════════════════
#  CẤU HÌNH BỘ NHỚ ĐỆM TẠM THỜI (IN-MEMORY CACHE)
#  Giải pháp tối ưu hóa tốc độ tải trang dứt điểm khi deploy Vercel
# ═══════════════════════════════════════════════════════════════
_SETTINGS_CACHE = None
_CACHE_TIMEOUT = 300  # Lưu trữ cấu hình trong 5 phút (300 giây) rồi mới kéo lại từ Supabase
_LAST_FETCH_TIME = 0


# ═══════════════════════════════════════════════════════════════
#  BƯỚC 5: GLOBAL CONTEXT PROCESSOR (BẢN CẬP NHẬT TỐI ƯU SIÊU TỐC)
#  Đã sửa lỗi nghẽn I/O gọi Supabase liên tục khi render template
# ═══════════════════════════════════════════════════════════════
@app.context_processor
def inject_global_settings():
    """Tự động kéo hoặc tái sử dụng cấu hình Banner/Cài đặt từ bộ nhớ đệm Cache"""
    global _SETTINGS_CACHE, _LAST_FETCH_TIME
    current_time = time.time()
    
    # CHIẾN THUẬT CỨU NGUY VERCEL: Nếu đã có Cache và chưa quá 5 phút -> Trả về lập tức (Tốc độ ~0ms)
    if _SETTINGS_CACHE and (current_time - _LAST_FETCH_TIME < _CACHE_TIMEOUT):
        return _SETTINGS_CACHE

    try:
        # Chỉ khi hết hạn cache hoặc Serverless Container khởi động lại mới truy vấn Supabase
        all_settings = SettingModel.get_settings()
        
        # Ghi đè dữ liệu mới vào bộ nhớ đệm tạm thời
        _SETTINGS_CACHE = dict(
            system_settings=all_settings,  # Tên biến bắt buộc phải trùng khớp với hệ thống template html
            global_settings=all_settings.get("general", {})
        )
        _LAST_FETCH_TIME = current_time
        return _SETTINGS_CACHE
        
    except Exception:
        # Cơ chế dự phòng an toàn tuyệt đối nếu kết nối mạng Supabase gặp sự cố khi đang tải trang
        defaults = SettingModel.DEFAULT_SETTINGS
        return dict(
            system_settings=defaults,
            global_settings=defaults["general"]
        )


# 3. MÁY CHỦ PHÁT TRIỂN (Local Development)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    
    print("=" * 55)
    print("🚀 GUA MAISON 2026 - SERVER IS STARTING...")
    print(f"🌍 Truy cập tại     : http://127.0.0.1:{port}")
    print(f"🛠️  Chế độ Debug    : {'BẬT (Development)' if is_debug else 'TẮT (Production)'}")
    print("=" * 55)
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=is_debug
    )   
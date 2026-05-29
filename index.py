import os

# 1. NẠP BIẾN MÔI TRƯỜNG (Dành riêng cho Local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.models.setting_model import SettingModel 

# 2. KHỞI TẠO ỨNG DỤNG FLASK
app = create_app()

# 🔴 BẢN CẬP NHẬT 1: Nâng hạn mức trần nhận dữ liệu của tệp tin đầu vào trong Flask lên 50MB
# Sửa tận gốc lỗi 413 Request Entity Too Large khi chạy Local/Gunicorn mà không có Nginx
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


# ═══════════════════════════════════════════════════════════════
#  BƯỚC 5: GLOBAL CONTEXT PROCESSOR (BẢN CẬP NHẬT ĐỒNG BỘ REAL-TIME)
#  Đã sửa lỗi hiển thị hệ thống Banner Storefront ngoài trang chủ công khai
# ═══════════════════════════════════════════════════════════════
@app.context_processor
def inject_global_settings():
    """Tự động kéo toàn bộ cấu hình mới nhất từ Supabase ra mọi trang Web công khai"""
    try:
        all_settings = SettingModel.get_settings()
        return dict(
            system_settings=all_settings, # Tên biến này bắt buộc phải trùng khớp với index.html
            global_settings=all_settings.get("general", {})
        )
    except Exception:
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
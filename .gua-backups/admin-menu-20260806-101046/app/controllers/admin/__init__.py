"""
app/controllers/admin/__init__.py
Gom (Aggregate) Blueprint và đăng ký toàn bộ các route con.
"""

# 1. Lấy blueprint gốc
from ._blueprint import admin_bp

# 2. BẮT BUỘC: Import các file chứa route để Flask đăng ký chúng vào admin_bp
# Lưu ý: Import ở đây để tránh lỗi vòng lặp (Circular Import)
from . import dashboard
from . import orders
from . import returns
from . import customers
from . import coupons
from . import products
from . import reports
from . import pos_controller  # <--- BẠN CHỈ CẦN THÊM DÒNG NÀY VÀO ĐÂY
from . import settings
from . import permissions_controller
from . import notifications   
from . import audit_controller
# 3. Export admin_bp ra ngoài (cho app/__init__.py gọi)
__all__ = ["admin_bp"]

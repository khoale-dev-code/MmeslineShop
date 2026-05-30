"""
app/controllers/admin/settings.py
Controller xử lý trang Cài đặt Hệ thống.
Sections: General, Storefront, Integrations, Shipping Rules, Language, Admin UI.
Tích hợp bộ bọc an toàn chống sập JSON và cách ly lỗi ghi nhật ký kiểm toán.
"""
import logging
import uuid
from flask import request, render_template, jsonify, current_app
from ._blueprint import admin_bp
from app.models.setting_model import SettingModel
from app.services.audit_service import AuditService
from app.middleware.auth_required import admin_required
from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)

VALID_SETTINGS_SECTIONS = [
    "general",
    "storefront",
    "integrations",
    "shipping_rules",
    "language",
    "admin_ui",
]

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'avi'}
# Đồng bộ hạn mức tối đa trần xử lý 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024  


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ═══════════════════════════════════════════════════════════════
#  1. HIỂN THỊ GIAO DIỆN CÀI ĐẶT
# ═══════════════════════════════════════════════════════════════


@admin_bp.route("/settings", methods=["GET"])
@admin_required
def settings_page():
    try:
        settings = SettingModel.get_settings()
        return render_template(
            "admin/settings/index.html",
            general=settings.get("general", {}),
            storefront=settings.get("storefront", {}),
            integrations=settings.get("integrations", {}),
            shipping_rules=settings.get("shipping_rules", {}),
            language=settings.get("language", {}),
            admin_ui=settings.get("admin_ui", {}),
        )
    except Exception as e:
        logger.error(f"[Settings Controller] Lỗi tải trang cài đặt: {e}")
        return jsonify({"error": "Lỗi hệ thống nội bộ", "detail": str(e)}), 500

# ═══════════════════════════════════════════════════════════════
#  2. CẬP NHẬT DỮ LIỆU
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/settings/update/<section>", methods=["POST"])
@admin_required
def update_settings(section):
    try:
        if section not in VALID_SETTINGS_SECTIONS:
            return jsonify({"success": False, "message": f"Khu vực '{section}' không hợp lệ."}), 400

        data = request.get_json(silent=True)
        if data is None:
            data = request.form.to_dict()

        # 🟢 FIX QUAN TRỌNG: Loại bỏ csrf_token khỏi dữ liệu để không lưu "rác" vào Database
        data.pop('csrf_token', None)

        if not data and section != "shipping_rules":
            return jsonify({"success": False, "message": "Không có dữ liệu gửi lên."}), 400

        old_settings = SettingModel.get_section(section)
        success = SettingModel.update_section(section, data)

        if success:
            try:
                AuditService.log_action(
                    action="UPDATE",
                    table_name="system_settings",
                    record_id=section,
                    old_values=old_settings,
                    new_values=data
                )
            except Exception as audit_err:
                logger.error(f"[Audit Log Error] Không thể ghi nhật ký kiểm toán: {audit_err}")

            section_names = {
                "general": "Thông tin chung",
                "storefront": "Giao diện cửa hàng",
                "integrations": "Khóa API & Tích hợp",
                "shipping_rules": "Luật vận chuyển",
                "language": "Ngôn ngữ Admin",
                "admin_ui": "Giao diện cấu hình Admin",
            }
            friendly_name = section_names.get(section, section.upper())

            return jsonify({
                "success": True,
                "message": f"Đã lưu thành công: {friendly_name}!"
            })

        return jsonify({"success": False, "message": "Mô hình từ chối cập nhật vào Database."}), 500

    except Exception as fatal_err:
        logger.error(f"[Fatal Route Settings Error] Sập hệ thống tệp tin: {fatal_err}")
        return jsonify({"success": False, "message": f"Lỗi hệ thống nội bộ: {str(fatal_err)}"}), 500

# ═══════════════════════════════════════════════════════════════
#  3. UPLOAD MEDIA LÊN BUCKET STORE-ASSETS
# ═══════════════════════════════════════════════════════════════


@admin_bp.route("/settings/upload", methods=["POST"])
@admin_required
def upload_storefront_media():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Không có file nào được gửi lên"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Chưa chọn file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Định dạng file không được hỗ trợ."}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({"success": False, "error": "File vượt quá giới hạn cấu hình (Tối đa 50MB)"}), 400

    try:
        db = get_supabase()
        ext = file.filename.rsplit('.', 1)[1].lower()
        
        bucket_name = "store-assets"
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        file_bytes = file.read()
        content_type = file.content_type or "image/jpeg"

        db.storage.from_(bucket_name).upload(
            filename,
            file_bytes,
            {"content-type": content_type}
        )
        
        public_url = db.storage.from_(bucket_name).get_public_url(filename)
        return jsonify({"success": True, "url": public_url})

    except Exception as e:
        logger.error(f"[Settings Upload Crash] Chi tiết lỗi: {e}")
        return jsonify({"success": False, "error": f"Lỗi lưu trữ dữ liệu Supabase: {str(e)}"}), 500
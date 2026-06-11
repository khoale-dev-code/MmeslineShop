"""
app/controllers/admin/settings.py
Controller xử lý trang Cài đặt Hệ thống.
Fix:
- Lưu storefront xong sẽ xoá cache runtime để ảnh mới hiển thị ngay.
- Upload media dùng Supabase service_role để tránh lỗi RLS/storage policy.
- Trả reload=True cho storefront để admin tự refresh dữ liệu mới.
"""
import logging
import sys
import uuid

from flask import request, render_template, jsonify
from ._blueprint import admin_bp
from app.models.setting_model import SettingModel
from app.services.audit_service import AuditService
from app.middleware.auth_required import admin_required
from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

VALID_SETTINGS_SECTIONS = [
    "general",
    "storefront",
    "integrations",
    "shipping_rules",
    "language",
    "admin_ui",
]

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov", "avi", "webm"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _invalidate_runtime_settings_cache() -> None:
    """
    Xoá toàn bộ cache settings sau khi admin cập nhật cấu hình.
    Quan trọng: SettingModel.invalidate_cache() chỉ xoá cache của model,
    nhưng index.py còn có _SETTINGS_CACHE riêng nên phải xoá thêm.
    """
    try:
        SettingModel.invalidate_cache()
    except Exception as e:
        logger.warning("[Settings Cache] Không xoá được SettingModel cache: %s", e)

    try:
        from app.context_processors import invalidate_shared_cache
        invalidate_shared_cache()
    except Exception as e:
        logger.debug("[Settings Cache] Bỏ qua app.context_processors cache: %s", e)

    # Không import index trực tiếp để tránh circular import / tạo app lần 2.
    for module_name in ("index", "__main__"):
        module = sys.modules.get(module_name)
        if not module:
            continue

        fn = getattr(module, "invalidate_global_context_cache", None)
        if callable(fn):
            try:
                fn()
                logger.info("[Settings Cache] Đã xoá cache global từ module %s", module_name)
            except Exception as e:
                logger.warning("[Settings Cache] Không xoá được cache module %s: %s", module_name, e)


@admin_bp.route("/settings", methods=["GET"])
@admin_required
def settings_page():
    try:
        settings = SettingModel.get_settings(force_reload=True)
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
        logger.error("[Settings Controller] Lỗi tải trang cài đặt: %s", e, exc_info=True)
        return jsonify({"error": "Lỗi hệ thống nội bộ", "detail": str(e)}), 500


@admin_bp.route("/settings/update/<section>", methods=["POST"])
@admin_required
def update_settings(section):
    try:
        if section not in VALID_SETTINGS_SECTIONS:
            return jsonify({
                "success": False,
                "message": f"Khu vực '{section}' không hợp lệ."
            }), 400

        data = request.get_json(silent=True)
        if data is None:
            data = request.form.to_dict()

        data.pop("csrf_token", None)

        if not data and section != "shipping_rules":
            return jsonify({
                "success": False,
                "message": "Không có dữ liệu gửi lên."
            }), 400

        old_settings = SettingModel.get_section(section)
        success = SettingModel.update_section(section, data)

        if not success:
            return jsonify({
                "success": False,
                "message": "Mô hình từ chối cập nhật vào Database."
            }), 500

        _invalidate_runtime_settings_cache()

        try:
            AuditService.log_action(
                action="UPDATE",
                table_name="system_settings",
                record_id=section,
                old_values=old_settings,
                new_values=data,
            )
        except Exception as audit_err:
            logger.warning("[Audit Log Error] Không thể ghi nhật ký kiểm toán: %s", audit_err)

        section_names = {
            "general": "Thông tin chung",
            "storefront": "Giao diện cửa hàng",
            "integrations": "Khóa API & Tích hợp",
            "shipping_rules": "Luật vận chuyển",
            "language": "Ngôn ngữ Admin",
            "admin_ui": "Giao diện cấu hình Admin",
        }

        return jsonify({
            "success": True,
            "message": f"Đã lưu thành công: {section_names.get(section, section.upper())}!",
            "reload": section == "storefront",
        })

    except Exception as fatal_err:
        logger.error("[Fatal Route Settings Error] %s", fatal_err, exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Lỗi hệ thống nội bộ: {str(fatal_err)}"
        }), 500


@admin_bp.route("/settings/upload", methods=["POST"])
@admin_required
def upload_storefront_media():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "Không có file nào được gửi lên"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"success": False, "error": "Chưa chọn file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Định dạng file không được hỗ trợ."}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        return jsonify({
            "success": False,
            "error": "File vượt quá giới hạn cấu hình. Tối đa 50MB."
        }), 400

    try:
        db = get_supabase_admin()

        ext = file.filename.rsplit(".", 1)[1].lower()
        bucket_name = "store-assets"
        filename = f"storefront/{uuid.uuid4().hex}.{ext}"

        file_bytes = file.read()
        content_type = file.content_type or "application/octet-stream"

        db.storage.from_(bucket_name).upload(
            filename,
            file_bytes,
            {
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false",
            },
        )

        public_url = db.storage.from_(bucket_name).get_public_url(filename)

        return jsonify({
            "success": True,
            "url": public_url,
        })

    except Exception as e:
        logger.error("[Settings Upload Crash] Chi tiết lỗi: %s", e, exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Lỗi lưu trữ Supabase: {str(e)}"
        }), 500
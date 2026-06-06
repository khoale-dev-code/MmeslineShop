"""
app/__init__.py  –  Application Factory (GUA MAISON 2026 Edition)
"""
import os
import logging
from flask import Flask, session, render_template_string
from flask_wtf.csrf import CSRFProtect, CSRFError

from config.settings import get_config, validate_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

csrf = CSRFProtect()
def _env_enabled(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}
from app.models.cart_model     import CartModel
from app.models.category_model import CategoryModel
from app.models.setting_model  import SettingModel

# ── KHAI BÁO ERROR_TEMPLATE Ở ĐÂY ĐỂ LINTER KHÔNG BÁO LỖI ──────────────────
ERROR_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ code }} – GUA Maison</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,700;0,900;1,400&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'DM Sans', system-ui, sans-serif;
      background: #fafaf9;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 3rem 1rem;
      overflow: hidden;
    }
    .blob {
      position: fixed; top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      width: 500px; height: 500px;
      background: #e7e5e4;
      border-radius: 50%;
      filter: blur(100px);
      pointer-events: none; z-index: 0;
    }
    .card {
      position: relative; z-index: 10;
      width: 100%; max-width: 620px;
      background: rgba(255,255,255,0.85);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(231,229,228,0.7);
      border-radius: 1.5rem;
      padding: clamp(2.5rem, 6vw, 5rem);
      text-align: center;
      box-shadow: 0 20px 60px -15px rgba(0,0,0,0.1);
      animation: revealUp .7s cubic-bezier(.22,1,.36,1) forwards;
      opacity: 0;
    }
    @keyframes revealUp {
      from { opacity: 0; transform: translateY(28px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .icon-wrap {
      width: 4rem; height: 4rem;
      border-radius: 50%;
      background: #f5f5f4;
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 1.5rem;
      color: #a8a29e;
    }
    .icon-wrap svg { width: 2rem; height: 2rem; }
    .code {
      font-size: clamp(5rem, 18vw, 8rem);
      font-weight: 900;
      line-height: 1;
      letter-spacing: -.04em;
      color: #1c1917;
      margin-bottom: 1rem;
    }
    .title {
      font-size: clamp(1.1rem, 3vw, 1.6rem);
      font-weight: 700;
      color: #1c1917;
      letter-spacing: -.02em;
      margin-bottom: .75rem;
    }
    .desc {
      color: #78716c;
      font-size: .9rem;
      font-weight: 500;
      line-height: 1.7;
      max-width: 380px;
      margin: 0 auto 2.5rem;
    }
    .btn-home {
      display: inline-block;
      background: #1c1917;
      color: #fff;
      font-size: .875rem;
      font-weight: 700;
      padding: .9rem 2.5rem;
      border-radius: .75rem;
      text-decoration: none;
      box-shadow: 0 4px 20px rgba(0,0,0,.15);
      transition: background .2s, transform .2s;
    }
    .btn-home:hover  { background: #44403c; transform: translateY(-2px); }
    .btn-home:active { transform: scale(.97); }
    .btn-debug {
      display: block;
      margin-top: 1.25rem;
      font-size: .75rem;
      font-weight: 700;
      color: #a8a29e;
      text-decoration: underline;
      text-underline-offset: 3px;
      cursor: pointer;
      background: none; border: none;
      transition: color .2s;
    }
    .btn-debug:hover { color: #1c1917; }
  </style>
</head>
<body>
  <div class="blob" aria-hidden="true"></div>
  <div class="card">
    <div class="icon-wrap" aria-hidden="true">
      {% if code == 404 %}
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/></svg>
      {% elif code in (403, 400, 405) %}
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/></svg>
      {% elif code == 413 %}
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/></svg>
      {% else %}
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
      {% endif %}
    </div>

    <p class="code">{{ code }}</p>
    <h1 class="title">{{ title }}</h1>
    <p class="desc">{{ desc }}</p>

    <a href="/" class="btn-home">Trở về Trang chủ</a>

    {% if show_debug and code == 500 %}
    <a href="/debug/test-db" class="btn-debug">Chạy trình kiểm tra CSDL</a>
    {% endif %}
  </div>
</body>
</html>"""


def create_app() -> Flask:
    # ĐỔI TÊN BIẾN THÀNH flask_app ĐỂ IDE KHÔNG BỊ NHẦM
    flask_app = Flask(__name__, template_folder="templates", static_folder="static")

    # 1. Validate & Load Config
    validate_config()
    flask_app.config.from_object(get_config())
    flask_app.config["BASE_URL"] = os.environ.get("BASE_URL", "")
    # 2. Extensions
    csrf.init_app(flask_app)

 # 3. Blueprints
    # Storefront/public routes: luôn cần cho website bán hàng
    from app.controllers.auth_controller          import auth_bp
    from app.controllers.product_controller       import products_bp
    from app.controllers.cart_controller          import cart_bp
    from app.controllers.profile_controller       import profile_bp
    from app.controllers.favorite_controller      import favorite_bp
    from app.controllers.payment_controller       import payment_bp
    from app.controllers.promotions_controller    import promotions_bp
    from app.controllers.notification_controller  import notification_bp

    public_blueprints = [
        auth_bp,
        products_bp,
        cart_bp,
        profile_bp,
        favorite_bp,
        payment_bp,
        promotions_bp,
        notification_bp,
    ]

    for bp in public_blueprints:
        flask_app.register_blueprint(bp)

    # Analytics: tách riêng để có thể tắt nếu đang ưu tiên tốc độ storefront
    if _env_enabled("ENABLE_ANALYTICS", "true"):
        from app.controllers.analytics_controller import analytics_bp
        flask_app.register_blueprint(analytics_bp)
        logger.info("✅ Analytics blueprint enabled.")

    # AI / Chat: chỉ bật khi cần, vì import AI service có thể làm cold start nặng
    if _env_enabled("ENABLE_AI", "false"):
        from app.controllers.chat_controller import chat_bp
        from app.controllers.ai_controller   import ai_bp

        flask_app.register_blueprint(chat_bp)
        flask_app.register_blueprint(ai_bp)
        logger.info("✅ AI / Chat blueprints enabled.")

    # Admin: chỉ bật khi cần. Không nên load admin vào storefront production nếu đang tối ưu tốc độ.
    if _env_enabled("ENABLE_ADMIN", "true"):
        from app.controllers.admin import admin_bp
        from app.controllers.admin.admin_shipping_controller import admin_shipping_bp
        from app.controllers.admin.admin_shipping_providers_controller import admin_providers_bp

        flask_app.register_blueprint(admin_bp)
        flask_app.register_blueprint(admin_shipping_bp)
        flask_app.register_blueprint(admin_providers_bp)
        logger.info("✅ Admin blueprints enabled.")
    else:
        logger.info("🚫 Admin blueprints disabled for faster storefront cold start.")

    if flask_app.config.get("DEBUG"):
        from app.controllers.debug_controller import debug_bp
        flask_app.register_blueprint(debug_bp)
        logger.info("🛠️  Debug blueprint đã được kích hoạt (Development only).")

    # 4. Context Processor
    @flask_app.context_processor
    def inject_globals() -> dict:
        cart_count = 0
        categories = []
        pending_returns = 0
        system_settings = {}
        
        user_id = session.get("user_id")
        role = session.get("role")

        try:
            system_settings = SettingModel.get_settings()
        except Exception:
            logger.warning("context_processor: Lỗi khi lấy system_settings.")

        unread_notification_count = 0
        if user_id:
            try:
                cart_count = CartModel.get_count(user_id)
            except Exception:
                pass
            try:
                from app.models.notification_model import NotificationModel
                unread_notification_count = NotificationModel.get_unread_count(user_id)
            except Exception:
                pass

        try:
            categories = CategoryModel.get_all()
        except Exception:
            pass

        if role == "admin":
            try:
                from app.utils.supabase_client import get_supabase
                r = (
                    get_supabase()
                    .table("return_requests")
                    .select("id", count="exact")
                    .eq("status", "pending")
                    .execute()
                )
                pending_returns = r.count or 0
            except Exception:
                pass

        return {
            "current_user": {
                "id": user_id,
                "email": session.get("email"),
                "full_name": session.get("full_name"),
                "role": role,
            },
            "cart_count": cart_count,
            "global_categories": categories,
            "pending_returns": pending_returns,
            "system_settings": system_settings,
            "unread_notification_count": unread_notification_count,
        }

    # 5. Error Handlers
    def _error_response(code: int, title: str, desc: str):
        show_debug = flask_app.config.get("DEBUG", False)
        return render_template_string(
            ERROR_TEMPLATE, code=code, title=title, desc=desc,
            show_debug=show_debug
        ), code

    @flask_app.errorhandler(400)
    def bad_request(_e):
        return _error_response(400, "Yêu cầu không hợp lệ", "Dữ liệu gửi lên bị lỗi hoặc không đúng định dạng.")

    @flask_app.errorhandler(403)
    def forbidden(_e):
        return _error_response(403, "Từ chối truy cập", "Bạn không có quyền truy cập vào trang này.")

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(_e):
        return _error_response(403, "Phiên bảo mật hết hạn", "Token bảo mật đã hết hạn. Vui lòng tải lại trang và thử lại.")

    @flask_app.errorhandler(404)
    def not_found(_e):
        return _error_response(404, "Không tìm thấy trang", "Đường dẫn này không tồn tại hoặc đã bị gỡ khỏi hệ thống GUA Maison.")

    @flask_app.errorhandler(405)
    def method_not_allowed(_e):
        return _error_response(405, "Phương thức không được phép", "Hành động này không được hỗ trợ trên endpoint hiện tại.")

    @flask_app.errorhandler(413)
    def request_too_large(_e):
        return _error_response(413, "File quá lớn", "Kích thước file vượt quá giới hạn 10 MB. Vui lòng chọn ảnh nhỏ hơn.")

    @flask_app.errorhandler(500)
    def server_error(_e):
        logger.exception("Internal Server Error")
        return _error_response(500, "Lỗi máy chủ", "Hệ thống đang gặp sự cố kỹ thuật. Đội ngũ kỹ sư đang xử lý.")

    return flask_app

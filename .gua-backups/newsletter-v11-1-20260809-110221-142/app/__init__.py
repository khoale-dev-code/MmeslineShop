"""
app/__init__.py
Application Factory - GUAMAISON 2026 Edition

Cập nhật:
- Luôn register chat_bp để endpoint /api/bot không bị 404.
- ai_bp vẫn có thể bật/tắt bằng ENABLE_AI.
- Context processor an toàn hơn.
- Error template đồng bộ GUAMAISON green/gold.
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


from app.services.cart_service import cart_service
from app.models.category_model import CategoryModel
from app.models.setting_model import SettingModel
from app.models.navigation_model import NavigationModel


ERROR_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ code }} – GUAMAISON</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap"
    rel="stylesheet"
  >

  <style>
    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    :root {
      --mm-green: #1b4922;
      --mm-green-dark: #123418;
      --mm-gold: #c99e14;
      --mm-ink: #101510;
      --mm-muted: #687466;
      --mm-line: rgba(27, 73, 34, .14);
      --mm-cream: #fbfaf4;
      --mm-soft: #f7f9f2;
    }

    body {
      font-family: "DM Sans", system-ui, sans-serif;
      background:
        radial-gradient(circle at top right, rgba(201, 158, 20, .18), transparent 34%),
        radial-gradient(circle at bottom left, rgba(27, 73, 34, .14), transparent 36%),
        linear-gradient(180deg, #fff 0%, var(--mm-cream) 100%);
      color: var(--mm-ink);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 3rem 1rem;
      overflow: hidden;
    }

    .blob {
      position: fixed;
      top: 50%;
      left: 50%;
      width: 560px;
      height: 560px;
      transform: translate(-50%, -50%);
      background: rgba(27, 73, 34, .13);
      border-radius: 999px;
      filter: blur(100px);
      pointer-events: none;
      z-index: 0;
    }

    .card {
      position: relative;
      z-index: 10;
      width: 100%;
      max-width: 660px;
      background: rgba(255, 255, 255, .9);
      backdrop-filter: blur(22px);
      border: 1px solid var(--mm-line);
      border-radius: 24px;
      padding: clamp(2.5rem, 6vw, 5rem);
      text-align: center;
      box-shadow: 0 28px 80px -46px rgba(27, 73, 34, .55);
      animation: revealUp .7s cubic-bezier(.22, 1, .36, 1) forwards;
      opacity: 0;
    }

    @keyframes revealUp {
      from {
        opacity: 0;
        transform: translateY(28px);
      }

      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .brand {
      margin-bottom: 1.5rem;
      color: var(--mm-gold);
      font-size: .72rem;
      font-weight: 900;
      letter-spacing: .24em;
      text-transform: uppercase;
    }

    .icon-wrap {
      width: 4.25rem;
      height: 4.25rem;
      border-radius: 1.35rem;
      background: var(--mm-soft);
      color: var(--mm-green);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem;
      border: 1px solid var(--mm-line);
    }

    .icon-wrap svg {
      width: 2rem;
      height: 2rem;
    }

    .code {
      font-size: clamp(5.4rem, 18vw, 9rem);
      font-weight: 900;
      line-height: .82;
      letter-spacing: -.075em;
      color: var(--mm-green);
      margin-bottom: 1.2rem;
    }

    .title {
      font-size: clamp(1.15rem, 3vw, 1.7rem);
      font-weight: 900;
      color: var(--mm-ink);
      letter-spacing: -.03em;
      margin-bottom: .8rem;
    }

    .desc {
      color: var(--mm-muted);
      font-size: .94rem;
      font-weight: 600;
      line-height: 1.75;
      max-width: 430px;
      margin: 0 auto 2.5rem;
    }

    .btn-home {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      background: var(--mm-green);
      color: #fff;
      font-size: .78rem;
      font-weight: 900;
      letter-spacing: .12em;
      text-transform: uppercase;
      padding: 0 2.1rem;
      border-radius: 14px;
      text-decoration: none;
      box-shadow: 0 18px 36px -24px rgba(27, 73, 34, .8);
      transition: background .2s ease, color .2s ease, transform .2s ease;
    }

    .btn-home:hover {
      background: var(--mm-gold);
      color: var(--mm-green-dark);
      transform: translateY(-2px);
    }

    .btn-home:active {
      transform: scale(.98);
    }

    .btn-debug {
      display: block;
      margin-top: 1.25rem;
      font-size: .75rem;
      font-weight: 800;
      color: var(--mm-gold);
      text-decoration: underline;
      text-underline-offset: 3px;
    }

    .btn-debug:hover {
      color: var(--mm-green);
    }
  </style>
</head>

<body>
  <div class="blob" aria-hidden="true"></div>

  <main class="card">
    <p class="brand">GUAMAISON SYSTEM</p>

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

    <a href="/" class="btn-home">Trở về trang chủ</a>

    {% if show_debug and code == 500 %}
    <a href="/debug/test-db" class="btn-debug">Chạy trình kiểm tra CSDL</a>
    {% endif %}
  </main>
</body>
</html>"""


def create_app() -> Flask:
    flask_app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # 1. Validate & Load Config
    validate_config()
    flask_app.config.from_object(get_config())
    flask_app.config["BASE_URL"] = os.environ.get("BASE_URL", "")

    # 2. Extensions
    csrf.init_app(flask_app)

    # 3. Public Blueprints
    from app.controllers.auth_controller import auth_bp
    from app.controllers.product_controller import products_bp
    from app.controllers.cart_controller import cart_bp
    from app.controllers.profile_controller import profile_bp
    from app.controllers.favorite_controller import favorite_bp
    from app.controllers.payment_controller import payment_bp
    from app.controllers.promotions_controller import promotions_bp
    from app.controllers.notification_controller import notification_bp

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

    # 4. Chatbot API luôn bật để /api/bot không bị 404
    try:
        from app.controllers.chat_controller import chat_bp

        flask_app.register_blueprint(chat_bp)
        logger.info("✅ Chat blueprint enabled at /api/bot.")
    except Exception as e:
        logger.error("❌ Không register được chat_bp: %s", e, exc_info=True)

    # 5. AI nâng cao bật/tắt riêng
    if _env_enabled("ENABLE_AI", "false"):
        try:
            from app.controllers.ai_controller import ai_bp

            flask_app.register_blueprint(ai_bp)
            logger.info("✅ AI blueprint enabled.")
        except Exception as e:
            logger.error("❌ Không register được ai_bp: %s", e, exc_info=True)
    else:
        logger.info("ℹ️ ENABLE_AI=false: chỉ bật Chat API cơ bản /api/bot.")

    # 6. Analytics
    if _env_enabled("ENABLE_ANALYTICS", "true"):
        try:
            from app.controllers.analytics_controller import analytics_bp

            flask_app.register_blueprint(analytics_bp)
            logger.info("✅ Analytics blueprint enabled.")
        except Exception as e:
            logger.error("❌ Không register được analytics_bp: %s", e, exc_info=True)

    # 7. Sepay webhook nếu có
    try:
        from app.controllers.sepay_controller import sepay_bp

        flask_app.register_blueprint(sepay_bp)
        logger.info("✅ Sepay blueprint enabled.")
    except Exception as e:
        logger.info("ℹ️ Sepay blueprint chưa bật hoặc chưa tồn tại: %s", e)

    # 8. Admin
    if _env_enabled("ENABLE_ADMIN", "true"):
        try:
            from app.controllers.admin import admin_bp
            from app.controllers.admin.admin_shipping_controller import admin_shipping_bp
            from app.controllers.admin.admin_shipping_providers_controller import admin_providers_bp

            flask_app.register_blueprint(admin_bp)
            flask_app.register_blueprint(admin_shipping_bp)
            flask_app.register_blueprint(admin_providers_bp)
            logger.info("✅ GUAMAISON admin blueprints enabled.")
        except Exception as e:
            logger.error("❌ Không register được admin blueprints: %s", e, exc_info=True)
    else:
        logger.info("🚫 Admin blueprints disabled for faster storefront cold start.")

    # 9. Debug
    if flask_app.config.get("DEBUG"):
        try:
            from app.controllers.debug_controller import debug_bp

            flask_app.register_blueprint(debug_bp)
            logger.info("🛠️ Debug blueprint enabled. Development only.")
        except Exception as e:
            logger.warning("Không register được debug_bp: %s", e)

    # 10. Context Processor
    @flask_app.context_processor
    def inject_globals() -> dict:
        cart_count = 0
        categories = []
        pending_returns = 0
        system_settings = {}
        unread_notification_count = 0
        navigation_config = NavigationModel.normalize_config({})
        menu_product_categories = []

        user_id = session.get("user_id")
        role = session.get("role") or session.get("user_role")

        try:
            system_settings = SettingModel.get_settings() or {}
        except Exception:
            logger.warning("context_processor: Không lấy được system_settings.", exc_info=True)
            system_settings = getattr(SettingModel, "DEFAULT_SETTINGS", {}) or {}

        if user_id:
            try:
                cart_count = cart_service.get_count(user_id)
            except Exception:
                cart_count = 0

            try:
                from app.models.notification_model import NotificationModel

                unread_notification_count = NotificationModel.get_unread_count(user_id)
            except Exception:
                unread_notification_count = 0

        try:
            categories = CategoryModel.get_all(active_only=True, admin_mode=False)
        except TypeError:
            try:
                categories = CategoryModel.get_all(active_only=True)
            except Exception:
                categories = []
        except Exception:
            categories = []

        navigation_config = NavigationModel.normalize_config(
            system_settings.get("navigation") if isinstance(system_settings, dict) else {}
        )
        menu_product_categories = NavigationModel.select_product_categories(
            navigation_config, categories
        )

        if role == "admin":
            try:
                from app.utils.supabase_client import get_supabase_admin

                r = (
                    get_supabase_admin()
                    .table("return_requests")
                    .select("id", count="exact")
                    .eq("status", "pending")
                    .execute()
                )
                pending_returns = r.count or 0
            except Exception:
                pending_returns = 0

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
            "admin_notification_count": unread_notification_count,
            "site_navigation": navigation_config,
            "menu_product_categories": menu_product_categories,
            "shop_name": navigation_config["navbar"].get("brand_label") or "GUAMAISON",
            "shop_description": navigation_config["footer"].get("description") or "GUAMAISON | Official Online Store",
        }

    # 11. Error Handlers
    def _error_response(code: int, title: str, desc: str):
        show_debug = flask_app.config.get("DEBUG", False)

        return render_template_string(
            ERROR_TEMPLATE,
            code=code,
            title=title,
            desc=desc,
            show_debug=show_debug,
        ), code

    @flask_app.errorhandler(400)
    def bad_request(_e):
        return _error_response(
            400,
            "Yêu cầu không hợp lệ",
            "Dữ liệu gửi lên chưa đúng định dạng. Vui lòng kiểm tra lại và thử lần nữa.",
        )

    @flask_app.errorhandler(403)
    def forbidden(_e):
        return _error_response(
            403,
            "Từ chối truy cập",
            "Bạn không có quyền truy cập vào khu vực này của GUAMAISON.",
        )

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(_e):
        return _error_response(
            403,
            "Phiên bảo mật hết hạn",
            "Token bảo mật đã hết hạn. Vui lòng tải lại trang và thực hiện lại thao tác.",
        )

    @flask_app.errorhandler(404)
    def not_found(_e):
        return _error_response(
            404,
            "Không tìm thấy trang",
            "Đường dẫn này không tồn tại hoặc đã bị gỡ khỏi hệ thống GUAMAISON.",
        )

    @flask_app.errorhandler(405)
    def method_not_allowed(_e):
        return _error_response(
            405,
            "Phương thức không được phép",
            "Hành động này không được hỗ trợ trên endpoint hiện tại.",
        )

    @flask_app.errorhandler(413)
    def request_too_large(_e):
        return _error_response(
            413,
            "File quá lớn",
            "Kích thước file vượt quá giới hạn cho phép. Vui lòng chọn file nhỏ hơn.",
        )

    @flask_app.errorhandler(500)
    def server_error(_e):
        logger.exception("GUAMAISON Internal Server Error")

        return _error_response(
            500,
            "Lỗi máy chủ",
            "Hệ thống GUAMAISON đang gặp sự cố kỹ thuật. Vui lòng thử lại sau.",
        )

    return flask_app
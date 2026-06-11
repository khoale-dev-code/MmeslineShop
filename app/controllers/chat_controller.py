"""
app/controllers/chat_controller.py
==================================
API cho GUAMAISON AI Ecommerce Assistant.

Endpoint:
- POST /api/bot
- GET  /api/bot/health
"""

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from app import csrf
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import AdvancedChatService

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


def _model_to_dict(model) -> Dict[str, Any]:
    """
    Hỗ trợ cả Pydantic v1 và v2.
    """
    if hasattr(model, "model_dump"):
        return model.model_dump()

    if hasattr(model, "dict"):
        return model.dict()

    return dict(model or {})


@chat_bp.route("/bot/health", methods=["GET"])
def bot_health():
    return jsonify({
        "success": True,
        "service": "GUAMAISON AI Chatbot",
        "endpoint": "/api/bot",
        "status": "online"
    }), 200


@chat_bp.route("/bot", methods=["POST"])
@csrf.exempt
def bot_reply():
    try:
        payload = request.get_json(silent=True) or {}

        try:
            chat_request = ChatRequest(**payload)
        except Exception as validation_error:
            logger.warning("[Chat API] Payload không hợp lệ: %s", validation_error)

            return jsonify({
                "reply": "Tin nhắn chưa hợp lệ. Bạn vui lòng nhập lại nội dung cần hỗ trợ nhé.",
                "intent": "error",
                "products": [],
                "action_data": {}
            }), 400

        session_id = str(chat_request.session_id or "anonymous_session").strip()
        message = str(chat_request.message or "").strip()

        if not message:
            return jsonify({
                "reply": "Bạn vui lòng nhập tin nhắn để GUAMAISON Stylist hỗ trợ nhé.",
                "intent": "error",
                "products": [],
                "action_data": {}
            }), 400

        if len(message) > 1200:
            return jsonify({
                "reply": "Tin nhắn hơi dài. Bạn vui lòng rút gọn nội dung để mình hỗ trợ chính xác hơn nhé.",
                "intent": "error",
                "products": [],
                "action_data": {}
            }), 413

        response_data = AdvancedChatService.process_message(
            session_id=session_id,
            message=message
        )

        if isinstance(response_data, ChatResponse):
            return jsonify(_model_to_dict(response_data)), 200

        if not isinstance(response_data, dict):
            logger.error("[Chat API] Service trả về sai định dạng: %s", type(response_data))

            return jsonify({
                "reply": "Hệ thống AI đang xử lý chưa ổn định. Bạn vui lòng thử lại sau nhé.",
                "intent": "error",
                "products": [],
                "action_data": {}
            }), 500

        response = ChatResponse(
            reply=response_data.get("reply") or "Mình đã nhận được yêu cầu của bạn.",
            intent=response_data.get("intent") or "general_chat",
            products=response_data.get("products") or [],
            action_data=response_data.get("action_data") or {}
        )

        return jsonify(_model_to_dict(response)), 200

    except Exception as e:
        logger.error("[Chat API Error] %s", e, exc_info=True)

        return jsonify({
            "reply": "Hệ thống AI đang bảo trì. Bạn có thể nhắn GUAMAISON qua Fanpage để được hỗ trợ nhanh nhất nhé.",
            "intent": "error",
            "products": [],
            "action_data": {}
        }), 500
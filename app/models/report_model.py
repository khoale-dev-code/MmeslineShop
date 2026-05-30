"""
app/models/report_model.py
=========================
Xử lý dữ liệu Báo cáo & Thống kê Omnichannel bằng Pure Python (Tối ưu cho Vercel Serverless).
Không sử dụng Pandas để tránh lỗi vượt dung lượng container và tối ưu hóa tốc độ phản hồi.

CHANGELOG (Tối ưu hóa Lazy Initialization & Khắc phục bẫy RLS Báo cáo):
- Triển khai cơ chế Lazy Initialization qua hai lớp hàm _db() và _db_admin().
- Nâng cấp luồng get_dashboard_reports() chạy qua quyền admin nhằm bypass RLS khi quét dữ liệu nâng cao.
- Dọn sạch các bẫy import Top-Level, đảm bảo ứng dụng không phát sinh Cold Start mạng trên Vercel.
"""

import logging
from collections import defaultdict
from datetime import datetime
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class ReportModel:

    # ═══════════════════════════════════════════════════════════════
    #  LAZY INITIALIZATION HELPERS (KHỞI TẠO KẾT NỐI LƯỜI)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """Khởi tạo lười kết nối Client công khai (Dành cho hiển thị Storefront nếu có)"""
        return get_supabase()

    @staticmethod
    def _db_admin():
        """Khởi tạo lười kết nối Client quyền Admin (Dành cho việc tổng hợp báo cáo Workspace Admin)"""
        return get_supabase_admin()

    # ═══════════════════════════════════════════════════════════════
    #  CORE METHODS (XỬ LÝ DỮ LIỆU THỐNG KÊ)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_dashboard_reports() -> dict:
        # ✅ ĐÃ SỬA: Chuyển sang sử dụng Admin Client để bypass RLS đa bảng, chống lỗi hụt data báo cáo
        db = ReportModel._db_admin()
        try:
            # ── Kéo dữ liệu từ các bảng cần thiết ──
            analytics_res = db.table("product_analytics").select("*, products(name)").execute()
            orders_res = db.table("orders").select("id, total_amount, sales_channel, created_at, status, payment_status").execute()
            order_items_res = db.table("order_items").select("order_id, product_id, quantity, unit_price, products(name)").execute()

            analytics_data = analytics_res.data or []
            orders_data = orders_res.data or []
            order_items_data = order_items_res.data or []

            if not analytics_data and not orders_data:
                return ReportModel._get_fallback_data()

            valid_order_ids = set()
            channel_revenue = defaultdict(float)
            monthly_dict = defaultdict(float)
            order_channel_map = {}

            # ── BƯỚC 1: Lọc đơn hợp lệ và Tính doanh thu ──
            for o in orders_data:
                status = o.get("status")
                payment_status = o.get("payment_status")
                
                # Điều kiện hợp lệ: Đã giao/hoàn thành HOẶC đã thanh toán
                if status in ["delivered", "completed"] or payment_status == "paid":
                    oid = o.get("id")
                    valid_order_ids.add(oid)
                    
                    # Doanh thu theo kênh
                    channel = o.get("sales_channel") or "web"
                    order_channel_map[oid] = channel
                    amt = float(o.get("total_amount") or 0)
                    channel_revenue[channel] += amt
                    
                    # Doanh thu theo tháng
                    created_at_str = o.get("created_at")
                    if created_at_str:
                        try:
                            dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            month_key = dt.strftime("%Y-%m")  # Lưu YYYY-MM để sắp xếp chuẩn xác
                            monthly_dict[month_key] += amt
                        except ValueError:
                            pass

            # Sắp xếp và lấy dữ liệu của 12 tháng gần nhất
            sorted_months = sorted(monthly_dict.keys())[-12:]
            monthly_stats = []
            for ym in sorted_months:
                dt_obj = datetime.strptime(ym, "%Y-%m")
                monthly_stats.append({
                    "month": dt_obj.strftime("%m/%Y"),  # Đổi định dạng thành MM/YYYY cho giao diện UI
                    "revenue": monthly_dict[ym]
                })

            # ── BƯỚC 2: Tính số lượng bán thực tế từ order_items ──
            sold_by_product = defaultdict(int)
            for item in order_items_data:
                if item.get("order_id") in valid_order_ids:
                    sold_by_product[item.get("product_id")] += int(item.get("quantity") or 0)

            # ── BƯỚC 3: Funnel & AI Score từ product_analytics ──
            funnel_by_channel = defaultdict(lambda: {"views": 0, "add_to_carts": 0, "sold": 0})
            best_production_dict = {}
            product_likes = defaultdict(int)

            if analytics_data:
                for a in analytics_data:
                    channel = a.get("channel") or "web"
                    prod_data = a.get("products")
                    prod_name = prod_data.get("name") if isinstance(prod_data, dict) else "Unknown"
                    pid = a.get("product_id")
                    
                    views = int(a.get("views") or 0)
                    carts = int(a.get("add_to_carts") or 0)
                    likes = int(a.get("wishlist_count") or 0)
                    
                    # Hợp nhất sold (Lấy MAX giữa hệ thống tracking online và thực tế hóa đơn quầy)
                    sold_actual = sold_by_product.get(pid, 0)
                    sold_tracking = int(a.get("sold") or 0)
                    final_sold = max(sold_actual, sold_tracking)

                    # Funnel Aggregation
                    funnel_by_channel[channel]["views"] += views
                    funnel_by_channel[channel]["add_to_carts"] += carts
                    funnel_by_channel[channel]["sold"] += final_sold

                    # AI Score Calculation (Thuật toán đề xuất sản phẩm tối ưu)
                    ai_score = (final_sold * 0.5) + (likes * 0.3) + (views * 0.2)
                    
                    # Tìm best product per channel dựa theo điểm số AI
                    if channel not in best_production_dict or ai_score > best_production_dict[channel]["ai_score"]:
                        best_production_dict[channel] = {
                            "channel": channel,
                            "product_name": prod_name,
                            "ai_score": ai_score,
                            "sold": final_sold,
                            "views": views
                        }
                        
                    # Tổng hợp lượt yêu thích
                    product_likes[prod_name] += likes

                # Format cấu trúc dữ liệu phễu chuyển đổi (Funnel Data)
                funnel_data = []
                for ch, data in funnel_by_channel.items():
                    v = max(data["views"], 1)  # Đặt mức trần 1 để phòng hờ lỗi chia cho 0
                    c = max(data["add_to_carts"], 1)
                    funnel_data.append({
                        "channel": ch,
                        "views": data["views"],
                        "add_to_carts": data["add_to_carts"],
                        "sold": data["sold"],
                        "cr_view_to_cart": round((data["add_to_carts"] / v) * 100, 1),
                        "cr_cart_to_order": round((data["sold"] / c) * 100, 1),
                        "cr_total": round((data["sold"] / v) * 100, 1)
                    })
                
                best_production = list(best_production_dict.values())
                
                # Trích xuất Top 5 sản phẩm được yêu thích nhiều nhất
                sorted_likes = sorted(product_likes.items(), key=lambda x: x[1], reverse=True)
                most_liked = [{"product_name": k, "likes": v} for k, v in sorted_likes if v > 0][:5]

            # ── BƯỚC 4: Fallback nếu thiếu dữ liệu analytics nhưng có dữ liệu đơn ──
            elif sold_by_product and order_items_data and valid_order_ids:
                for item in order_items_data:
                    oid = item.get("order_id")
                    if oid in valid_order_ids:
                        ch = order_channel_map.get(oid, "pos")
                        qty = int(item.get("quantity") or 0)
                        funnel_by_channel[ch]["sold"] += qty
                        funnel_by_channel[ch]["views"] += 1
                        funnel_by_channel[ch]["add_to_carts"] += qty
                        
                funnel_data = []
                for ch, data in funnel_by_channel.items():
                    funnel_data.append({
                        "channel": ch,
                        "views": data["views"],
                        "add_to_carts": data["add_to_carts"],
                        "sold": data["sold"],
                        "cr_view_to_cart": 100.0,
                        "cr_cart_to_order": 100.0,
                        "cr_total": 100.0
                    })
                best_production = []
                most_liked = []
            else:
                funnel_data = []
                best_production = []
                most_liked = []

            return {
                "channel_revenue": dict(channel_revenue),
                "monthly_stats": monthly_stats,
                "funnel": funnel_data,
                "production_suggestions": best_production,
                "most_liked": most_liked,
            }

        except Exception as e:
            logger.error(f"[ReportModel] Lỗi xử lý dữ liệu báo cáo: {e}", exc_info=True)
            return ReportModel._get_fallback_data()

    @staticmethod
    def _get_fallback_data():
        """Dữ liệu dự phòng mặc định chống sập lỗi trang khi DB trống"""
        return {
            "channel_revenue": {"web": 0, "pos": 0, "tiktok": 0},
            "monthly_stats": [],
            "funnel": [],
            "production_suggestions": [],
            "most_liked": [],
        }
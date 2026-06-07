<div align="center">

<br/>
<br/>

```
███╗   ███╗███╗   ███╗███████╗███████╗████████╗██╗     ██╗███╗   ██╗███████╗
████╗ ████║████╗ ████║██╔════╝██╔════╝╚══██╔══╝██║     ██║████╗  ██║██╔════╝
██╔████╔██║██╔████╔██║█████╗  ███████╗   ██║   ██║     ██║██╔██╗ ██║█████╗  
██║╚██╔╝██║██║╚██╔╝██║██╔══╝  ╚════██║   ██║   ██║     ██║██║╚██╗██║██╔══╝  
██║ ╚═╝ ██║██║ ╚═╝ ██║███████╗███████║   ██║   ███████╗██║██║ ╚████║███████╗
╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝   ╚═╝   ╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝
```

**Nền tảng thương mại điện tử thời trang — Hiện đại · Đẳng cấp · Trọn vẹn**

<br/>

[![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask_3.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://vercel.com)

[![VNPay](https://img.shields.io/badge/VNPay-Integrated-005BAC?style=flat-square)](https://vnpay.vn)
[![SePay](https://img.shields.io/badge/SePay_Webhook-Integrated-111111?style=flat-square)](https://sepay.vn)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/your-username/fashion_store?style=flat-square&color=f59e0b)](https://github.com/your-username/fashion_store)

<br/>

> *Từ trải nghiệm mua sắm đến vận hành nội bộ — tất cả trong một hệ thống.*

<br/>

</div>

---

## ✦ Tổng quan

**MMÉSTLINE** là nền tảng thương mại điện tử thời trang full-stack, được thiết kế để đáp ứng toàn bộ chu kỳ bán hàng — từ hiển thị sản phẩm, giỏ hàng, đặt hàng, đến tích hợp thanh toán và quản trị nội bộ.

Kiến trúc được phân tầng rõ ràng theo mô hình **Controller → Service → Repository → Model**, đảm bảo tách biệt hoàn toàn giữa logic giao diện, nghiệp vụ và dữ liệu. Hệ thống được xây dựng trên **Flask** + **Jinja2** + **TailwindCSS** với backend lưu trữ trên **Supabase PostgreSQL**.

<br/>

```
Trình duyệt  ──►  Flask App  ──►  Controller  ──►  Service  ──►  Repository  ──►  Supabase
                                       │
                                  Middleware
                               (Auth · CSRF · Role)
```

<br/>

---

## ✦ Tính năng

<table>
<tr>
<td width="50%" valign="top">

### 🛍️ Storefront
- Hero banner, video nền, bộ sưu tập nổi bật
- Danh sách sản phẩm: lọc, tìm kiếm, phân trang
- Chi tiết sản phẩm: ảnh, màu sắc, kích thước, tồn kho
- Quick View: chọn màu/size, thêm giỏ, yêu thích
- Giỏ hàng theo tài khoản người dùng
- Checkout nhiều bước với địa chỉ và phí vận chuyển

### 💳 Thanh toán
- Thanh toán khi nhận hàng (COD)
- Tích hợp **VNPay** (redirect + checksum)
- Tích hợp **SePay** (QR chuyển khoản + webhook)
- Theo dõi trạng thái thanh toán theo đơn
- Ghi nhận lịch sử giao dịch để đối soát

</td>
<td width="50%" valign="top">

### ⚙️ Quản trị
- Dashboard tổng quan
- Quản lý sản phẩm, biến thể, ảnh, tồn kho, mã vạch
- Quản lý danh mục và bộ sưu tập
- Quản lý đơn hàng, khách hàng, đổi trả, vận chuyển
- Quản lý khuyến mãi, thông báo, cài đặt storefront
- POS tại quầy · Phân quyền · Nhật ký hệ thống

### 🔧 Vận hành
- Quản lý địa chỉ và thông tin cá nhân
- Yêu thích sản phẩm
- Thông báo nội bộ
- Đổi / trả hàng
- Loyalty: tích điểm, hạng thành viên
- Analytics: lượt xem, thêm giỏ, yêu thích, doanh số

</td>
</tr>
</table>

---

## ✦ Công nghệ

| Nhóm | Stack |
|---|---|
| **Backend** | Flask 3.x · Jinja2 · Python 3.10+ |
| **Database** | Supabase PostgreSQL |
| **Storage** | Supabase Storage |
| **Frontend** | TailwindCSS · Vanilla JavaScript · Font Awesome |
| **Auth** | Flask Session · bcrypt |
| **Payment** | VNPay · SePay Webhook |
| **Deploy** | Vercel · Python-compatible server |
| **Reports** | Pandas · OpenPyXL *(optional)* |
| **Utils** | python-dotenv · httpx · email-validator |

---

## ✦ Kiến trúc hệ thống

```
fashion_store/
│
├── run.py                         ← Entry point
├── requirements.txt
├── vercel.json
├── .env.example
│
├── config/
│   └── settings.py
│
├── app/
│   ├── __init__.py
│   │
│   ├── controllers/               ← Xử lý request / response
│   │   ├── auth_controller.py
│   │   ├── product_controller.py
│   │   ├── cart_controller.py
│   │   ├── payment_controller.py
│   │   ├── profile_controller.py
│   │   ├── favorite_controller.py
│   │   ├── analytics_controller.py
│   │   └── admin_controller.py
│   │
│   ├── models/                    ← Data classes & schema
│   │   ├── user_model.py
│   │   ├── product_model.py
│   │   ├── cart_model.py
│   │   ├── order_model.py
│   │   ├── address_model.py
│   │   ├── setting_model.py
│   │   └── notification_model.py
│   │
│   ├── services/                  ← Business logic
│   │   ├── favorite_service.py
│   │   ├── shipping_service.py
│   │   ├── vnpay_service.py
│   │   ├── sepay_service.py
│   │   └── loyalty_service.py
│   │
│   ├── repositories/              ← Database queries
│   │   └── favorite_repository.py
│   │
│   ├── middleware/                ← Auth & role guards
│   │   └── auth_required.py
│   │
│   ├── utils/
│   │   ├── supabase_client.py
│   │   └── security.py
│   │
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   └── video/
│   │
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── partials/
│       ├── components/
│       ├── products/
│       ├── cart/
│       ├── profile/
│       ├── auth/
│       └── admin/
│
└── migrations/
    └── *.sql
```

---

## ✦ Bắt đầu nhanh

### 1 — Clone dự án

```bash
git clone https://github.com/your-username/fashion_store.git
cd fashion_store
```

### 2 — Tạo môi trường ảo

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3 — Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### 4 — Cấu hình môi trường

```bash
cp .env.example .env
# Mở .env và điền các biến bên dưới
```

### 5 — Khởi tạo database

Mở **Supabase Dashboard → SQL Editor**, chạy toàn bộ file `.sql` trong thư mục `migrations/` theo thứ tự.

### 6 — Chạy server

```bash
python run.py
```

> Ứng dụng chạy tại `http://127.0.0.1:5000`

---

## ✦ Biến môi trường

```env
# ─── Flask ─────────────────────────────────────────────────────────
FLASK_DEBUG=True
SECRET_KEY=your-secret-key
SESSION_TYPE=filesystem

# ─── Supabase ──────────────────────────────────────────────────────
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# ─── App ───────────────────────────────────────────────────────────
APP_URL=http://127.0.0.1:5000

# ─── VNPay ─────────────────────────────────────────────────────────
VNPAY_TMN_CODE=your-vnpay-tmn-code
VNPAY_HASH_SECRET=your-vnpay-hash-secret
VNPAY_PAYMENT_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://127.0.0.1:5000/payment/vnpay_return

# ─── SePay ─────────────────────────────────────────────────────────
SEPAY_BANK_CODE=your-bank-code
SEPAY_BANK_ACCOUNT=your-bank-account
SEPAY_BANK_NAME=your-bank-name
SEPAY_ACCOUNT_NAME=your-account-name
SEPAY_WEBHOOK_API_KEY=your-webhook-secret

# ─── Mail (optional) ───────────────────────────────────────────────
MAIL_SERVER=
MAIL_PORT=
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=
```

> ⚠️ **Không commit** `.env`, API key, service role key hoặc webhook secret lên bất kỳ repository nào.

---

## ✦ Phân quyền

| Vai trò | Mô tả |
|---|---|
| `user` | Khách hàng: mua sắm, hồ sơ, địa chỉ, đơn hàng |
| `staff` | Vận hành: xử lý đơn, POS tại quầy |
| `admin` | Quản lý sản phẩm, đơn hàng, khách hàng, báo cáo |
| `super_admin` | Toàn quyền hệ thống, phân quyền, nhật ký |

---

## ✦ Luồng đặt hàng

```
Khách hàng
  │
  ├─► Chọn sản phẩm → Chọn màu / size
  │
  ├─► Thêm vào giỏ hàng
  │
  ├─► Checkout: địa chỉ giao hàng + phí vận chuyển
  │
  ├─► Chọn phương thức thanh toán
  │         │
  │    ┌────┴────────────────────┐
  │    ▼                        ▼                        ▼
  │   COD                    VNPay                    SePay
  │    │                        │                        │
  │    │              Redirect cổng TT         Hiển thị QR chuyển khoản
  │    │              Xác nhận checksum         Nhận webhook xác nhận
  │    │                        │                        │
  │    └───────────────── Cập nhật trạng thái đơn ───────┘
  │
  └─► Xóa giỏ hàng → Chuyển trang thành công
```

---

## ✦ Luồng SePay Webhook

```
POST /api/sepay/webhook
        │
        ├─► Xác thực API key
        ├─► Đối chiếu mã đơn trong nội dung chuyển khoản
        ├─► Kiểm tra số tiền khớp tổng đơn
        ├─► Cập nhật payment_status = paid
        └─► Xóa giỏ → Trả về 200 OK
```

---

## ✦ Deploy

### Vercel

```bash
npm i -g vercel
vercel login
vercel --prod
```

Cấu hình biến môi trường tại: **Vercel Dashboard → Project → Settings → Environment Variables**

### Checklist trước khi deploy

- [ ] `APP_URL` trỏ đúng domain production
- [ ] `VNPAY_RETURN_URL` đã cập nhật theo domain production
- [ ] Webhook SePay đã cập nhật URL production
- [ ] `FLASK_DEBUG=False`
- [ ] Supabase RLS policy đã được kiểm tra
- [ ] Service role key chỉ dùng phía server

---

## ✦ Xử lý lỗi thường gặp

<details>
<summary><strong>Không lưu được địa chỉ</strong></summary>

- Bảng `user_addresses` có đúng cột đang insert không?
- RLS policy cho phép user thao tác địa chỉ của chính mình?
- Controller đã import đầy đủ thư viện?
- Payload từ form có đủ `full_name`, `phone`, `address_line`?

</details>

<details>
<summary><strong>Không hiển thị collection ở navbar</strong></summary>

- `global_collections` đã được inject qua context processor chưa?
- Template có dùng `default([])` để tránh lỗi undefined?
- Bảng `collections` có bản ghi nào với `is_active = true`?

</details>

<details>
<summary><strong>SePay không tự cập nhật đơn</strong></summary>

- Webhook URL có public và còn hoạt động không?
- API key webhook có đúng không?
- Nội dung chuyển khoản có chứa mã đơn hàng không?
- Số tiền giao dịch có khớp với tổng đơn không?
- Kiểm tra log endpoint `/api/sepay/webhook` để xem payload thực tế.

</details>

<details>
<summary><strong>VNPay thành công nhưng đơn chưa cập nhật</strong></summary>

- Checksum có hợp lệ không?
- `vnp_TxnRef` có khớp với `order_id` hoặc `order_code` không?
- `OrderModel.update_payment_status()` đã update đúng bảng và cột chưa?
- Supabase RLS có chặn thao tác update không?

</details>

---

## ✦ Quy ước code

```
Controller   →  Chỉ xử lý request / response, không chứa business logic
Service      →  Business logic thuần túy, không biết về HTTP
Repository   →  Toàn bộ truy vấn Supabase tập trung tại đây
Model        →  Data class, schema, không có side effect
Template     →  Render giao diện, hạn chế nhúng logic phức tạp
```

- Không hard-code secret, URL production hoặc API key
- Ưu tiên partial / component cho UI dùng lại nhiều lần
- Không expose Supabase service role key ra frontend

---

## ✦ Roadmap

- [ ] Hoàn thiện module loyalty và tích điểm thành viên
- [ ] Tối ưu báo cáo doanh thu theo ngày, tháng, kênh bán
- [ ] Nâng cấp POS tại quầy
- [ ] Tự động gửi email xác nhận đơn hàng
- [ ] Tự động đồng bộ trạng thái giao hàng từ đơn vị vận chuyển
- [ ] Tối ưu SEO cho trang sản phẩm và bộ sưu tập
- [ ] Tách CSS/JS lớn thành static assets độc lập

---

## ✦ Giao diện

| Khu vực | Mô tả |
|---|---|
| **Trang chủ** | Hero video/banner, bộ sưu tập, sản phẩm nổi bật, CTA |
| **Shop** | Danh sách, lọc, tìm kiếm, quick view |
| **Chi tiết sản phẩm** | Ảnh, màu, size, tồn kho, thêm giỏ |
| **Giỏ hàng** | Cập nhật số lượng, xóa sản phẩm |
| **Checkout** | Địa chỉ, phí ship, phương thức thanh toán |
| **Hồ sơ** | Thông tin cá nhân, mật khẩu, địa chỉ, đơn hàng, yêu thích |
| **Admin Panel** | Dashboard, sản phẩm, đơn hàng, khách hàng, cài đặt |

---

## ✦ Bảo mật

| Lớp | Cơ chế |
|---|---|
| Mật khẩu | Hash bằng `bcrypt` |
| Form | CSRF token trên các form quan trọng |
| Session | Server-side session |
| Cookie | `HttpOnly` · `SameSite=Lax` |
| Route | Middleware phân quyền theo vai trò |
| API | Webhook thanh toán yêu cầu API key riêng |
| Database | Supabase RLS policy theo từng bảng |

---

<div align="center">

<br/>

**MMÉSTLINE** — Built with craft, deployed with confidence.

<br/>

[MIT License](./LICENSE) &nbsp;·&nbsp; © 2026 MMÉSTLINE

<br/>
<br/>

</div>
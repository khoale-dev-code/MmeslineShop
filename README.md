<div align="center">

<img src="./app/static/images/logo.svg" alt="GUAMAISON logo" width="112" />

# GUAMAISON

### Fashion commerce, built for both shoppers and operators.

**Nền tảng thương mại điện tử thời trang full-stack** kết hợp storefront hiện đại, quản trị vận hành, POS, thanh toán Việt Nam và trợ lý mua sắm AI trong một hệ thống thống nhất.

[![Python](https://img.shields.io/badge/Python-3.10%2B-1b4922?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-123418?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-1b4922?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-Responsive-c99e14?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Vercel](https://img.shields.io/badge/Vercel-Deploy-123418?style=flat-square&logo=vercel&logoColor=white)](https://vercel.com/)
[![Portfolio](https://img.shields.io/badge/Project-Full--stack_Portfolio-c99e14?style=flat-square)](#recruiter-fast-track)

[Điểm nổi bật](#highlights) · [Tính năng](#feature-map) · [Kiến trúc](#architecture) · [Cài đặt](#quick-start) · [Bảo mật](#security) · [Roadmap](#roadmap)

</div>

---

<a id="overview"></a>

## Một sản phẩm, hai trải nghiệm hoàn chỉnh

GUAMAISON không chỉ là một website trưng bày sản phẩm. Dự án mô phỏng toàn bộ vòng đời của một hệ thống bán lẻ thời trang: khách hàng khám phá và mua sắm, trong khi đội ngũ nội bộ quản lý catalog, tồn kho, đơn hàng, khách hàng, nội dung, khuyến mãi và bán hàng tại quầy.

| Góc nhìn sản phẩm | Phạm vi triển khai |
| --- | --- |
| **Customer experience** | Tìm kiếm, lọc, biến thể màu/size, Quick View, yêu thích, giỏ hàng, checkout, thanh toán và theo dõi đơn |
| **Commerce operations** | Sản phẩm, kho, coupon, đơn hàng, đổi trả, vận chuyển, khách hàng, thông báo và báo cáo |
| **Omnichannel** | Storefront trực tuyến kết hợp POS tại quầy, đồng bộ sản phẩm, khách hàng, tồn kho và loyalty |
| **Intelligent experience** | AI Assistant và Styling Lab có thể hoạt động với Gemini hoặc fallback nội bộ |
| **Vietnam-ready payments** | COD, VNPay redirect/checksum và SePay QR/webhook |

> **Engineering focus:** biến một bài toán e-commerce nhiều luồng nghiệp vụ thành codebase Flask có ranh giới rõ ràng, bảo mật theo vai trò và khả năng vận hành thực tế.

<a id="highlights"></a>

## Điều làm GUAMAISON khác biệt

### 1. Thanh toán được xử lý như một workflow, không phải một nút bấm

- **VNPay:** tạo URL thanh toán phía server, xác minh checksum khi callback và chỉ hoàn tất đơn khi chữ ký hợp lệ.
- **SePay:** nhận webhook, xác thực API key, tách mã đơn, đối chiếu số tiền và bỏ qua giao dịch đã ghi nhận.
- Sau khi xác nhận thanh toán, hệ thống đồng bộ trạng thái đơn, log giao dịch, tồn kho, analytics, coupon usage và giỏ hàng.

### 2. Admin là một sản phẩm riêng

- Dashboard, báo cáo, quản lý sản phẩm/biến thể, tồn kho, đơn hàng và khách hàng.
- RBAC theo permission code cho `staff`, `admin` và nhóm quyền tùy chỉnh.
- Audit log ghi nhận thao tác quản trị.
- Storefront CMS cho menu, footer, media, thông báo và cấu hình hiển thị.
- POS hỗ trợ barcode/SKU, coupon, loyalty, tiền mặt, chuyển khoản và giao hàng sau.

### 3. AI có graceful fallback

- AI Assistant hỗ trợ tìm sản phẩm, tư vấn size, phối đồ, chính sách và tra cứu đơn.
- Styling Lab xếp hạng gợi ý theo style profile và dữ liệu sản phẩm.
- Nếu chưa cấu hình Gemini, hệ thống chuyển sang rule-based fallback thay vì làm hỏng trải nghiệm chính.

### 4. Tối ưu cho vận hành thật

- Adapter vận chuyển tách biệt cho GHN, tự giao và mock provider.
- Global context cache giúp giảm truy vấn Supabase lặp lại.
- Cache được invalidation sau khi Admin cập nhật storefront để nội dung mới xuất hiện ngay.
- Static assets có cache header dài hạn khi deploy trên Vercel.

<a id="feature-map"></a>

## Feature map

| Khu vực | Tính năng tiêu biểu |
| --- | --- |
| 🛍️ **Storefront** | Hero/banner, collection, search, filter, pagination, Quick View, snackbar, responsive navigation |
| 👕 **Catalog** | Sản phẩm, category, collection, product group, ảnh, biến thể màu/size, size chart, SKU, barcode, tồn kho |
| 🛒 **Cart & checkout** | Giỏ hàng theo người dùng, cập nhật line item, địa chỉ giao hàng, phí vận chuyển, coupon, tạo đơn |
| 💳 **Payments** | COD, VNPay, SePay QR/webhook, payment log, trạng thái thanh toán, xử lý giao dịch trùng |
| 👤 **Customer account** | Đăng ký/đăng nhập, hồ sơ, đổi mật khẩu, sổ địa chỉ, yêu thích, lịch sử và chi tiết đơn |
| 🎁 **Growth** | Coupon, promotion, newsletter, notification, loyalty point và member tier |
| 🚚 **Operations** | Đơn hàng, shipment, shipping provider, tồn kho, đổi/trả, customer management |
| 🧾 **POS** | Tra cứu SKU/barcode, khách hàng nhanh, coupon, loyalty, VAT, tiền khách đưa, giao hàng sau |
| 📊 **Analytics** | Product events, doanh thu, báo cáo vận hành, xuất dữ liệu Excel và dashboard |
| 🧠 **AI experience** | Product discovery assistant, size/policy support, outfit suggestion, Styling Lab |
| 🧩 **Admin CMS** | Menu động, footer, storefront media, cài đặt hệ thống, role/permission và audit log |

<details>
<summary><strong>Xem hành trình mua hàng từ đầu đến cuối</strong></summary>

1. Khách hàng tìm hoặc lọc sản phẩm theo nhu cầu.
2. Chọn biến thể màu, kích thước và số lượng còn trong kho.
3. Thêm vào giỏ, áp coupon và chọn địa chỉ giao hàng.
4. Hệ thống tính phí vận chuyển và tạo snapshot thông tin line item.
5. Khách chọn COD, VNPay hoặc SePay.
6. Callback/webhook hợp lệ cập nhật payment, order, inventory và analytics.
7. Khách theo dõi đơn trong hồ sơ; Admin tiếp tục xử lý vận chuyển hoặc đổi trả.

</details>

<a id="architecture"></a>

## Kiến trúc

GUAMAISON chuẩn hóa module mới và các phần được refactor theo mô hình bốn tầng. Mục tiêu là giữ HTTP, nghiệp vụ và truy cập dữ liệu tách biệt để dễ kiểm thử, thay đổi và mở rộng.

```mermaid
flowchart TD
    A["HTTP / Jinja2 / JSON"] --> B["Controller — request, validation, response"]
    B --> C["Service — business rules"]
    C --> D["Repository — Supabase queries"]
    D --> E["Model — data & schema"]
    B -.-> F["Middleware — auth, CSRF, RBAC"]
```

| Tầng | Trách nhiệm | Không nên chứa |
| --- | --- | --- |
| **Controller** | Params, validation cơ bản, HTTP response, template/JSON | Business rule hoặc query Supabase |
| **Service** | Use case, workflow, tính toán và chính sách nghiệp vụ | `request`, `session` hoặc render template |
| **Repository** | Nơi tập trung mọi query Supabase | HTTP và logic trình bày |
| **Model** | Dataclass, schema và cấu trúc dữ liệu | Side effect hoặc điều phối workflow |

### Request lifecycle

```mermaid
sequenceDiagram
    participant U as Client
    participant M as Middleware
    participant C as Controller
    participant S as Service
    participant R as Repository
    U->>M: HTTP request
    M->>M: Auth · CSRF · permission
    M->>C: Valid request
    C->>S: Use case input
    S->>R: Data operation
    R-->>S: Domain data
    S-->>C: Result
    C-->>U: HTML or JSON
```

### Payment lifecycle

```mermaid
flowchart TD
    A["Checkout"] --> B{"Payment method"}
    B -->|COD| C["Order pending"]
    B -->|VNPay| D["Signed redirect"]
    B -->|SePay| E["QR + webhook"]
    D --> F["Verify checksum"]
    E --> G["Verify key + amount"]
    F --> H["Finalize order effects"]
    G --> H
    C --> I["Fulfilment"]
    H --> I
```

### Cấu trúc thư mục

```text
fashion_store/
├── index.py                       # Local entry point + Vercel WSGI app
├── config/                        # Environment-driven configuration
├── app/
│   ├── controllers/               # Storefront, API and admin controllers
│   ├── services/                  # Business workflows and integrations
│   │   └── shipping/              # GHN, self-ship and mock adapters
│   ├── repositories/              # Supabase data-access boundary
│   ├── models/                    # Domain data and schema helpers
│   ├── schemas/                   # Request/response schemas
│   ├── middleware/                # Authentication and permissions
│   ├── templates/                 # Jinja2 pages, partials and components
│   ├── static/                    # CSS, Vanilla JS, images and video
│   └── utils/                     # Security and Supabase clients
├── migrations/                    # Base SQL migrations
├── supabase/migrations/           # Incremental Supabase migrations
├── requirements.txt
└── vercel.json
```

<a id="stack"></a>

## Tech stack

| Layer | Technology |
| --- | --- |
| **Backend** | Python 3.10+, Flask 3.x, Flask-WTF, Flask-Session, Jinja2 |
| **Frontend** | Tailwind CSS, Vanilla JavaScript, Font Awesome, responsive Jinja2 components |
| **Data** | Supabase PostgreSQL, Supabase Storage |
| **Payments** | VNPay, SePay webhook, COD |
| **AI** | Google GenAI/Gemini with local fallback |
| **Operations** | APScheduler, SendGrid/email, Pandas, OpenPyXL, QR generation |
| **Deployment** | Vercel Python runtime, immutable static-asset cache |

<a id="recruiter-fast-track"></a>

## Recruiter fast track — xem gì trong 3 phút?

| Thời gian | Điểm nên xem | Vì sao đáng chú ý |
| --- | --- | --- |
| **30 giây** | `app/services/vnpay_service.py` | Chữ ký thanh toán được tạo và xác minh phía server |
| **30 giây** | `app/controllers/sepay_controller.py` | Webhook có API-key guard, amount reconciliation và duplicate protection |
| **30 giây** | `app/services/rbac_service.py` | Permission catalog, custom role và server-side authorization |
| **30 giây** | `app/controllers/admin/pos_controller.py` | Workflow bán tại quầy nhiều nghiệp vụ trong cùng một module |
| **30 giây** | `app/services/chat_service.py` | AI intent handling, product search và graceful fallback |
| **30 giây** | `index.py` + `vercel.json` | Context caching, cache invalidation và cấu hình serverless deployment |

<a id="quick-start"></a>

## Chạy dự án cục bộ

### Yêu cầu

- Python 3.10+
- Một Supabase project
- Git và virtual environment
- VNPay/SePay/Gemini chỉ cần khi muốn bật integration tương ứng

### 1. Tạo môi trường và cài dependency

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

### 2. Cấu hình môi trường

```env
# Core
FLASK_DEBUG=True
SECRET_KEY=replace-with-a-long-random-value
APP_URL=http://127.0.0.1:5000

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-server-only-service-role-key

# VNPay — optional
VNPAY_TMN_CODE=
VNPAY_HASH_SECRET=
VNPAY_PAYMENT_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://127.0.0.1:5000/payment/vnpay_return

# SePay — optional
SEPAY_BANK_CODE=
SEPAY_BANK_ACCOUNT=
SEPAY_ACCOUNT_NAME=
SEPAY_WEBHOOK_API_KEY=

# AI — optional; local fallback remains available
ENABLE_AI=false
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
```

> Không commit `.env`, Supabase service-role key, payment secret hoặc webhook key. Chỉ sử dụng service-role key trong code chạy phía server.

### 3. Khởi tạo database

1. Mở **Supabase Dashboard → SQL Editor**.
2. Chạy migration nền trong `migrations/` theo thứ tự.
3. Chạy migration bổ sung trong `supabase/migrations/` theo timestamp.
4. Kiểm tra lại bảng, Storage bucket và RLS policy trước khi dùng dữ liệu thật.

### 4. Chạy Flask

```bash
python index.py
```

Mở `http://127.0.0.1:5000`.

<details>
<summary><strong>Các nhóm biến môi trường khác</strong></summary>

- SMTP/SendGrid cho email và newsletter.
- GHN hoặc provider giao vận được chọn.
- POS loyalty rate, point value, store account và VAT mặc định.
- Global context cache TTL và giới hạn upload.
- Feature flags cho AI, analytics và tích hợp tùy chọn.

Hãy dùng `.env.example` làm nguồn cấu hình chuẩn và cập nhật file này khi thêm biến mới.

</details>

<a id="security"></a>

## Security & reliability

| Rủi ro | Cách hệ thống xử lý |
| --- | --- |
| **Secret leakage** | Đọc secret qua environment; service-role key chỉ dùng server-side |
| **Form forgery** | Flask-WTF CSRF token cho form; chỉ exempt endpoint webhook cần thiết |
| **Unauthorized admin access** | Middleware đăng nhập + RBAC theo permission code |
| **Payment tampering** | VNPay checksum validation; SePay API key và amount reconciliation |
| **Duplicate webhook** | Kiểm tra transaction đã tồn tại trước khi ghi payment |
| **Password exposure** | Hash mật khẩu bằng bcrypt |
| **Unsafe upload** | Allowlist extension/MIME, giới hạn dung lượng và upload Storage phía server |
| **Sensitive mutations** | Audit log cho thao tác Admin/Staff |
| **Database access** | RLS cần được review sau mỗi migration; service role không được expose ra browser |

### Production checklist

- [ ] `FLASK_DEBUG=False` và `SECRET_KEY` đủ mạnh.
- [ ] RLS policy đã được audit cho mọi bảng public-facing.
- [ ] VNPay return URL và SePay webhook trỏ đúng production domain.
- [ ] Payment secrets chỉ tồn tại trong environment của server.
- [ ] Storage policy và giới hạn upload đã được kiểm tra.
- [ ] Không commit `.env`, `.gua-backups/`, dump database hoặc file người dùng upload.
- [ ] Chạy test checkout/payment trên sandbox trước khi nhận giao dịch thật.

<a id="engineering-notes"></a>

## Những quyết định kỹ thuật đáng chú ý

- **Progressive enhancement:** Jinja2 render nội dung chính; Vanilla JS nâng cấp tương tác thay vì bắt buộc SPA framework.
- **Reusable UI:** navbar, footer, modal, snackbar và home sections được tách thành partial/component.
- **Integration isolation:** payment, shipping, email và AI được đặt sau service/adapter để dễ thay thế.
- **Defensive workflows:** payment side effects chỉ chạy sau bước xác minh; lỗi tích hợp tùy chọn không làm sập storefront.
- **Operational consistency:** POS và online commerce dùng chung domain data cho sản phẩm, kho, khách hàng và loyalty.
- **Performance awareness:** global context cache, explicit cache invalidation và immutable static assets trên Vercel.

<a id="roadmap"></a>

## Next engineering milestones

- [ ] Di chuyển nốt các truy vấn Supabase legacy khỏi Controller/Model vào Repository.
- [ ] Bổ sung unit test cho Service và integration test cho VNPay/SePay webhook.
- [ ] Thêm CI chạy lint, test, migration check và secret scanning cho pull request.
- [ ] Chuẩn hóa transaction/RPC cho checkout, POS và inventory side effects.
- [ ] Upload media lớn trực tiếp tới Supabase Storage để phù hợp giới hạn serverless.
- [ ] Bổ sung observability: structured logging, error tracking và payment alert.
- [ ] Hoàn thiện screenshot/GIF product tour và public demo environment.

<a id="conventions"></a>

## Quy ước đóng góp

```text
Controller  → HTTP only
Service     → Pure business logic
Repository  → Supabase access only
Model       → Data and schema only
Template    → Presentation with reusable partials
```

Một thay đổi được xem là hoàn chỉnh khi:

- Không hardcode secret hoặc production URL.
- Có validation và permission guard phù hợp.
- Không gọi Supabase trực tiếp ngoài Repository đối với code mới/refactor.
- Form mutation có CSRF; webhook có cơ chế xác thực riêng.
- UI hoạt động tốt trên desktop/mobile và có keyboard focus rõ ràng.
- Migration được thêm mới theo thứ tự; không sửa migration đã chạy trên production.

---

<div align="center">

### Built with product thinking, not only code.

**GUAMAISON © 2026** · Flask · Supabase · Vanilla JS · Vietnam-ready commerce

<sub>A portfolio project demonstrating full-stack engineering, commerce workflows and operational UX.</sub>

</div>

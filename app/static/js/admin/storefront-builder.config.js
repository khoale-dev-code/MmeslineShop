// app/static/js/admin/storefront-builder.config.js

window.StorefrontBuilderConfig = {
  modules: [
    {
      type: "hero_slider",
      title: "Hero Banner",
      subtitle: "Banner lớn hoặc hero nhỏ, có ảnh/video riêng",
      icon: "fa-panorama",
      defaults: {
        heading: "New Collection",
        subheading: "Khám phá phong cách mới từ GUAMAISON",
        media_url: "",
        media_type: "auto",
        button_text: "Mua ngay",
        link: "/shop",
        height: "large",
        align: "center",
        overlay: "medium"
      }
    },

    {
      type: "product_grid",
      title: "Sản phẩm",
      subtitle: "Danh sách sản phẩm nổi bật, mới nhất, bán chạy hoặc chọn thủ công",
      icon: "fa-shirt",
      defaults: {
        heading: "Sản phẩm nổi bật",
        source: "featured",
        product_ids: "",
        limit: 8,
        columns: 4,
        show_price: true,
        show_button: true,
        link: "/shop"
      }
    },

    {
      type: "image_banner",
      title: "Banner hình",
      subtitle: "Một ảnh banner có link riêng",
      icon: "fa-image",
      defaults: {
        heading: "Ưu đãi đặc biệt",
        media_url: "",
        link: "/shop",
        height: "medium",
        rounded: true
      }
    },

    {
      type: "image_grid",
      title: "Lưới ảnh linh hoạt",
      subtitle: "Nhiều ảnh trong một block, kéo thả ảnh, chỉnh số cột và tỉ lệ",
      icon: "fa-border-all",
      defaults: {
        heading: "Bộ ảnh thương hiệu",
        layout: "grid",
        width_mode: "container",

        columns_desktop: 3,
        columns_tablet: 2,
        columns_mobile: 1,

        gap: 12,
        aspect_ratio: "1/1",
        custom_height: 320,
        image_fit: "cover",
        radius: 20,
        padding_y: 32,
        show_title: false,

        items: [
          {
            id: "img_1",
            image_url: "",
            title: "Ảnh 1",
            link: "/shop"
          },
          {
            id: "img_2",
            image_url: "",
            title: "Ảnh 2",
            link: "/shop"
          }
        ]
      }
    },

    {
      type: "split_banner",
      title: "Banner 2 cột",
      subtitle: "Hai banner đặt cạnh nhau, mỗi bên có ảnh và link riêng",
      icon: "fa-table-columns",
      defaults: {
        heading: "For Him & For Her",

        left_media_url: "",
        left_title: "For Him",
        left_link: "/shop",

        right_media_url: "",
        right_title: "For Her",
        right_link: "/shop"
      }
    },

    {
      type: "category_grid",
      title: "Danh mục",
      subtitle: "Hiển thị danh mục nổi bật",
      icon: "fa-layer-group",
      defaults: {
        heading: "Danh mục nổi bật",
        limit: 8,
        columns: 4,
        layout: "grid"
      }
    },

    {
      type: "collection_grid",
      title: "Bộ sưu tập",
      subtitle: "Hiển thị các collection đang active",
      icon: "fa-images",
      defaults: {
        heading: "Bộ sưu tập",
        limit: 6,
        columns: 3,
        layout: "grid"
      }
    },

    {
      type: "video_showcase",
      title: "Video Showcase",
      subtitle: "Video hoặc TVC thương hiệu",
      icon: "fa-circle-play",
      defaults: {
        heading: "Best Sellers",
        subheading: "Khám phá những thiết kế bán chạy",
        video_url: "",
        poster_url: "",
        link: "/shop"
      }
    },

    {
      type: "text_block",
      title: "Text / HTML",
      subtitle: "Khối nội dung tự do cho giới thiệu, thông báo hoặc campaign",
      icon: "fa-align-left",
      defaults: {
        heading: "Câu chuyện thương hiệu",
        content: "Nhập nội dung giới thiệu, thông báo hoặc mô tả chiến dịch.",
        align: "center",
        max_width: "medium"
      }
    },

    {
      type: "benefits",
      title: "Lợi ích mua hàng",
      subtitle: "Cam kết, đổi trả, vận chuyển, chất lượng",
      icon: "fa-gem",
      defaults: {
        heading: "Vì sao chọn GUAMAISON",
        style: "cards"
      }
    },

    {
      type: "cta",
      title: "CTA",
      subtitle: "Kêu gọi mua hàng, đăng ký hoặc xem bộ sưu tập",
      icon: "fa-bullhorn",
      defaults: {
        heading: "Tham gia cộng đồng GUAMAISON",
        subheading: "Nhận ưu đãi mới nhất và bộ sưu tập độc quyền.",
        button_text: "Đăng ký ngay",
        link: "/auth/register"
      }
    },

    {
      type: "spacer",
      title: "Khoảng trắng",
      subtitle: "Tạo khoảng cách giữa các block",
      icon: "fa-arrows-up-down",
      defaults: {
        height: 48
      }
    }
  ],

  defaultLayout: [
    {
      type: "hero_slider",
      overrides: {
        heading: "New Collection",
        subheading: "Khám phá phong cách mới từ GUAMAISON",
        media_url: "",
        button_text: "Mua ngay",
        link: "/shop",
        height: "large",
        align: "center",
        overlay: "medium"
      }
    },

    {
      type: "product_grid",
      overrides: {
        heading: "Sản phẩm nổi bật",
        source: "featured",
        limit: 8,
        columns: 4,
        show_price: true,
        show_button: true,
        link: "/shop"
      }
    },

    {
      type: "image_grid",
      overrides: {
        heading: "Bộ ảnh nổi bật",
        layout: "grid",
        width_mode: "container",
        columns_desktop: 3,
        columns_tablet: 2,
        columns_mobile: 1,
        gap: 12,
        aspect_ratio: "1/1",
        custom_height: 320,
        image_fit: "cover",
        radius: 20,
        padding_y: 32,
        show_title: false,
        items: [
          {
            id: "img_1",
            image_url: "",
            title: "Ảnh 1",
            link: "/shop"
          },
          {
            id: "img_2",
            image_url: "",
            title: "Ảnh 2",
            link: "/shop"
          },
          {
            id: "img_3",
            image_url: "",
            title: "Ảnh 3",
            link: "/shop"
          }
        ]
      }
    },

    {
      type: "image_banner",
      overrides: {
        heading: "Ưu đãi mùa này",
        media_url: "",
        link: "/shop",
        height: "medium",
        rounded: true
      }
    },

    {
      type: "product_grid",
      overrides: {
        heading: "Sản phẩm mới",
        source: "latest",
        limit: 8,
        columns: 4,
        show_price: true,
        show_button: true,
        link: "/shop"
      }
    },

    {
      type: "collection_grid",
      overrides: {
        heading: "Bộ sưu tập",
        limit: 6,
        columns: 3,
        layout: "grid"
      }
    },

    {
      type: "benefits",
      overrides: {
        heading: "Vì sao chọn GUAMAISON",
        style: "cards"
      }
    }
  ]
};
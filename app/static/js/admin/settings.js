/**
 * GUA Maison Admin Dashboard - Settings Management
 * File: app/static/js/admin/settings.js
 */

// Sử dụng IIFE (Immediately Invoked Function Expression) để bảo vệ phạm vi biến, tránh xung đột toàn cục
(function() {
    'use strict';

    // Hàm lấy CSRF Token bảo mật chống lỗi 400 Bad Request / 403 Forbidden
    function getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                      document.querySelector('input[name="csrf_token"]')?.value;
        if (token) {
            console.log(`[CSRF] ✅ Token found (length: ${token.length})`);
        } else {
            console.warn(`[CSRF] ❌ Token not found! Hãy chắc chắn đã thêm thẻ csrf_token vào Form.`);
        }
        return token;
    }

    // Định nghĩa Object điều hướng chức năng Settings
    const Settings = {
        init() {
            console.log("GUA Maison Admin Dashboard - Settings Module loaded successfully");
            this.bindEvents();
        },

        bindEvents() {
            // Tự động xem trước (Preview) khi chọn file hình ảnh/video mới
            const fileInputs = document.querySelectorAll('.settings-file-input');
            fileInputs.forEach(input => {
                input.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    const previewId = e.target.dataset.preview;
                    const previewEl = document.getElementById(previewId);
                    
                    if (file && previewEl) {
                        const url = URL.createObjectURL(file);
                        // Giải phóng bộ nhớ cũ để tối ưu RAM trình duyệt
                        const oldMedia = previewEl.querySelector('img, video');
                        if (oldMedia && oldMedia.src && oldMedia.src.startsWith('blob:')) {
                            URL.revokeObjectURL(oldMedia.src);
                        }

                        if (file.type.startsWith('video/')) {
                            previewEl.innerHTML = `<video src="${url}" controls class="w-full h-48 object-cover rounded-lg bg-neutral-900"></video>`;
                        } else if (file.type.startsWith('image/')) {
                            previewEl.innerHTML = `<img src="${url}" class="w-full h-48 object-cover rounded-lg" loading="lazy" />`;
                        }
                    }
                });
            });
        },

        // Hàm lưu cấu hình nâng cao nhận tham số tabName (ví dụ: 'storefront')
        async save(tabName) {
            const form = document.getElementById(`form-${tabName}`);
            if (!form) {
                console.error(`[Settings.save] Form 'form-${tabName}' không tồn tại trong DOM.`);
                return;
            }

            // Tạo FormData thu thập tất cả dữ liệu chữ và file media
            const formData = new FormData(form);
            
            // Giao diện trạng thái đang xử lý (Loading)
            const saveBtn = document.querySelector(`button[onclick*="Settings.save('${tabName}')"]`) || 
                            document.querySelector(`button[onclick*='Settings.save("${tabName}")']`);
            let originalBtnHtml = '';
            if (saveBtn) {
                originalBtnHtml = saveBtn.innerHTML;
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang lưu cấu hình...';
            }

            try {
                const csrfToken = getCSRFToken();

                // Gọi API bằng đường dẫn tương đối để tương thích mọi Domain (Vercel, Localhost, Custom Domain)
                const response = await fetch(`/admin/settings/update/${tabName}`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData // Gửi trực tiếp multipart/form-data
                });

                if (!response.ok) {
                    throw new Error(`Máy chủ phản hồi lỗi mạng HTTP: ${response.status}`);
                }

                const result = await response.json();

                if (result.success) {
                    // Thông báo thành công trực quan
                    if (typeof showToast === 'function') {
                        showToast(result.message || 'Cập nhật cấu hình thành công!', 'success');
                    } else {
                        alert(result.message || 'Cập nhật cấu hình thành công!');
                    }
                    
                    // Làm mới trang nếu backend yêu cầu cập nhật lại trạng thái giao diện gốc
                    if (result.reload) {
                        setTimeout(() => window.location.reload(), 1200);
                    }
                } else {
                    throw new Error(result.message || 'Phía máy chủ từ chối lưu dữ liệu cấu hình.');
                }

            } catch (error) {
                console.error(`[Settings.save] Lỗi nghiêm trọng:`, error);
                if (typeof showToast === 'function') {
                    showToast(error.message || 'Không thể lưu. Vui lòng kiểm tra lại kết nối mạng hoặc định dạng file!', 'error');
                } else {
                    alert(`Lỗi: ${error.message || 'Không thể kết nối hoặc lưu dữ liệu cấu hình.'}`);
                }
            } finally {
                // Khôi phục lại trạng thái ban đầu của nút bấm sau khi xử lý xong
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = originalBtnHtml;
                }
            }
        }
    };

    // 💡 GIẢI PHÁP QUAN TRỌNG: Gắn chặt Settings vào cửa sổ toàn cục (window)
    // Giúp các thuộc tính onclick="Settings.save(...)" trong HTML tìm thấy hàm chính xác ở mọi môi trường build
    window.Settings = Settings;

    // Kích hoạt Module khi cấu trúc trang tải xong
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => Settings.init());
    } else {
        Settings.init();
    }
})();
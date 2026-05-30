/**
 * GUA Maison Admin Dashboard - Settings Management
 * File: app/static/js/admin/settings.js
 */

// Hàm lấy CSRF Token từ meta tag hoặc input hidden chống lỗi bảo mật
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                  document.querySelector('input[name="csrf_token"]')?.value;
    if (token) {
        console.log(`[CSRF] ✅ Token found (length: ${token.length} )`); // Dòng 17 trong log của bạn
    } else {
        console.warn(`[CSRF] ❌ Token not found`);
    }
    return token;
}

// Định nghĩa Object điều hướng chức năng Settings
const Settings = {
    init() {
        console.log("GUA Maison Admin Dashboard loaded successfully");
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
                    if (file.type.startsWith('video/')) {
                        previewEl.innerHTML = `<video src="${url}" controls class="w-full h-48 object-cover rounded-lg"></video>`;
                    } else if (file.type.startsWith('image/')) {
                        previewEl.innerHTML = `<img src="${url}" class="w-full h-48 object-cover rounded-lg" />`;
                    }
                }
            });
        });
    },

    // Hàm lưu cấu hình nâng cao nhận tham số tabName (ví dụ: 'storefront')
    async save(tabName) {
        const form = document.getElementById(`form-${tabName}`);
        if (!form) {
            console.error(`[Settings.save] Form 'form-${tabName}' không tồn tại.`);
            return;
        }

        // Tạo FormData thu thập tất cả input text, file video/hình ảnh
        const formData = new FormData(form);
        
        // Giao diện trạng thái đang xử lý (Loading)
        const saveBtn = document.querySelector(`button[onclick="Settings.save('${tabName}')"]`);
        let originalBtnHtml = '';
        if (saveBtn) {
            originalBtnHtml = saveBtn.innerHTML;
            saveBtn.disabled = true;
            // Dùng icon font chữ thay thế SVG gãy tránh lỗi thuộc tính <path d:...> của trình duyệt
            saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang lưu...';
        }

        try {
            const csrfToken = getCSRFToken();

            /**
             * SỬA LỖI TẠI ĐÂY (Dòng 90):
             * Sử dụng đường dẫn tương đối `/admin/settings/update/${tabName}` thay vì ghi cứng localhost.
             * Trình duyệt sẽ tự động map theo domain hiện tại của bạn (không lo lệch port).
             */
            const response = await fetch(`/admin/settings/update/${tabName}`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData // Truyền trực tiếp FormData bao gồm cả file video dung lượng lớn
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                // Nếu backend xử lý thành công (Toast thông báo)
                if (typeof showToast === 'function') {
                    showToast(result.message || 'Cập nhật cấu hình thành công!', 'success');
                } else {
                    alert(result.message || 'Cập nhật cấu hình thành công!');
                }
                
                // Reload nhẹ lại trang nếu có yêu cầu từ phía server
                if (result.reload) {
                    setTimeout(() => window.location.reload(), 1000);
                }
            } else {
                throw new Error(result.message || 'Lưu thất bại từ phản hồi phía máy chủ.');
            }

        } catch (error) {
            // Khối bắt lỗi log console (Dòng 106 trong log của bạn)
            console.error(`[Settings.save] Error:`, error);
            
            if (typeof showToast === 'function') {
                showToast(error.message || 'Không thể lưu. Vui lòng kiểm tra lại kết nối hoặc dung lượng file video!', 'error');
            } else {
                alert('Lỗi: Không thể kết nối hoặc lưu dữ liệu cấu hình.');
            }
        } finally {
            // Phục hồi lại trạng thái nút bấm sau khi xử lý xong (dù thành công hay thất bại)
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalBtnHtml;
            }
        }
    }
};

// Khởi chạy khi DOM đã sẵn sàng
document.addEventListener('DOMContentLoaded', () => {
    Settings.init();
});
/**
 * GUA Maison Admin Dashboard - Settings Management
 * File: app/static/js/admin/settings.js
 * CHANGELOG: Fix lỗi FormData trống do disabled input + Fetch credentials
 */

(function() {
    'use strict';

    // ── Hàm quét và lấy CSRF Token tự động ──
    function getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                      document.querySelector('input[name="csrf_token"]')?.value;
        if (!token) {
            console.warn(`[CSRF] ❌ Token không tồn tại trong DOM!`);
        }
        return token;
    }

    // ── Hàm gọi thông báo UI linh hoạt ──
    function notify(message, type = 'success') {
        if (window.GUA && typeof window.GUA.snackbar === 'function') {
            window.GUA.snackbar(message, type);
        } else if (window.GUA && typeof window.GUA.toast === 'function') {
            window.GUA.toast(message, type);
        } else if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            alert(type === 'error' ? `⚠️ LỖI: ${message}` : `✅ ${message}`);
        }
    }

    const Settings = {
        currentTab: 'general',

        init() {
            console.log("🚀 GUA Maison - Settings Module Loaded");
            this.initTabs();
            this.bindEvents();
        },

        // ── LOGIC CHUYỂN TAB ──
        initTabs() {
            const navLinks = document.querySelectorAll('.s-nav');
            const panels = document.querySelectorAll('.s-panel');

            const switchTab = (tabId) => {
                panels.forEach(p => p.classList.remove('active'));
                navLinks.forEach(n => {
                    n.classList.remove('bg-white', 'shadow-sm', 'text-stone-900', 'font-bold');
                    n.classList.add('text-stone-500', 'hover:bg-stone-50', 'hover:text-stone-900');
                });

                const targetPanel = document.getElementById(`panel-${tabId}`);
                if (targetPanel) targetPanel.classList.add('active');

                const targetNav = document.querySelector(`.s-nav[data-tab="${tabId}"]`);
                if (targetNav) {
                    targetNav.classList.remove('text-stone-500', 'hover:bg-stone-50', 'hover:text-stone-900');
                    targetNav.classList.add('bg-white', 'shadow-sm', 'text-stone-900', 'font-bold');
                }
                
                this.currentTab = tabId;
                
                if (history.pushState) {
                    const newUrl = `${window.location.protocol}//${window.location.host}${window.location.pathname}?tab=${tabId}`;
                    window.history.pushState({path: newUrl}, '', newUrl);
                }
            };

            const params = new URLSearchParams(window.location.search);
            if (params.has('tab')) {
                switchTab(params.get('tab'));
            } else if (navLinks.length > 0) {
                switchTab(navLinks[0].dataset.tab);
            }

            navLinks.forEach(nav => {
                nav.addEventListener('click', function(e) {
                    e.preventDefault();
                    switchTab(this.dataset.tab);
                });
            });
            
            this.switchTab = switchTab;
        },

        // ── LOGIC XEM TRƯỚC HÌNH ẢNH (PREVIEW MEDIA) ──
        bindEvents() {
            const fileInputs = document.querySelectorAll('.settings-file-input');
            fileInputs.forEach(input => {
                input.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    const previewId = e.target.dataset.preview;
                    const previewEl = document.getElementById(previewId);
                    
                    if (file && previewEl) {
                        const url = URL.createObjectURL(file);
                        const oldMedia = previewEl.querySelector('img, video');
                        if (oldMedia && oldMedia.src && oldMedia.src.startsWith('blob:')) {
                            URL.revokeObjectURL(oldMedia.src);
                        }

                        if (file.type.startsWith('video/')) {
                            previewEl.innerHTML = `<video src="${url}" controls class="w-full h-48 object-cover rounded-lg bg-stone-950 shadow-sm border border-stone-200"></video>`;
                        } else if (file.type.startsWith('image/')) {
                            previewEl.innerHTML = `<img src="${url}" class="w-full h-48 object-cover rounded-lg shadow-sm border border-stone-200" loading="lazy" />`;
                        }
                    }
                });
            });
        },

        // ── LOGIC GỬI API LÊN SERVER ──
        async save(tabName) {
            const form = document.getElementById(`form-${tabName}`);
            if (!form) {
                console.error(`[Settings.save] Không tìm thấy Form id="form-${tabName}"`);
                return;
            }

            const saveBtn = document.querySelector(`button[onclick*="Settings.save('${tabName}')"]`) || 
                            document.querySelector(`button[onclick*='Settings.save("${tabName}")']`) ||
                            form.querySelector('button[type="submit"]');
            
            let originalBtnHtml = '';
            
            // 🟢 TẠO FORMDATA TRƯỚC KHI DISABLE INPUT ĐỂ KHÔNG BỊ RỖNG DỮ LIỆU
            if (tabName === 'storefront' && window.__storefrontUploadCount > 0) {
            notify('Ảnh/video đang tải lên. Vui lòng chờ báo tải lên thành công rồi bấm Lưu.', 'warning');
            return;
        }

            const formData = new FormData(form);
            const csrfToken = getCSRFToken();

            // 🔴 BÂY GIỜ MỚI KHÓA FORM
            const formElements = form.querySelectorAll('input, select, textarea, button');
            if (saveBtn) {
                originalBtnHtml = saveBtn.innerHTML;
                saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
                saveBtn.disabled = true;
            }
            formElements.forEach(el => el.disabled = true);

            try {
                const response = await fetch(`/admin/settings/update/${tabName}`, {
                    method: 'POST',
                    credentials: 'same-origin', // Gửi kèm session cookie để pass CSRF
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData 
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    throw new Error(errData.message || `Lỗi máy chủ HTTP ${response.status}`);
                }

                const result = await response.json();

                if (result.success) {
                    notify(result.message || 'Cập nhật cấu hình thành công!', 'success');
                    if (result.reload) {
                        setTimeout(() => window.location.reload(), 1200);
                    }
                } else {
                    throw new Error(result.message || 'Từ chối lưu dữ liệu cấu hình.');
                }

            } catch (error) {
                console.error(`[Settings.save ERROR]`, error);
                notify(error.message || 'Mất kết nối tới máy chủ. Vui lòng thử lại!', 'error');
            } finally {
                // UI: Mở khóa lại Form sau khi gửi xong
                formElements.forEach(el => el.disabled = false);
                if (saveBtn) {
                    saveBtn.innerHTML = originalBtnHtml;
                    saveBtn.disabled = false;
                }
            }
        }
    };

    window.Settings = Settings;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => Settings.init());
    } else {
        Settings.init();
    }
})();
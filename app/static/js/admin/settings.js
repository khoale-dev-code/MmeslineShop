/**
 * static/js/admin/settings.js
 * Version 2.2 – bổ sung debug CSRF token
 */
window.Settings = window.Settings || {};
const Settings = (() => {

  // ═══════════════════════════════════════════════════════════════
  //  CSRF TOKEN (có log)
  // ═══════════════════════════════════════════════════════════════
  function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    const token = meta?.getAttribute('content') || '';
    if (!token) {
      console.error('[CSRF] ❌ Không tìm thấy meta[name="csrf-token"] trong HTML');
    } else {
      console.log('[CSRF] ✅ Token found (length:', token.length, ')');
    }
    return token;
  }

  // ═══════════════════════════════════════════════════════════════
  //  TOAST NOTIFICATION
  // ═══════════════════════════════════════════════════════════════
  function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
      success: '<svg viewBox="0 0 16 16" fill="none"><path d="M3 8l4 4 6-7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      error:   '<svg viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
      info:    '<svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.2"/><path d="M8 7v4M8 5h.01" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    };

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      toast.addEventListener('animationend', () => toast.remove());
    }, 3200);
  }

  // ═══════════════════════════════════════════════════════════════
  //  TAB SWITCHING
  // ═══════════════════════════════════════════════════════════════
  function switchTab(tabName, clickedEl) {
    document.querySelectorAll('.s-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.s-nav__item').forEach(n => n.classList.remove('active'));

    const panel = document.getElementById(`panel-${tabName}`);
    if (panel) panel.classList.add('active');
    if (clickedEl) clickedEl.classList.add('active');

    history.replaceState(null, '', `#${tabName}`);
  }

  function initTabFromHash() {
    const hash = window.location.hash.replace('#', '');
    if (hash) {
      const navItem = document.querySelector(`[data-tab="${hash}"]`);
      if (navItem) switchTab(hash, navItem);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  LƯU DỮ LIỆU CÁC SECTION
  // ═══════════════════════════════════════════════════════════════
  async function save(section) {
    const form = document.getElementById(`form-${section}`);
    if (!form) return;

    const formData = new FormData(form);
    const data = {};
    formData.forEach((val, key) => { data[key] = val; });

    form.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      if (!cb.checked) data[cb.name] = 'false';
    });

    const token = getCSRFToken();
    if (!token) {
      showToast('Không tìm thấy token bảo mật. Vui lòng tải lại trang.', 'error');
      return;
    }

    try {
      // Đã chuẩn hóa Relative URL
      const res = await fetch(`/admin/settings/update/${section}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': token
        },
        body: JSON.stringify(data),
      });
      const json = await res.json();
      if (json.success) {
        showToast(json.message || `Đã lưu ${section}!`, 'success');
      } else {
        showToast(json.message || 'Có lỗi xảy ra khi lưu.', 'error');
      }
    } catch (err) {
      showToast('Lỗi kết nối máy chủ. Vui lòng thử lại.', 'error');
      console.error('[Settings.save] Error:', err);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  LANGUAGE TAB
  // ═══════════════════════════════════════════════════════════════
  function selectLanguage(lang, cardEl) {
    document.querySelectorAll('.lang-card').forEach(c => c.classList.remove('selected'));
    cardEl.classList.add('selected');
    const input = document.getElementById('selected_language');
    if (input) input.value = lang;
  }

  async function saveLanguage() {
    const lang    = document.getElementById('selected_language')?.value || 'vi';
    const dateF   = document.getElementById('date_format')?.value || 'DD/MM/YYYY';
    const timeF   = document.getElementById('time_format')?.value || '24h';

    const token = getCSRFToken();
    if (!token) {
      showToast('Không tìm thấy token bảo mật. Vui lòng tải lại trang.', 'error');
      return;
    }

    try {
      // Đã chuẩn hóa Relative URL
      const res = await fetch('/admin/settings/update/language', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': token
        },
        body: JSON.stringify({ admin_lang: lang, date_format: dateF, time_format: timeF }),
      });
      const json = await res.json();
      showToast(json.success ? 'Đã cập nhật ngôn ngữ Admin!' : (json.message || 'Lỗi lưu ngôn ngữ.'), json.success ? 'success' : 'error');
    } catch {
      showToast('Lỗi kết nối. Vui lòng thử lại.', 'error');
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  SHIPPING RULES
  // ═══════════════════════════════════════════════════════════════
  function getShippingRules() {
    return Array.from(document.querySelectorAll('#rulesBody .rule-row')).map(row => {
      try { return JSON.parse(row.dataset.rule); } catch { return null; }
    }).filter(Boolean);
  }

  function updateShippingStats() {
    const rules = getShippingRules();
    const el = id => document.getElementById(id);
    if (el('statsRuleCount'))  el('statsRuleCount').textContent  = rules.length;
    if (el('statsWarnCount'))  el('statsWarnCount').textContent  = rules.filter(r => r.type === 'warning').length;
    if (el('statsFeeCount'))   el('statsFeeCount').textContent   = rules.filter(r => r.type === 'custom_fee').length;
  }

  // Sử dụng 'change' thay vì onclick inline giúp tăng hiệu năng render
  function toggleFeeInput(selectEl) {
    const group = document.getElementById('feeAmountGroup');
    if (!group) return;
    group.style.display = selectEl.value === 'custom_fee' ? 'flex' : 'none';
  }

  function addShippingRule() {
    const province = document.getElementById('new_province')?.value.trim();
    const type     = document.getElementById('new_rule_type')?.value;
    const fee      = document.getElementById('new_fee_amount')?.value;
    const note     = document.getElementById('new_note')?.value.trim();

    if (!province) { showToast('Vui lòng nhập tên tỉnh / thành phố.', 'error'); return; }

    const rule = { province, type, fee: type === 'custom_fee' ? Number(fee) : null, note };

    const tbody = document.getElementById('rulesBody');
    const emptyRow = document.getElementById('emptyRow');
    if (emptyRow) emptyRow.remove();

    const tagMap = { warning: ['orange','Cảnh báo'], blocked: ['red','Không ship'], custom_fee: ['blue','Phí riêng'] };
    const [tagColor, tagLabel] = tagMap[type] || ['blue','Phí riêng'];

    const tr = document.createElement('tr');
    tr.className = 'rule-row';
    tr.dataset.rule = JSON.stringify(rule);
    tr.innerHTML = `
      <td class="rule-province">${escapeHtml(province)}</td>
      <td><span class="tag tag--${tagColor}">${tagLabel}</span></td>
      <td class="rule-fee">${rule.fee ? rule.fee.toLocaleString('vi-VN') + 'đ' : '<span class="text-muted">—</span>'}</td>
      <td class="rule-note text-muted">${escapeHtml(note || '—')}</td>
      <td><button class="btn-icon btn-icon--danger" onclick="Settings.removeShippingRule(this)" title="Xóa">
        <svg viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V2h4v2M5 4v9h6V4H5z" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button></td>
    `;
    tbody.appendChild(tr);

    ['new_province','new_fee_amount','new_note'].forEach(id => {
      const el = document.getElementById(id); if (el) el.value = '';
    });

    updateShippingStats();
    showToast(`Đã thêm luật cho "${province}".`, 'info');
  }

  function removeShippingRule(btn) {
    const row = btn.closest('.rule-row');
    if (!row) return;
    const name = row.querySelector('.rule-province')?.textContent || 'tỉnh này';
    row.remove();

    if (!document.querySelector('#rulesBody .rule-row')) {
      document.getElementById('rulesBody').innerHTML = `
        <tr id="emptyRow">
          <td colspan="5" class="table-empty"><span>Chưa có luật vận chuyển nào.</span></td>
        </tr>`;
    }
    updateShippingStats();
    showToast(`Đã xóa luật cho "${name}".`, 'info');
  }

  async function saveShipping() {
    const rules = getShippingRules();
    const token = getCSRFToken();
    if (!token) {
      showToast('Không tìm thấy token bảo mật. Vui lòng tải lại trang.', 'error');
      return;
    }
    try {
      // Đã chuẩn hóa Relative URL
      const res = await fetch('/admin/settings/update/shipping_rules', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': token
        },
        body: JSON.stringify({ rules }),
      });
      const json = await res.json();
      showToast(json.success ? 'Đã lưu luật vận chuyển!' : (json.message || 'Lỗi lưu luật ship.'), json.success ? 'success' : 'error');
    } catch {
      showToast('Lỗi kết nối. Vui lòng thử lại.', 'error');
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  PASSWORD TOGGLE
  // ═══════════════════════════════════════════════════════════════
  function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    btn.setAttribute('aria-label', isPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
    btn.style.opacity = isPassword ? '1' : '0.5';
  }

  // ═══════════════════════════════════════════════════════════════
  //  PREVIEW & CLOSE BANNER
  // ═══════════════════════════════════════════════════════════════
  function previewBannerUrl(inputId, previewId) {
    const url = document.getElementById(inputId)?.value.trim();
    const preview = document.getElementById(previewId);
    const img = document.getElementById(`${previewId}Img`);
    if (!url || !preview || !img) return;
    img.src = url;
    preview.style.display = 'block';
    img.onerror = () => showToast('Không tải được ảnh từ URL này.', 'error');
  }

  function closeBannerPreview(previewId) {
    const preview = document.getElementById(previewId);
    if (preview) preview.style.display = 'none';
  }

  // ═══════════════════════════════════════════════════════════════
  //  UPLOAD FILE
  // ═══════════════════════════════════════════════════════════════
  async function uploadFile(inputEl, targetInputId, previewId = '') {
    const file = inputEl.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      showToast('File quá lớn (tối đa 10MB).', 'error');
      return;
    }

    const token = getCSRFToken();
    if (!token) {
      showToast('Không tìm thấy token bảo mật. Vui lòng tải lại trang.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Đã chuẩn hóa Relative URL
      const res = await fetch('/admin/settings/upload', {
        method: 'POST',
        headers: { 'X-CSRFToken': token },
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        const targetInput = document.getElementById(targetInputId);
        if (targetInput) targetInput.value = data.url;
        showToast('Đã tải file lên thành công!', 'success');
        if (previewId && typeof previewBannerUrl === 'function') {
          previewBannerUrl(targetInputId, previewId);
        }
      } else {
        showToast(data.error || 'Upload thất bại.', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Lỗi kết nối server.', 'error');
    }
    inputEl.value = '';
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
      if (m === '&') return '&amp;';
      if (m === '<') return '&lt;';
      if (m === '>') return '&gt;';
      return m;
    });
  }

  function init() {
    initTabFromHash();
    updateShippingStats();
    getCSRFToken();
  }

  return {
    switchTab,
    save,
    saveLanguage,
    selectLanguage,
    saveShipping,
    addShippingRule,
    removeShippingRule,
    toggleFeeInput,
    togglePassword,
    previewBannerUrl,
    closeBannerPreview,
    uploadFile,
    init,
  };
})();

document.addEventListener('DOMContentLoaded', () => {
  Settings.init();
});
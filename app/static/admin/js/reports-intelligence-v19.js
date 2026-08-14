/* GUAMAISON Analytics Intelligence v19.0.0 */
(function () {
  "use strict";

  var root = document.querySelector("[data-analytics-version='19.0.0']");
  if (!root) return;

  var STORAGE_KEY = "guamaison.analytics.v19.export-config";
  var reportData = { trend: { points: [] }, channels: [], forecast: { points: [] }, filters: {} };
  var dataNode = document.getElementById("aiReportData");
  var toastTimer = null;

  try {
    reportData = JSON.parse(dataNode ? dataNode.textContent : "{}");
  } catch (error) {
    console.warn("[Analytics v19] Invalid chart payload", error);
  }

  function money(value) {
    return Number(value || 0).toLocaleString("vi-VN") + " ₫";
  }

  function showToast(message, isError) {
    var toast = root.querySelector("[data-report-toast]");
    if (!toast) return;
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.toggle("is-error", Boolean(isError));
    toast.hidden = false;
    toastTimer = window.setTimeout(function () { toast.hidden = true; }, 4200);
  }

  function chartDefaults() {
    if (!window.Chart) return;
    Chart.defaults.color = "#667263";
    Chart.defaults.font.family = "'Plus Jakarta Sans', Inter, system-ui, sans-serif";
    Chart.defaults.animation.duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 600;
  }

  function commonTooltip() {
    return {
      backgroundColor: "#0b2110",
      titleColor: "#f4e4aa",
      bodyColor: "#ffffff",
      padding: 12,
      cornerRadius: 12,
      displayColors: false
    };
  }

  function initRevenueChart() {
    var canvas = document.getElementById("aiRevenueChart");
    var points = (reportData.trend && reportData.trend.points) || [];
    if (!canvas || !window.Chart || !points.length) {
      if (canvas) canvas.parentElement.innerHTML = '<div class="ai-empty">Chưa có dữ liệu doanh thu trong kỳ.</div>';
      return;
    }
    var context = canvas.getContext("2d");
    var gradient = context.createLinearGradient(0, 0, 0, 360);
    gradient.addColorStop(0, "rgba(27,73,34,.25)");
    gradient.addColorStop(1, "rgba(27,73,34,0)");

    new Chart(canvas, {
      type: "line",
      data: {
        labels: points.map(function (point) { return point.label; }),
        datasets: [{
          label: "Doanh thu thuần",
          data: points.map(function (point) { return point.revenue; }),
          borderColor: "#1b4922",
          backgroundColor: gradient,
          borderWidth: 3,
          pointRadius: points.length > 24 ? 0 : 3,
          pointHoverRadius: 6,
          pointBackgroundColor: "#c99e14",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
          tension: .35,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(commonTooltip(), {
            callbacks: { label: function (context) { return money(context.raw); } }
          })
        },
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
          y: {
            beginAtZero: true,
            border: { display: false },
            grid: { color: "rgba(27,73,34,.08)" },
            ticks: { callback: function (value) { return Number(value / 1000000).toLocaleString("vi-VN") + " Tr"; } }
          }
        }
      }
    });
  }

  function initChannelChart() {
    var canvas = document.getElementById("aiChannelChart");
    var channels = reportData.channels || [];
    if (!canvas || !window.Chart || !channels.length) {
      if (canvas) canvas.parentElement.innerHTML = '<div class="ai-empty">Chưa có dữ liệu kênh bán.</div>';
      return;
    }
    var names = { web: "Website", pos: "POS", shopee: "Shopee", lazada: "Lazada", tiktok_shop: "TikTok Shop" };
    var colors = { web: "#1b4922", pos: "#c99e14", shopee: "#ee4d2d", lazada: "#0f146d", tiktok_shop: "#111111" };
    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: channels.map(function (row) { return names[row.channel] || row.channel.toUpperCase(); }),
        datasets: [{
          data: channels.map(function (row) { return row.net_revenue; }),
          backgroundColor: channels.map(function (row) { return colors[row.channel] || "#667263"; }),
          borderColor: "#ffffff",
          borderWidth: 5,
          borderRadius: 6,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(commonTooltip(), {
            callbacks: { label: function (context) { return " " + context.label + ": " + money(context.raw); } }
          })
        }
      }
    });
  }

  function initForecastChart() {
    var canvas = document.getElementById("aiForecastChart");
    var points = (reportData.forecast && reportData.forecast.points) || [];
    if (!canvas || !window.Chart || !points.length) return;
    new Chart(canvas, {
      type: "line",
      data: {
        labels: points.map(function (point) { return point.label; }),
        datasets: [
          { label: "Mức cao", data: points.map(function (point) { return point.high; }), borderColor: "rgba(201,158,20,.35)", borderDash: [5, 5], pointRadius: 0, tension: .25 },
          { label: "Cơ sở", data: points.map(function (point) { return point.revenue; }), borderColor: "#1b4922", backgroundColor: "rgba(27,73,34,.10)", borderWidth: 3, pointBackgroundColor: "#c99e14", tension: .25, fill: false },
          { label: "Mức thấp", data: points.map(function (point) { return point.low; }), borderColor: "rgba(27,73,34,.32)", borderDash: [5, 5], pointRadius: 0, tension: .25 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 7, font: { size: 9, weight: "700" } } },
          tooltip: Object.assign(commonTooltip(), { callbacks: { label: function (context) { return " " + context.dataset.label + ": " + money(context.raw); } } })
        },
        scales: {
          x: { grid: { display: false }, border: { display: false } },
          y: { beginAtZero: true, border: { display: false }, grid: { color: "rgba(27,73,34,.08)" }, ticks: { callback: function (value) { return Math.round(value / 1000000) + " Tr"; } } }
        }
      }
    });
  }

  function parseIsoDate(value) {
    var parts = String(value || "").split("-").map(Number);
    if (parts.length !== 3 || parts.some(function (item) { return !item; })) return null;
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function toInputDate(date) {
    var year = date.getFullYear();
    var month = String(date.getMonth() + 1).padStart(2, "0");
    var day = String(date.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
  }

  function initDatePresets() {
    var form = root.querySelector("[data-report-filters]");
    if (!form) return;
    var startInput = form.querySelector("[name='start_date']");
    var endInput = form.querySelector("[name='end_date']");
    root.querySelectorAll("[data-report-preset]").forEach(function (button) {
      button.addEventListener("click", function () {
        var days = Number(button.dataset.reportPreset || 30);
        var end = parseIsoDate(endInput.value) || new Date();
        var start = new Date(end.getFullYear(), end.getMonth(), end.getDate());
        start.setDate(start.getDate() - days + 1);
        startInput.value = toInputDate(start);
      });
    });
  }

  function initProductFilters() {
    var rows = Array.from(root.querySelectorAll("[data-product-row]"));
    var search = root.querySelector("[data-product-search]");
    var buttons = Array.from(root.querySelectorAll("[data-segment-filter]"));
    var empty = root.querySelector("[data-product-empty]");
    var active = "all";

    function apply() {
      var query = String(search ? search.value : "").trim().toLocaleLowerCase("vi-VN");
      var visible = 0;
      rows.forEach(function (row) {
        var segmentOk = active === "all" || row.dataset.segment === active;
        var searchOk = !query || String(row.dataset.search || "").includes(query);
        row.hidden = !(segmentOk && searchOk);
        if (!row.hidden) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        active = button.dataset.segmentFilter || "all";
        buttons.forEach(function (item) { item.classList.toggle("is-active", item === button); });
        apply();
      });
    });
    if (search) search.addEventListener("input", apply);
  }

  function csrfToken() {
    var meta = document.querySelector("meta[name='csrf-token']");
    return meta ? meta.content : "";
  }

  function currentFilters() {
    return Object.assign({}, reportData.filters || {});
  }

  function readExportConfig() {
    var config = {
      title: "GUAMAISON Analytics Intelligence",
      note: "",
      sheets: [],
      product_columns: [],
      include_charts: true
    };
    root.querySelectorAll("[data-export-sheet]:checked").forEach(function (input) { config.sheets.push(input.value); });
    root.querySelectorAll("[data-export-column]:checked").forEach(function (input) { config.product_columns.push(input.value); });
    var title = root.querySelector("[data-export-title]");
    var note = root.querySelector("[data-export-note]");
    var charts = root.querySelector("[data-export-charts]");
    config.title = title ? title.value.trim() : config.title;
    config.note = note ? note.value.trim() : "";
    config.include_charts = charts ? charts.checked : true;
    return config;
  }

  function saveExportConfig(config) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(config)); } catch (error) { /* Storage may be blocked. */ }
  }

  function restoreExportConfig() {
    var config = null;
    try { config = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); } catch (error) { config = null; }
    if (!config) return;
    var title = root.querySelector("[data-export-title]");
    var note = root.querySelector("[data-export-note]");
    var charts = root.querySelector("[data-export-charts]");
    if (title && config.title) title.value = config.title;
    if (note) note.value = config.note || "";
    if (charts) charts.checked = config.include_charts !== false;
    if (Array.isArray(config.sheets)) {
      root.querySelectorAll("[data-export-sheet]").forEach(function (input) { input.checked = config.sheets.includes(input.value); });
    }
    if (Array.isArray(config.product_columns)) {
      root.querySelectorAll("[data-export-column]").forEach(function (input) { input.checked = config.product_columns.includes(input.value); });
    }
  }

  function setLoading(button, loading, label) {
    if (!button) return;
    if (loading) {
      button.dataset.originalHtml = button.innerHTML;
      button.disabled = true;
      button.innerHTML = '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>' + label;
    } else {
      button.disabled = false;
      button.innerHTML = button.dataset.originalHtml || button.innerHTML;
    }
  }

  async function postJson(url, body) {
    var response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      var message = "Yêu cầu thất bại (" + response.status + ").";
      try { message = (await response.json()).message || message; } catch (error) { /* HTML error page. */ }
      throw new Error(message);
    }
    return response;
  }

  function renderPreview(payload) {
    var preview = root.querySelector("[data-export-preview]");
    if (!preview) return;
    var sheets = (payload && payload.sheets) || [];
    preview.innerHTML = "";
    sheets.forEach(function (sheet) {
      var row = document.createElement("div");
      var name = document.createElement("strong");
      var count = document.createElement("span");
      name.textContent = sheet.label;
      count.textContent = Number(sheet.row_count || 0).toLocaleString("vi-VN") + " dòng";
      row.append(name, count);
      preview.appendChild(row);
    });
    var columnRow = document.createElement("div");
    columnRow.innerHTML = "<strong>Cột sản phẩm</strong><span>" + ((payload.product_columns || []).length) + " cột</span>";
    preview.appendChild(columnRow);
  }

  function filenameFromResponse(response) {
    var header = response.headers.get("Content-Disposition") || "";
    var utf = header.match(/filename\*=UTF-8''([^;]+)/i);
    var plain = header.match(/filename="?([^";]+)"?/i);
    return decodeURIComponent((utf && utf[1]) || (plain && plain[1]) || "GUAMAISON_Analytics.xlsx");
  }

  function initExportModal() {
    var modal = root.querySelector("[data-export-modal]");
    if (!modal) return;
    var openButton = root.querySelector("[data-export-open]");
    var closeButtons = modal.querySelectorAll("[data-export-close]");
    var previewButton = modal.querySelector("[data-export-preview-button]");
    var downloadButton = modal.querySelector("[data-export-download]");
    var lastFocused = null;

    restoreExportConfig();

    function open() {
      lastFocused = document.activeElement;
      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("ai-modal-open");
      window.requestAnimationFrame(function () {
        var focusTarget = modal.querySelector("[data-export-title]");
        if (focusTarget) focusTarget.focus();
      });
    }

    function close() {
      modal.hidden = true;
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("ai-modal-open");
      if (lastFocused && typeof lastFocused.focus === "function") lastFocused.focus();
    }

    if (openButton) openButton.addEventListener("click", open);
    closeButtons.forEach(function (button) { button.addEventListener("click", close); });
    modal.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close();
      if (event.key !== "Tab") return;
      var focusable = Array.from(modal.querySelectorAll("button:not([disabled]), input:not([disabled]), textarea:not([disabled])"));
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });

    if (previewButton) previewButton.addEventListener("click", async function () {
      var config = readExportConfig();
      if (!config.sheets.length) return showToast("Hãy chọn ít nhất một sheet.", true);
      saveExportConfig(config);
      setLoading(previewButton, true, "Đang xem trước");
      try {
        var response = await postJson(root.dataset.previewUrl, { filters: currentFilters(), config: config });
        var payload = await response.json();
        renderPreview(payload.preview);
      } catch (error) {
        showToast(error.message, true);
      } finally {
        setLoading(previewButton, false);
      }
    });

    if (downloadButton) downloadButton.addEventListener("click", async function () {
      var config = readExportConfig();
      if (!config.sheets.length) return showToast("Hãy chọn ít nhất một sheet.", true);
      saveExportConfig(config);
      setLoading(downloadButton, true, "Đang tạo Excel");
      try {
        var response = await postJson(root.dataset.exportUrl, { filters: currentFilters(), config: config });
        var blob = await response.blob();
        var url = URL.createObjectURL(blob);
        var anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filenameFromResponse(response);
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        showToast("Đã tạo báo cáo Excel theo cấu hình của bạn.", false);
        close();
      } catch (error) {
        showToast(error.message, true);
      } finally {
        setLoading(downloadButton, false);
      }
    });
  }

  function init() {
    chartDefaults();
    initRevenueChart();
    initChannelChart();
    initForecastChart();
    initDatePresets();
    initProductFilters();
    initExportModal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

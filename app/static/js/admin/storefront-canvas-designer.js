/* app/static/js/admin/storefront-canvas-designer.js */

(function () {
"use strict";

const DEFAULT_CANVAS = {
enabled: true,
desktop: {
width: 1440,
height: 900
},
style: {
background: "#fffaf5",
radius: 28,
padding: 0,
grid_size: 20,
show_grid: true,
snap: true
},
frames: []
};

const FRAME_DEFAULTS = {
media: {
type: "media",
title: "Khung media",
x: 80,
y: 80,
w: 360,
h: 240,
radius: 20,
z: 1,
media_type: "auto",
media_url: "",
link: "",
fit: "cover",
opacity: 100,
text: "",
text_color: "#241207",
bg_color: "transparent",
font_size: 24,
align: "center",
locked: false
},
image: {
type: "image",
title: "Khung ảnh",
x: 90,
y: 90,
w: 360,
h: 240,
radius: 20,
z: 1,
media_type: "image",
media_url: "",
link: "",
fit: "cover",
opacity: 100,
text: "",
text_color: "#241207",
bg_color: "transparent",
font_size: 24,
align: "center",
locked: false
},
video: {
type: "video",
title: "Khung video",
x: 100,
y: 100,
w: 520,
h: 300,
radius: 24,
z: 1,
media_type: "video",
media_url: "",
link: "",
fit: "cover",
opacity: 100,
text: "",
text_color: "#241207",
bg_color: "transparent",
font_size: 24,
align: "center",
locked: false
},
hero: {
type: "media",
title: "Hero lớn",
x: 60,
y: 60,
w: 920,
h: 360,
radius: 28,
z: 1,
media_type: "auto",
media_url: "",
link: "/shop",
fit: "cover",
opacity: 100,
text: "",
text_color: "#241207",
bg_color: "transparent",
font_size: 24,
align: "center",
locked: false
},
banner: {
type: "media",
title: "Banner ngang",
x: 90,
y: 100,
w: 720,
h: 240,
radius: 24,
z: 1,
media_type: "auto",
media_url: "",
link: "/shop",
fit: "cover",
opacity: 100,
text: "",
text_color: "#241207",
bg_color: "transparent",
font_size: 24,
align: "center",
locked: false
},
square: {
type: "image",
title: "Ô vuông",
x: 110,
y: 110,
w: 300,
h: 300,
radius: 22,
z: 1,
media_type: "image",
media_url: "",
link: "/shop",
fit: "cover",
opacity: 100,
text: "",
text_color: "#241207",
bg_color: "transparent",
font_size: 24,
align: "center",
locked: false
},
portrait: {
type: "image",
title: "Ô dọc 4:5",
x: 120,
y: 120,
w: 300,
h: 375,
radius: 22,
z: 1,
media_type: "image",
media_url: "",
link: "/shop",
fit: "cover",
opacity: 100,
text: "",
text_color: "#241207",
bg_color: "transparent",
font_size: 24,
align: "center",
locked: false
},
text: {
type: "text",
title: "Khung chữ",
x: 140,
y: 140,
w: 420,
h: 150,
radius: 18,
z: 1,
media_type: "none",
media_url: "",
link: "",
fit: "cover",
opacity: 100,
text: "New Collection",
text_color: "#241207",
bg_color: "rgba(255, 253, 249, 0.72)",
font_size: 42,
align: "center",
locked: false
},
button: {
type: "button",
title: "Nút CTA",
x: 160,
y: 160,
w: 240,
h: 70,
radius: 999,
z: 1,
media_type: "none",
media_url: "",
link: "/shop",
fit: "cover",
opacity: 100,
text: "Mua ngay",
text_color: "#ffffff",
bg_color: "#3b2414",
font_size: 16,
align: "center",
locked: false
}
};

let root = null;
let hiddenInput = null;
let canvasEl = null;
let layerEl = null;
let viewportEl = null;

let state = clone(DEFAULT_CANVAS);
let selectedId = null;
let zoom = 1;
let dirty = false;

let history = [];
let historyIndex = -1;
let isRestoringHistory = false;

let dragSession = null;
let resizeSession = null;
let uploadTargetFrameId = null;

const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => Array.from(parent.querySelectorAll(selector));

function clone(value) {
return JSON.parse(JSON.stringify(value));
}

function uid(prefix) {
return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

function toNumber(value, fallback = 0) {
const number = Number(value);
return Number.isFinite(number) ? number : fallback;
}

function clamp(value, min, max) {
return Math.max(min, Math.min(max, value));
}

function escapeHtml(value) {
return String(value == null ? "" : value)
.replace(/&/g, "&amp;")
.replace(/</g, "&lt;")
.replace(/>/g, "&gt;")
.replace(/"/g, "&quot;")
.replace(/'/g, "&#39;");
}

function escapeAttr(value) {
return escapeHtml(value).replace(/`/g, "`");
}

function getCsrfToken() {
const meta = document.querySelector('meta[name="csrf-token"]');
const input = document.querySelector('input[name="csrf_token"]');

  
return (meta && meta.content) || (input && input.value) || "";
  

}

function notify(message, isError = false) {
const toast = $("#sfbToast");
const text = $("#sfbToastText");
const icon = $("#sfbToastIcon");

  
if (!toast || !text || !icon) {
  if (isError) {
    console.error(message);
  } else {
    console.log(message);
  }
  return;
}

text.textContent = message || "";
toast.classList.toggle("is-error", Boolean(isError));
icon.className = isError
  ? "fa-solid fa-triangle-exclamation"
  : "fa-solid fa-circle-check";

toast.classList.add("is-show");

window.clearTimeout(notify._timer);
notify._timer = window.setTimeout(() => {
  toast.classList.remove("is-show");
}, 3200);
  

}

function setDirty(value = true) {
dirty = Boolean(value);

  
if (root) {
  root.classList.toggle("is-dirty", dirty);
  root.classList.toggle("is-saved", !dirty);
}

const localStatus = $("#sfcSaveStateText");
if (localStatus) {
  localStatus.textContent = dirty ? "Chưa lưu" : "Đã lưu";
}

const globalStatus = $("#sfbDirtyStatus");
if (globalStatus) {
  globalStatus.textContent = dirty ? "Chưa lưu" : "Sẵn sàng";
  globalStatus.classList.toggle("is-dirty", dirty);
}
  

}

function isVideoUrl(url) {
const clean = String(url || "").split("?")[0].toLowerCase();
return clean.endsWith(".mp4") || clean.endsWith(".webm") || clean.endsWith(".mov") || clean.endsWith(".avi");
}

function guessMediaTypeFromUrl(url) {
const value = String(url || "").trim();
if (!value) return "auto";
return isVideoUrl(value) ? "video" : "image";
}

function normalizeDroppedUrl(value) {
return String(value || "")
  .split("\n")
  .map((line) => line.trim())
  .find(Boolean) || "";
}

function isFrameEditorTarget(target) {
return Boolean(target && target.closest("input, textarea, select, button, [contenteditable='true']"));
}

function getFrame(id) {
return state.frames.find((frame) => frame.id === id) || null;
}

function getSelectedFrame() {
return selectedId ? getFrame(selectedId) : null;
}

function getMaxZ() {
return state.frames.reduce((max, frame) => Math.max(max, toNumber(frame.z, 1)), 0);
}

function snapValue(value) {
if (!state.style.snap) {
return Math.round(value);
}

  
const size = Math.max(1, toNumber(state.style.grid_size, 20));
return Math.round(value / size) * size;
  

}

function normalizeFrame(raw, index = 0) {
const base = clone(FRAME_DEFAULTS[raw && raw.type ? raw.type : "media"] || FRAME_DEFAULTS.media);
const frame = {
...base,
...(raw || {})
};

  
frame.id = frame.id || uid("frame");
frame.type = frame.type || "media";
frame.title = frame.title || base.title || "Frame";
frame.x = toNumber(frame.x, 80 + index * 24);
frame.y = toNumber(frame.y, 80 + index * 24);
frame.w = Math.max(40, toNumber(frame.w, base.w || 240));
frame.h = Math.max(40, toNumber(frame.h, base.h || 160));
frame.radius = clamp(toNumber(frame.radius, base.radius || 20), 0, 200);
frame.z = toNumber(frame.z, index + 1);
frame.media_type = frame.media_type || "auto";
frame.media_url = frame.media_url || "";
frame.link = frame.link || "";
frame.fit = frame.fit || "cover";
frame.opacity = clamp(toNumber(frame.opacity, 100), 0, 100);
frame.text = frame.text || "";
frame.text_color = frame.text_color || "#241207";
frame.bg_color = frame.bg_color || "transparent";
frame.font_size = clamp(toNumber(frame.font_size, 24), 8, 160);
frame.align = frame.align || "center";
frame.locked = Boolean(frame.locked);

return frame;
  

}

function normalizeCanvas(raw) {
let parsed = raw;

  
if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
  parsed = {};
}

const desktop = parsed.desktop && typeof parsed.desktop === "object"
  ? parsed.desktop
  : {};

const style = parsed.style && typeof parsed.style === "object"
  ? parsed.style
  : {};

return {
  enabled: parsed.enabled !== false,
  desktop: {
    width: clamp(toNumber(desktop.width || parsed.width, DEFAULT_CANVAS.desktop.width), 320, 2560),
    height: clamp(toNumber(desktop.height || parsed.height, DEFAULT_CANVAS.desktop.height), 320, 4000)
  },
  style: {
    background: style.background || parsed.background || DEFAULT_CANVAS.style.background,
    radius: clamp(toNumber(style.radius || parsed.radius, DEFAULT_CANVAS.style.radius), 0, 120),
    padding: clamp(toNumber(style.padding || parsed.padding, DEFAULT_CANVAS.style.padding), 0, 160),
    grid_size: clamp(toNumber(style.grid_size || parsed.grid_size, DEFAULT_CANVAS.style.grid_size), 4, 80),
    show_grid: style.show_grid !== false && parsed.show_grid !== false,
    snap: style.snap !== false && parsed.snap !== false
  },
  frames: Array.isArray(parsed.frames)
    ? parsed.frames.map(normalizeFrame)
    : []
};
  

}

function parseStoredCanvas() {
if (!root) {
return clone(DEFAULT_CANVAS);
}

  
const raw = root.dataset.storedCanvas || "";

if (!raw) {
  return clone(DEFAULT_CANVAS);
}

try {
  const parsed = JSON.parse(raw);

  if (typeof parsed === "string" && parsed.trim()) {
    return normalizeCanvas(JSON.parse(parsed));
  }

  return normalizeCanvas(parsed);
} catch (error) {
  console.warn("[StorefrontCanvasDesigner] Cannot parse homepage_canvas:", error);
  return clone(DEFAULT_CANVAS);
}
  

}

function canvasOutput() {
return {
enabled: Boolean(state.enabled),
desktop: {
width: toNumber(state.desktop.width, 1440),
height: toNumber(state.desktop.height, 900)
},
style: {
background: state.style.background || "#fffaf5",
radius: toNumber(state.style.radius, 28),
padding: toNumber(state.style.padding, 0),
grid_size: toNumber(state.style.grid_size, 20),
show_grid: Boolean(state.style.show_grid),
snap: Boolean(state.style.snap)
},
frames: state.frames
.slice()
.sort((a, b) => toNumber(a.z, 0) - toNumber(b.z, 0))
.map((frame) => ({
id: frame.id,
type: frame.type,
title: frame.title || "",
x: toNumber(frame.x, 0),
y: toNumber(frame.y, 0),
w: toNumber(frame.w, 240),
h: toNumber(frame.h, 160),
radius: toNumber(frame.radius, 20),
z: toNumber(frame.z, 1),
media_type: frame.media_type || "auto",
media_url: frame.media_url || "",
link: frame.link || "",
fit: frame.fit || "cover",
opacity: toNumber(frame.opacity, 100),
text: frame.text || "",
text_color: frame.text_color || "#241207",
bg_color: frame.bg_color || "transparent",
font_size: toNumber(frame.font_size, 24),
align: frame.align || "center",
locked: Boolean(frame.locked)
}))
};
}

function syncHiddenInput() {
if (hiddenInput) {
hiddenInput.value = JSON.stringify(canvasOutput());
}

  
renderOutputStats();
  

}

function pushHistory() {
if (isRestoringHistory) {
return;
}

  
const snapshot = JSON.stringify(canvasOutput());

if (history[historyIndex] === snapshot) {
  return;
}

history = history.slice(0, historyIndex + 1);
history.push(snapshot);

if (history.length > 60) {
  history.shift();
}

historyIndex = history.length - 1;
  

}

function restoreHistory(index) {
if (index < 0 || index >= history.length) {
return;
}

  
try {
  isRestoringHistory = true;
  const snapshot = JSON.parse(history[index]);
  state = normalizeCanvas(snapshot);
  historyIndex = index;
  selectedId = state.frames[0] ? state.frames[0].id : null;
  renderAll();
  setDirty(true);
} catch (error) {
  notify("Không thể khôi phục lịch sử canvas.", true);
} finally {
  isRestoringHistory = false;
}
  

}

function undo() {
if (historyIndex <= 0) {
notify("Không còn thao tác để hoàn tác.");
return;
}

  
restoreHistory(historyIndex - 1);
  

}

function redo() {
if (historyIndex >= history.length - 1) {
notify("Không còn thao tác để làm lại.");
return;
}

  
restoreHistory(historyIndex + 1);
  

}

function applyCanvasSettingsToInputs() {
const preset = $("#sfcPreset");
const widthInput = $("#sfcCanvasWidth");
const heightInput = $("#sfcCanvasHeight");
const bgInput = $("#sfcCanvasBg");
const radiusInput = $("#sfcCanvasRadius");
const gridSizeInput = $("#sfcGridSize");
const paddingInput = $("#sfcCanvasPadding");
const enabledInput = $("#sfcCanvasEnabled");
const gridInput = $("#sfcGridEnabled");
const snapInput = $("#sfcSnapEnabled");

  
if (widthInput) widthInput.value = state.desktop.width;
if (heightInput) heightInput.value = state.desktop.height;
if (bgInput) bgInput.value = state.style.background || "#fffaf5";
if (radiusInput) radiusInput.value = state.style.radius;
if (gridSizeInput) gridSizeInput.value = state.style.grid_size;
if (paddingInput) paddingInput.value = state.style.padding;
if (enabledInput) enabledInput.checked = Boolean(state.enabled);
if (gridInput) gridInput.checked = Boolean(state.style.show_grid);
if (snapInput) snapInput.checked = Boolean(state.style.snap);

if (preset) {
  const value = `${state.desktop.width}x${state.desktop.height}`;
  const hasPreset = Array.from(preset.options).some((option) => option.value === value);
  preset.value = hasPreset ? value : "custom";
}
  

}

function applyCanvasStyles() {
if (!canvasEl) {
return;
}

  
const width = toNumber(state.desktop.width, 1440);
const height = toNumber(state.desktop.height, 900);
const radius = toNumber(state.style.radius, 28);
const background = state.style.background || "#fffaf5";
const gridSize = toNumber(state.style.grid_size, 20);

canvasEl.style.width = `${width}px`;
canvasEl.style.height = `${height}px`;
canvasEl.style.borderRadius = `${radius}px`;
canvasEl.style.backgroundColor = background;
canvasEl.style.setProperty("--sfc-grid-size", `${gridSize}px`);
canvasEl.style.transform = `scale(${zoom})`;

canvasEl.classList.toggle("is-grid", Boolean(state.style.show_grid));
canvasEl.classList.toggle("is-no-grid", !state.style.show_grid);

const meta = $("#sfcCanvasMeta");
const sizeText = $("#sfcCanvasSizeText");

if (meta) meta.textContent = `${width} × ${height}`;
if (sizeText) sizeText.textContent = `${width}×${height}`;

const zoomLabel = $("#sfcZoomLabel");
const zoomText = $("#sfcZoomText");

if (zoomLabel) zoomLabel.textContent = `${Math.round(zoom * 100)}%`;
if (zoomText) zoomText.textContent = `${Math.round(zoom * 100)}%`;
  

}

function createFrame(kind) {
const base = clone(FRAME_DEFAULTS[kind] || FRAME_DEFAULTS.media);
const index = state.frames.length;
const offset = index * 22;

  
base.id = uid("frame");
base.x = clamp(toNumber(base.x, 80) + offset, 0, Math.max(0, state.desktop.width - base.w));
base.y = clamp(toNumber(base.y, 80) + offset, 0, Math.max(0, state.desktop.height - base.h));
base.z = getMaxZ() + 1;

return normalizeFrame(base, index);
  

}

function addFrame(kind) {
const frame = createFrame(kind);
state.frames.push(frame);
selectedId = frame.id;

  
renderAll();
pushHistory();
setDirty(true);
  

}

function addTemplate(name) {
const ok = state.frames.length
? confirm("Thêm mẫu bố cục vào canvas hiện tại?")
: true;

  
if (!ok) {
  return;
}

const width = state.desktop.width;
const padding = Math.max(40, Math.round(width * 0.04));
const gap = 24;

let frames = [];

if (name === "hero-three") {
  frames = [
    { kind: "hero", x: padding, y: 60, w: Math.round(width * 0.58), h: 420, title: "Hero chính" },
    { kind: "square", x: padding + Math.round(width * 0.58) + gap, y: 60, w: 280, h: 198, title: "Ảnh phụ 1" },
    { kind: "square", x: padding + Math.round(width * 0.58) + gap, y: 282, w: 280, h: 198, title: "Ảnh phụ 2" }
  ];
} else if (name === "shopee-grid") {
  frames = [
    { kind: "hero", x: padding, y: 60, w: 520, h: 520, title: "Campaign lớn" },
    { kind: "banner", x: padding + 544, y: 60, w: 360, h: 248, title: "Banner 1" },
    { kind: "banner", x: padding + 928, y: 60, w: 360, h: 248, title: "Banner 2" },
    { kind: "banner", x: padding + 544, y: 332, w: 360, h: 248, title: "Banner 3" },
    { kind: "banner", x: padding + 928, y: 332, w: 360, h: 248, title: "Banner 4" }
  ];
} else if (name === "lookbook") {
  frames = [
    { kind: "portrait", x: padding, y: 70, w: 340, h: 520, title: "Lookbook 1" },
    { kind: "portrait", x: padding + 370, y: 120, w: 340, h: 520, title: "Lookbook 2" },
    { kind: "portrait", x: padding + 740, y: 70, w: 340, h: 520, title: "Lookbook 3" }
  ];
} else if (name === "video-banner") {
  frames = [
    { kind: "video", x: padding, y: 70, w: 760, h: 440, title: "Video thương hiệu" },
    { kind: "banner", x: padding + 790, y: 70, w: 400, h: 440, title: "Banner CTA" }
  ];
}

frames.forEach((item) => {
  const frame = createFrame(item.kind);
  Object.assign(frame, {
    x: item.x,
    y: item.y,
    w: item.w,
    h: item.h,
    title: item.title,
    z: getMaxZ() + 1
  });
  state.frames.push(normalizeFrame(frame));
});

selectedId = state.frames.length ? state.frames[state.frames.length - 1].id : null;
renderAll();
pushHistory();
setDirty(true);
  

}

function frameAlignToJustify(align) {
if (align === "left") return "flex-start";
if (align === "right") return "flex-end";
return "center";
}

function updateFrameMediaUrl(frameId, url, shouldPushHistory = true) {
const frame = getFrame(frameId);

if (!frame) {
  return;
}

const cleanUrl = String(url || "").trim();
frame.media_url = cleanUrl;

if (cleanUrl && (!frame.media_type || frame.media_type === "auto" || frame.media_type === "none")) {
  frame.media_type = guessMediaTypeFromUrl(cleanUrl);
}

renderAll();
setDirty(true);

if (shouldPushHistory) {
  pushHistory();
}
}

function renderFrameContent(frame) {
if (frame.type === "text") {
return `         <div
          class="sfc-frame-text"
          style="             --sfc-text-color: ${escapeAttr(frame.text_color || "#241207")};             --sfc-text-bg: ${escapeAttr(frame.bg_color || "transparent")};             --sfc-font-size: ${toNumber(frame.font_size, 24)}px;             --sfc-text-align: ${escapeAttr(frame.align || "center")};             --sfc-text-justify: ${frameAlignToJustify(frame.align)};
          "         >
          ${escapeHtml(frame.text || "Text")}         </div>
      `;
}

  
if (frame.type === "button") {
  return `
    <div
      class="sfc-frame-button"
      style="
        --sfc-text-color: ${escapeAttr(frame.text_color || "#ffffff")};
        --sfc-text-bg: ${escapeAttr(frame.bg_color || "#3b2414")};
        --sfc-font-size: ${toNumber(frame.font_size, 16)}px;
      "
    >
      ${escapeHtml(frame.text || "Button")}
    </div>
  `;
}

const url = String(frame.media_url || "").trim();

if (url) {
  const shouldUseVideo = frame.media_type === "video" || (frame.media_type === "auto" && isVideoUrl(url));

  return `
    <div class="sfc-frame-media">
      ${
        shouldUseVideo
          ? `<video src="${escapeAttr(url)}" muted loop playsinline preload="metadata"></video>`
          : `<img src="${escapeAttr(url)}" alt="${escapeAttr(frame.title || "")}" loading="lazy">`
      }
    </div>
  `;
}

return `
  <div class="sfc-frame-placeholder">
    <i class="fa-solid fa-plus"></i>
    <strong>Thêm media</strong>
    <span>Dán URL ảnh/video ở Properties hoặc bấm dấu cộng.</span>
  </div>
`;
  

}

function renderFrames() {
if (!layerEl) {
return;
}

  
const hint = $("#sfcEmptyCanvasHint");
if (hint) {
  hint.hidden = state.frames.length > 0;
}

$$(".sfc-frame", layerEl).forEach((node) => node.remove());

const frames = state.frames.slice().sort((a, b) => toNumber(a.z, 0) - toNumber(b.z, 0));

frames.forEach((frame) => {
  const node = document.createElement("article");
  node.className = [
    "sfc-frame",
    frame.id === selectedId ? "is-selected" : "",
    frame.media_url ? "has-media" : "",
    frame.locked ? "is-locked" : ""
  ].filter(Boolean).join(" ");

  node.dataset.frameId = frame.id;
  applyFrameStyle(node, frame);

  node.innerHTML = `
    <div class="sfc-frame-inner">
      ${renderFrameContent(frame)}

      <button type="button" class="sfc-frame-plus" data-sfc-frame-plus title="Thêm media">
        <i class="fa-solid fa-plus"></i>
      </button>

      <div class="sfc-frame-url-panel" data-sfc-url-panel>
        <input
          type="url"
          class="sfc-frame-url-input"
          value="${escapeAttr(frame.media_url || "")}"
          placeholder="Dán URL ảnh/video..."
          aria-label="URL ảnh hoặc video"
          data-sfc-frame-url-input
        >
        <button type="button" class="sfc-frame-url-apply" data-sfc-frame-url-apply>
          OK
        </button>
      </div>

      <div class="sfc-frame-label">
        ${escapeHtml(frame.title || frame.type)}
      </div>

      <div class="sfc-frame-lock">
        <i class="fa-solid fa-lock"></i>
      </div>

      <button type="button" class="sfc-frame-resize" data-sfc-resize title="Kéo để resize"></button>
    </div>
  `;

  node.addEventListener("pointerdown", (event) => {
    if (event.target.closest("[data-sfc-resize]")) {
      return;
    }

    if (event.target.closest("[data-sfc-frame-plus]") || event.target.closest("[data-sfc-url-panel]")) {
      return;
    }

    if (isFrameEditorTarget(event.target)) {
      return;
    }

    selectFrame(frame.id);

    if (!frame.locked) {
      startDrag(event, frame.id);
    }
  });

  node.querySelector("[data-sfc-resize]").addEventListener("pointerdown", (event) => {
    event.stopPropagation();
    selectFrame(frame.id);

    if (!frame.locked) {
      startResize(event, frame.id);
    }
  });

  node.querySelector("[data-sfc-frame-plus]").addEventListener("click", (event) => {
    event.stopPropagation();
    selectFrame(frame.id);
    uploadTargetFrameId = frame.id;

    const input = $("#sfcMediaUploadInput");
    if (input) {
      input.click();
    }
  });

  const urlInput = node.querySelector("[data-sfc-frame-url-input]");
  const urlApply = node.querySelector("[data-sfc-frame-url-apply]");

  if (urlInput) {
    ["pointerdown", "click", "dblclick"].forEach((eventName) => {
      urlInput.addEventListener(eventName, (event) => {
        event.stopPropagation();
      });
    });

    urlInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        event.stopPropagation();
        selectFrame(frame.id);
        updateFrameMediaUrl(frame.id, urlInput.value, true);
      }
    });

    urlInput.addEventListener("change", () => {
      selectFrame(frame.id);
      updateFrameMediaUrl(frame.id, urlInput.value, true);
    });

    urlInput.addEventListener("paste", () => {
      window.setTimeout(() => {
        selectFrame(frame.id);
        updateFrameMediaUrl(frame.id, urlInput.value, true);
      }, 0);
    });
  }

  if (urlApply) {
    urlApply.addEventListener("pointerdown", (event) => event.stopPropagation());
    urlApply.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      selectFrame(frame.id);
      updateFrameMediaUrl(frame.id, urlInput ? urlInput.value : "", true);
    });
  }

  node.addEventListener("dragover", (event) => {
    if (frame.locked) return;
    event.preventDefault();
    node.classList.add("is-drag-over");
  });

  node.addEventListener("dragleave", () => {
    node.classList.remove("is-drag-over");
  });

  node.addEventListener("drop", (event) => {
    if (frame.locked) return;

    event.preventDefault();
    event.stopPropagation();
    node.classList.remove("is-drag-over");
    selectFrame(frame.id);

    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];

    if (file) {
      uploadTargetFrameId = frame.id;
      uploadMediaFile(file);
      return;
    }

    const droppedUrl = normalizeDroppedUrl(
      event.dataTransfer.getData("text/uri-list") || event.dataTransfer.getData("text/plain")
    );

    if (droppedUrl) {
      updateFrameMediaUrl(frame.id, droppedUrl, true);
    }
  });

  layerEl.appendChild(node);
});
  

}

function applyFrameStyle(node, frame) {
node.style.setProperty("--sfc-x", `${toNumber(frame.x, 0)}px`);
node.style.setProperty("--sfc-y", `${toNumber(frame.y, 0)}px`);
node.style.setProperty("--sfc-w", `${toNumber(frame.w, 240)}px`);
node.style.setProperty("--sfc-h", `${toNumber(frame.h, 160)}px`);
node.style.setProperty("--sfc-radius", `${toNumber(frame.radius, 20)}px`);
node.style.setProperty("--sfc-z", `${toNumber(frame.z, 1)}`);
node.style.setProperty("--sfc-fit", frame.fit || "cover");
node.style.opacity = String(clamp(toNumber(frame.opacity, 100), 0, 100) / 100);
}

function updateFrameNode(frame) {
const node = layerEl ? layerEl.querySelector(`[data-frame-id="${CSS.escape(frame.id)}"]`) : null;
if (!node) {
return;
}

  
applyFrameStyle(node, frame);
  

}

function renderLayerList() {
const list = $("#sfcLayerList");

  
if (!list) {
  return;
}

if (!state.frames.length) {
  list.innerHTML = `
    <div class="sfc-empty-state">
      <i class="fa-solid fa-layer-group"></i>
      <p>Chưa có khung nào</p>
      <small>Bấm thêm khung để bắt đầu thiết kế.</small>
    </div>
  `;
  return;
}

const frames = state.frames.slice().sort((a, b) => toNumber(b.z, 0) - toNumber(a.z, 0));

list.innerHTML = frames.map((frame) => `
  <button
    type="button"
    class="sfc-layer-item ${frame.id === selectedId ? "is-selected" : ""}"
    data-sfc-layer="${escapeAttr(frame.id)}"
  >
    <span class="sfc-layer-icon">
      <i class="fa-solid ${getFrameIcon(frame)}"></i>
    </span>

    <span class="sfc-layer-info">
      <strong>${escapeHtml(frame.title || frame.type)}</strong>
      <span>${escapeHtml(frame.type)} · ${Math.round(frame.w)}×${Math.round(frame.h)} · z${frame.z}</span>
    </span>

    <span class="sfc-layer-actions">
      ${frame.locked ? '<i class="fa-solid fa-lock"></i>' : '<i class="fa-solid fa-chevron-right"></i>'}
    </span>
  </button>
`).join("");

$$("[data-sfc-layer]", list).forEach((button) => {
  button.addEventListener("click", () => {
    selectFrame(button.dataset.sfcLayer);
  });
});
  

}

function getFrameIcon(frame) {
if (frame.type === "text") return "fa-font";
if (frame.type === "button") return "fa-hand-pointer";
if (frame.media_type === "video" || frame.type === "video") return "fa-circle-play";
return "fa-image";
}

function selectFrame(id) {
selectedId = id;
renderFrames();
renderLayerList();
renderProperties();
}

function clearSelection() {
selectedId = null;
renderFrames();
renderLayerList();
renderProperties();
}

function renderProperties() {
const empty = $("#sfcPropertiesEmpty");
const form = $("#sfcPropertiesForm");
const frame = getSelectedFrame();

  
if (!empty || !form) {
  return;
}

if (!frame) {
  empty.classList.remove("sfb-hidden");
  form.classList.add("sfb-hidden");
  return;
}

empty.classList.add("sfb-hidden");
form.classList.remove("sfb-hidden");

const title = $("#sfcSelectedTitle");
const id = $("#sfcSelectedId");

if (title) title.textContent = frame.title || frame.type;
if (id) id.textContent = frame.id;

$$("[data-sfc-prop]", form).forEach((input) => {
  const key = input.dataset.sfcProp;
  const value = frame[key];

  if (input.type === "checkbox") {
    input.checked = Boolean(value);
  } else {
    input.value = value == null ? "" : value;
  }
});
  

}

function updateSelectedFrameFromInput(input, shouldPushHistory = false) {
const frame = getSelectedFrame();

  
if (!frame) {
  return;
}

const key = input.dataset.sfcProp;
if (!key) {
  return;
}

let value = input.value;

if (["x", "y", "w", "h", "radius", "z", "opacity", "font_size"].includes(key)) {
  value = toNumber(value, frame[key] || 0);
}

if (key === "w" || key === "h") {
  value = Math.max(40, value);
}

if (key === "opacity") {
  value = clamp(value, 0, 100);
}

if (key === "radius") {
  value = clamp(value, 0, 200);
}

frame[key] = value;

if (key === "type") {
  if (value === "text" && !frame.text) {
    frame.text = "New Text";
  }

  if (value === "button" && !frame.text) {
    frame.text = "Mua ngay";
  }
}

renderFrames();
renderLayerList();
renderOutputStats();
syncHiddenInput();
setDirty(true);

if (shouldPushHistory) {
  pushHistory();
}
  

}

function renderOutputStats() {
const total = $("#sfcTotalFrames");
const sizeText = $("#sfcCanvasSizeText");
const zoomText = $("#sfcZoomText");

  
if (total) total.textContent = String(state.frames.length);
if (sizeText) sizeText.textContent = `${state.desktop.width}×${state.desktop.height}`;
if (zoomText) zoomText.textContent = `${Math.round(zoom * 100)}%`;
  

}

function renderAll() {
applyCanvasSettingsToInputs();
applyCanvasStyles();
renderFrames();
renderLayerList();
renderProperties();
syncHiddenInput();
}

function startDrag(event, frameId) {
const frame = getFrame(frameId);

  
if (!frame || frame.locked) {
  return;
}

event.preventDefault();

dragSession = {
  frameId,
  startX: event.clientX,
  startY: event.clientY,
  originalX: frame.x,
  originalY: frame.y
};

document.body.classList.add("sfc-no-select");

const node = layerEl.querySelector(`[data-frame-id="${CSS.escape(frameId)}"]`);
if (node) {
  node.classList.add("is-dragging");
  node.setPointerCapture && node.setPointerCapture(event.pointerId);
}

document.addEventListener("pointermove", onDragMove);
document.addEventListener("pointerup", stopDrag, { once: true });
  

}

function onDragMove(event) {
if (!dragSession) {
return;
}

  
const frame = getFrame(dragSession.frameId);

if (!frame) {
  return;
}

const dx = (event.clientX - dragSession.startX) / zoom;
const dy = (event.clientY - dragSession.startY) / zoom;

const maxX = Math.max(0, state.desktop.width - frame.w);
const maxY = Math.max(0, state.desktop.height - frame.h);

frame.x = clamp(snapValue(dragSession.originalX + dx), 0, maxX);
frame.y = clamp(snapValue(dragSession.originalY + dy), 0, maxY);

updateFrameNode(frame);
renderProperties();
syncHiddenInput();
setDirty(true);
  

}

function stopDrag() {
if (dragSession) {
const node = layerEl.querySelector(`[data-frame-id="${CSS.escape(dragSession.frameId)}"]`);
if (node) {
node.classList.remove("is-dragging");
}
}

  
dragSession = null;
document.body.classList.remove("sfc-no-select");
document.removeEventListener("pointermove", onDragMove);
pushHistory();
  

}

function startResize(event, frameId) {
const frame = getFrame(frameId);

  
if (!frame || frame.locked) {
  return;
}

event.preventDefault();

resizeSession = {
  frameId,
  startX: event.clientX,
  startY: event.clientY,
  originalW: frame.w,
  originalH: frame.h
};

document.body.classList.add("sfc-no-select");

const node = layerEl.querySelector(`[data-frame-id="${CSS.escape(frameId)}"]`);
if (node) {
  node.classList.add("is-resizing");
  node.setPointerCapture && node.setPointerCapture(event.pointerId);
}

document.addEventListener("pointermove", onResizeMove);
document.addEventListener("pointerup", stopResize, { once: true });
  

}

function onResizeMove(event) {
if (!resizeSession) {
return;
}

  
const frame = getFrame(resizeSession.frameId);

if (!frame) {
  return;
}

const dx = (event.clientX - resizeSession.startX) / zoom;
const dy = (event.clientY - resizeSession.startY) / zoom;

const maxW = Math.max(40, state.desktop.width - frame.x);
const maxH = Math.max(40, state.desktop.height - frame.y);

frame.w = clamp(snapValue(resizeSession.originalW + dx), 40, maxW);
frame.h = clamp(snapValue(resizeSession.originalH + dy), 40, maxH);

updateFrameNode(frame);
renderProperties();
syncHiddenInput();
setDirty(true);
  

}

function stopResize() {
if (resizeSession) {
const node = layerEl.querySelector(`[data-frame-id="${CSS.escape(resizeSession.frameId)}"]`);
if (node) {
node.classList.remove("is-resizing");
}
}

  
resizeSession = null;
document.body.classList.remove("sfc-no-select");
document.removeEventListener("pointermove", onResizeMove);
pushHistory();
  

}

function updateCanvasSettingFromInput(input, shouldPushHistory = false) {
if (input.matches("[data-sfc-canvas-width]")) {
state.desktop.width = clamp(toNumber(input.value, state.desktop.width), 320, 2560);
}

  
if (input.matches("[data-sfc-canvas-height]")) {
  state.desktop.height = clamp(toNumber(input.value, state.desktop.height), 320, 4000);
}

if (input.matches("[data-sfc-canvas-bg]")) {
  state.style.background = input.value || "#fffaf5";
}

if (input.matches("[data-sfc-canvas-radius]")) {
  state.style.radius = clamp(toNumber(input.value, state.style.radius), 0, 120);
}

if (input.matches("[data-sfc-grid-size]")) {
  state.style.grid_size = clamp(toNumber(input.value, state.style.grid_size), 4, 80);
}

if (input.matches("[data-sfc-canvas-padding]")) {
  state.style.padding = clamp(toNumber(input.value, state.style.padding), 0, 160);
}

if (input.matches("[data-sfc-canvas-enabled]")) {
  state.enabled = input.checked;
}

if (input.matches("[data-sfc-grid-enabled]")) {
  state.style.show_grid = input.checked;
}

if (input.matches("[data-sfc-snap-enabled]")) {
  state.style.snap = input.checked;
}

applyCanvasStyles();
syncHiddenInput();
setDirty(true);

if (shouldPushHistory) {
  pushHistory();
}
  

}

function applyPreset(value) {
if (!value || value === "custom") {
return;
}

  
const parts = value.split("x");

if (parts.length !== 2) {
  return;
}

state.desktop.width = clamp(toNumber(parts[0], state.desktop.width), 320, 2560);
state.desktop.height = clamp(toNumber(parts[1], state.desktop.height), 320, 4000);

renderAll();
pushHistory();
setDirty(true);
  

}

function setZoom(value) {
zoom = clamp(value, 0.2, 1.4);
applyCanvasStyles();
renderOutputStats();
}

function fitScreen() {
if (!viewportEl || !canvasEl) {
return;
}

  
const availableWidth = viewportEl.clientWidth - 72;
const availableHeight = viewportEl.clientHeight - 72;

const scaleX = availableWidth / state.desktop.width;
const scaleY = availableHeight / state.desktop.height;

setZoom(Math.min(1, scaleX, scaleY));
  

}

function deleteSelected() {
const frame = getSelectedFrame();

  
if (!frame) {
  return;
}

const ok = confirm(`Xóa khung "${frame.title || frame.type}"?`);

if (!ok) {
  return;
}

state.frames = state.frames.filter((item) => item.id !== frame.id);
selectedId = state.frames[0] ? state.frames[0].id : null;

renderAll();
pushHistory();
setDirty(true);
  

}

function duplicateSelected() {
const frame = getSelectedFrame();

  
if (!frame) {
  return;
}

const copy = clone(frame);
copy.id = uid("frame");
copy.title = `${copy.title || "Frame"} - Copy`;
copy.x = clamp(copy.x + 30, 0, Math.max(0, state.desktop.width - copy.w));
copy.y = clamp(copy.y + 30, 0, Math.max(0, state.desktop.height - copy.h));
copy.z = getMaxZ() + 1;
copy.locked = false;

state.frames.push(copy);
selectedId = copy.id;

renderAll();
pushHistory();
setDirty(true);
  

}

function bringForward() {
const frame = getSelectedFrame();

  
if (!frame) {
  return;
}

frame.z = getMaxZ() + 1;

renderAll();
pushHistory();
setDirty(true);
  

}

function sendBackward() {
const frame = getSelectedFrame();

  
if (!frame) {
  return;
}

frame.z = Math.max(0, Math.min(...state.frames.map((item) => toNumber(item.z, 0))) - 1);

renderAll();
pushHistory();
setDirty(true);
  

}

function toggleLockSelected() {
const frame = getSelectedFrame();

  
if (!frame) {
  return;
}

frame.locked = !frame.locked;

renderAll();
pushHistory();
setDirty(true);
  

}

function unlockAll() {
state.frames.forEach((frame) => {
frame.locked = false;
});

  
renderAll();
pushHistory();
setDirty(true);
notify("Đã mở khóa tất cả khung.");
  

}

function selectAll() {
if (!state.frames.length) {
notify("Canvas chưa có khung nào.");
return;
}

  
selectedId = state.frames[0].id;
renderAll();
notify("Hiện tại chỉ hỗ trợ chỉnh từng khung. Đã chọn khung đầu tiên.");
  

}

function alignSelected(direction) {
const frame = getSelectedFrame();

  
if (!frame) {
  return;
}

if (direction === "left") {
  frame.x = 0;
}

if (direction === "center") {
  frame.x = Math.round((state.desktop.width - frame.w) / 2);
}

if (direction === "right") {
  frame.x = Math.max(0, state.desktop.width - frame.w);
}

renderAll();
pushHistory();
setDirty(true);
  

}

function clearCanvas() {
const ok = confirm("Xóa toàn bộ khung trong Canvas Designer?");

  
if (!ok) {
  return;
}

state.frames = [];
selectedId = null;

renderAll();
pushHistory();
setDirty(true);
  

}

async function uploadMediaFile(file) {
const frame = uploadTargetFrameId ? getFrame(uploadTargetFrameId) : getSelectedFrame();

  
if (!frame || !file) {
  return;
}

const previousUrl = frame.media_url || "";
const tempUrl = URL.createObjectURL(file);

frame.media_url = tempUrl;
frame.media_type = file.type.startsWith("video/") ? "video" : "image";

renderAll();
setDirty(true);

const formData = new FormData();
formData.append("file", file);

const csrf = getCsrfToken();

try {
  const response = await fetch("/admin/settings/upload", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": csrf,
      "X-CSRF-Token": csrf
    },
    body: formData
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok || !data.success) {
    throw new Error(data.message || data.error || "Upload thất bại.");
  }

  frame.media_url = data.url || data.public_url || data.file_url || "";
  frame.media_type = file.type.startsWith("video/") ? "video" : "image";

  renderAll();
  pushHistory();
  setDirty(true);
  notify("Tải media thành công.");
} catch (error) {
  frame.media_url = previousUrl;
  renderAll();
  notify(error.message || "Không thể tải media.", true);
} finally {
  URL.revokeObjectURL(tempUrl);
  uploadTargetFrameId = null;

  const input = $("#sfcMediaUploadInput");
  if (input) {
    input.value = "";
  }
}
  

}

function buildPreviewCanvas() {
const output = canvasOutput();

  
const preview = document.createElement("div");
preview.className = "sfc-desktop-canvas is-no-grid";
preview.style.width = `${output.desktop.width}px`;
preview.style.height = `${output.desktop.height}px`;
preview.style.borderRadius = `${output.style.radius}px`;
preview.style.backgroundColor = output.style.background;
preview.style.position = "relative";
preview.style.overflow = "hidden";

output.frames.forEach((frame) => {
  const node = document.createElement(frame.link ? "a" : "div");
  node.className = "sfc-frame";
  node.style.setProperty("--sfc-x", `${frame.x}px`);
  node.style.setProperty("--sfc-y", `${frame.y}px`);
  node.style.setProperty("--sfc-w", `${frame.w}px`);
  node.style.setProperty("--sfc-h", `${frame.h}px`);
  node.style.setProperty("--sfc-radius", `${frame.radius}px`);
  node.style.setProperty("--sfc-z", `${frame.z}`);
  node.style.setProperty("--sfc-fit", frame.fit || "cover");
  node.style.opacity = String(clamp(toNumber(frame.opacity, 100), 0, 100) / 100);
  node.style.cursor = frame.link ? "pointer" : "default";
  node.style.pointerEvents = frame.link ? "auto" : "none";

  if (frame.link) {
    node.href = frame.link;
    node.target = "_blank";
    node.rel = "noopener";
  }

  node.innerHTML = `<div class="sfc-frame-inner">${renderFrameContent(frame)}</div>`;
  preview.appendChild(node);
});

return preview;
  

}

function openPreview() {
const modal = $("#sfcPreviewModal");
const mount = $("#sfcPreviewMount");

  
if (!modal || !mount) {
  return;
}

mount.innerHTML = "";
mount.appendChild(buildPreviewCanvas());
modal.hidden = false;
root.classList.add("is-previewing");
  

}

function closePreview() {
const modal = $("#sfcPreviewModal");

  
if (modal) {
  modal.hidden = true;
}

if (root) {
  root.classList.remove("is-previewing");
}
  

}

function bindCanvasSettings() {
const preset = $("#sfcPreset");

  
if (preset) {
  preset.addEventListener("change", () => {
    applyPreset(preset.value);
  });
}

$$("[data-sfc-canvas-width], [data-sfc-canvas-height], [data-sfc-canvas-bg], [data-sfc-canvas-radius], [data-sfc-grid-size], [data-sfc-canvas-padding], [data-sfc-canvas-enabled], [data-sfc-grid-enabled], [data-sfc-snap-enabled]").forEach((input) => {
  input.addEventListener("input", () => updateCanvasSettingFromInput(input, false));
  input.addEventListener("change", () => updateCanvasSettingFromInput(input, true));
});
  

}

function bindProperties() {
$$("[data-sfc-prop]").forEach((input) => {
input.addEventListener("input", () => updateSelectedFrameFromInput(input, false));
input.addEventListener("change", () => updateSelectedFrameFromInput(input, true));
});
}

function bindActions() {
document.addEventListener("click", (event) => {
const addButton = event.target.closest("[data-sfc-add]");
if (addButton && root.contains(addButton)) {
addFrame(addButton.dataset.sfcAdd);
return;
}

  
  const templateButton = event.target.closest("[data-sfc-template]");
  if (templateButton && root.contains(templateButton)) {
    addTemplate(templateButton.dataset.sfcTemplate);
    return;
  }

  const actionButton = event.target.closest("[data-sfc-action]");
  if (!actionButton || !root.contains(actionButton)) {
    return;
  }

  const action = actionButton.dataset.sfcAction;

  if (action === "add-media-frame") addFrame("media");
  if (action === "toggle-grid") {
    state.style.show_grid = !state.style.show_grid;
    renderAll();
    pushHistory();
    setDirty(true);
  }
  if (action === "toggle-snap") {
    state.style.snap = !state.style.snap;
    renderAll();
    pushHistory();
    setDirty(true);
  }
  if (action === "fit-screen") fitScreen();
  if (action === "zoom-in") setZoom(zoom + 0.1);
  if (action === "zoom-out") setZoom(zoom - 0.1);
  if (action === "preview-canvas") openPreview();
  if (action === "close-preview") closePreview();
  if (action === "clear-canvas") clearCanvas();
  if (action === "delete-selected") deleteSelected();
  if (action === "duplicate-selected") duplicateSelected();
  if (action === "bring-forward") bringForward();
  if (action === "send-backward") sendBackward();
  if (action === "lock-selected") toggleLockSelected();
  if (action === "unlock-all") unlockAll();
  if (action === "select-all") selectAll();
  if (action === "align-left") alignSelected("left");
  if (action === "align-center") alignSelected("center");
  if (action === "align-right") alignSelected("right");
  if (action === "undo") undo();
  if (action === "redo") redo();

  if (action === "upload-selected-media") {
    const frame = getSelectedFrame();

    if (!frame) {
      notify("Hãy chọn một khung trước khi upload.", true);
      return;
    }

    uploadTargetFrameId = frame.id;

    const input = $("#sfcMediaUploadInput");
    if (input) {
      input.click();
    }
  }
});

if (canvasEl) {
  canvasEl.addEventListener("pointerdown", (event) => {
    if (event.target === canvasEl || event.target.classList.contains("sfc-frame-layer")) {
      clearSelection();
    }
  });
}

const uploadInput = $("#sfcMediaUploadInput");

if (uploadInput) {
  uploadInput.addEventListener("change", () => {
    const file = uploadInput.files && uploadInput.files[0];
    uploadMediaFile(file);
  });
}

document.addEventListener("keydown", (event) => {
  if (!root || root.hidden) {
    return;
  }

  const active = document.activeElement;
  const isTyping = active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);

  if (isTyping) {
    return;
  }

  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
    event.preventDefault();
    undo();
  }

  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
    event.preventDefault();
    redo();
  }

  if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    deleteSelected();
  }

  if (event.key === "Escape") {
    clearSelection();
    closePreview();
  }
});

const saveBtn = document.querySelector('[data-sfb-action="save"]');

if (saveBtn) {
  saveBtn.addEventListener("click", () => {
    syncHiddenInput();
    window.setTimeout(() => setDirty(false), 800);
  });
}
  

}

function init() {
root = $("#sfcDesignerRoot");

  
if (!root) {
  return;
}

hiddenInput = $("#homepage_canvas", root);
canvasEl = $("#sfcDesktopCanvas", root);
layerEl = $("#sfcFrameLayer", root);
viewportEl = $("#sfcCanvasViewport", root);

state = parseStoredCanvas();
zoom = 1;
selectedId = state.frames[0] ? state.frames[0].id : null;

bindCanvasSettings();
bindProperties();
bindActions();

renderAll();
pushHistory();
setDirty(false);

window.StorefrontCanvasDesigner = {
  getState: () => canvasOutput(),
  setState: (nextState) => {
    state = normalizeCanvas(nextState);
    selectedId = state.frames[0] ? state.frames[0].id : null;
    renderAll();
    pushHistory();
    setDirty(true);
  },
  sync: syncHiddenInput,
  fit: fitScreen,
  addFrame: addFrame
};
  

}

document.addEventListener("DOMContentLoaded", init);
})();

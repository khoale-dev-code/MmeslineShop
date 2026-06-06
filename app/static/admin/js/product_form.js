(function () {
  "use strict";

  if (window.__MM_PRODUCT_FORM_BOUND__ === true) {
    return;
  }

  window.__MM_PRODUCT_FORM_BOUND__ = true;

  const VND = new Intl.NumberFormat("vi-VN");

  const SELECTOR = {
    form: "#productForm",

    productName: "#productName",
    productSlug: "#productSlug",

    seoTitle: "#seoTitle",
    seoDescription: "#seoDescription",
    seoKeywords: "#seoKeywords",
    searchKeywords: "#searchKeywords",
    seoTitleCount: "#seoTitleCount",
    seoDescriptionCount: "#seoDescriptionCount",
    seoTitleCounterState: "#seoTitleCounterState",
    seoDescriptionCounterState: "#seoDescriptionCounterState",
    seoCheckName: "#seoCheckName",
    seoCheckTitle: "#seoCheckTitle",
    seoCheckDesc: "#seoCheckDesc",
    seoScoreBadge: "#seoScoreBadge",
    seoPreviewTitle: "#seoPreviewTitle",
    seoPreviewDescription: "#seoPreviewDescription",
    seoPreviewUrl: "#seoPreviewUrl",
    seoGenerateBtn: "#seoGenerateBtn",
    seoCopyNameBtn: "#seoCopyNameBtn",

    pricePreview: "#pricePreview",
    comparePreview: "#comparePreview",
    discountPreview: "#discountPreview",
    discountPreviewText: "#discountPreviewText",
    comparePriceHelp: "#comparePriceHelp",
    profitPreview: "#profitPreview",
    marginPreview: "#marginPreview",

    productSku: "#productSku",
    productBarcode: "#productBarcode",
    generateSkuBtn: "#generateSkuBtn",
    generateBarcodeBtn: "#generateBarcodeBtn",

    tagBox: "#tagBox",
    tagInput: "#tagInput",
    tagList: "#tagList",
    tagDropdown: "#tagDropdown",
    tagsHidden: "#tagsHidden",
    currentTagsJson: "currentTagsJson",
    tagOptionsJson: "tagOptionsJson",

    descriptionEditor: "#descriptionEditor"
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const moneyDigits = (value) => String(value || "").replace(/[^\d]/g, "");
  const toMoneyNumber = (value) => Number(moneyDigits(value) || 0);
  const formatMoneyInput = (value) => {
    const digits = moneyDigits(value);
    return digits ? VND.format(Number(digits)) : "";
  };
  const formatVnd = (value) => VND.format(Number(value || 0)) + "đ";

  function cleanText(value) {
    return String(value || "").trim();
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function slugifyVi(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "d")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function readJsonScript(id, fallback = []) {
    const el = document.getElementById(id);
    if (!el) return fallback;

    try {
      const parsed = JSON.parse(el.textContent || "[]");
      return parsed || fallback;
    } catch {
      return fallback;
    }
  }

  function setText(selector, value) {
    const el = $(selector);
    if (el) el.textContent = String(value);
  }

  function toggleHidden(selector, hidden) {
    const el = $(selector);
    if (el) el.classList.toggle("hidden", Boolean(hidden));
  }

  function getFieldValue(selector) {
    return cleanText($(selector)?.value || "");
  }

  function randomDigits(length) {
    let output = "";

    if (window.crypto && window.crypto.getRandomValues) {
      const arr = new Uint8Array(length);
      window.crypto.getRandomValues(arr);

      arr.forEach((n) => {
        output += String(n % 10);
      });

      return output;
    }

    for (let i = 0; i < length; i += 1) {
      output += String(Math.floor(Math.random() * 10));
    }

    return output;
  }

  function makeBarcode() {
    return "290" + randomDigits(10);
  }

  function makeSku(name) {
    const base = slugifyVi(name || "MMESTLINE")
      .split("-")
      .filter(Boolean)
      .slice(0, 4)
      .map((part) => part.slice(0, 4).toUpperCase())
      .join("-");

    return "MM-" + (base || "ITEM") + "-" + randomDigits(4);
  }

  function getBrandName() {
    return cleanText(document.querySelector("[name='brand']")?.value) || "MMESTLINE";
  }

  function getGenderText() {
    const gender = document.querySelector("[name='gender']")?.value || "unisex";

    return {
      unisex: "phù hợp phong cách unisex",
      women: "dành cho nữ",
      men: "dành cho nam",
      kids: "dành cho trẻ em",
      accessories: "thuộc nhóm phụ kiện"
    }[gender] || "phù hợp nhiều phong cách";
  }

  const MoneyInputs = {
    init(context = document) {
      $$("[data-money]", context).forEach((input) => {
        if (input.dataset.moneyBound === "1") return;

        input.dataset.moneyBound = "1";
        input.value = formatMoneyInput(input.value);

        input.addEventListener("input", () => {
          input.value = formatMoneyInput(input.value);

          try {
            input.setSelectionRange(input.value.length, input.value.length);
          } catch {}

          PricePreview.update();
        });

        input.addEventListener("blur", () => {
          input.value = formatMoneyInput(input.value);
          PricePreview.update();
        });
      });
    },

    normalizeBeforeSubmit() {
      $$("[data-money]").forEach((input) => {
        input.value = moneyDigits(input.value);
      });
    }
  };

  const PricePreview = {
    update() {
      const price = toMoneyNumber(document.querySelector("[name='price']")?.value);
      const compare = toMoneyNumber(document.querySelector("[name='compare_at_price']")?.value);
      const cost = toMoneyNumber(document.querySelector("[name='cost_price']")?.value);

      setText(SELECTOR.pricePreview, price ? formatVnd(price) : "0đ");

      const validCompare = Boolean(compare && price && compare > price);

      toggleHidden(SELECTOR.comparePreview, !validCompare);
      toggleHidden(SELECTOR.discountPreview, !validCompare);

      if (validCompare) {
        const discount = Math.round(((compare - price) / compare) * 100);

        setText(SELECTOR.comparePreview, formatVnd(compare));
        setText(SELECTOR.discountPreview, "-" + discount + "%");
        setText(SELECTOR.discountPreviewText, "-" + discount + "%");

        this.setCompareHelp("Hợp lệ. Website sẽ hiển thị giá gạch ngang.", "ok");
      } else {
        setText(SELECTOR.discountPreviewText, "Không có");

        if (compare && price && compare <= price) {
          this.setCompareHelp(
            "Giá so sánh phải lớn hơn giá bán. Nếu không, hệ thống sẽ bỏ qua.",
            "warning"
          );
        } else {
          this.setCompareHelp(
            "Nếu lớn hơn giá bán, storefront sẽ hiển thị giá gạch ngang.",
            ""
          );
        }
      }

      const profit = price && cost ? price - cost : 0;
      const margin = price && cost && price > 0
        ? Math.round(((price - cost) / price) * 100)
        : 0;

      setText(SELECTOR.profitPreview, profit > 0 ? formatVnd(profit) : "0đ");
      setText(SELECTOR.marginPreview, margin > 0 ? margin + "%" : "0%");
    },

    setCompareHelp(message, state) {
      const help = $(SELECTOR.comparePriceHelp);
      if (!help) return;

      help.textContent = message;
      help.classList.remove("is-ok", "is-warning");

      if (state === "ok") help.classList.add("is-ok");
      if (state === "warning") help.classList.add("is-warning");
    }
  };

  const SeoChecker = {
    init() {
      const name = $(SELECTOR.productName);
      const slug = $(SELECTOR.productSlug);
      const seoTitle = $(SELECTOR.seoTitle);
      const seoDesc = $(SELECTOR.seoDescription);
      const generateBtn = $(SELECTOR.seoGenerateBtn);
      const copyNameBtn = $(SELECTOR.seoCopyNameBtn);

      if (name && name.dataset.seoBound !== "1") {
        name.dataset.seoBound = "1";

        name.addEventListener("input", () => {
          if (slug && !slug.dataset.touched && !slug.value.trim()) {
            slug.value = slugifyVi(name.value);
          }

          if (seoTitle && !seoTitle.dataset.touched && !seoTitle.value.trim()) {
            seoTitle.value = this.makeTitle().slice(0, 70);
          }

          this.update();
        });
      }

      if (slug && slug.dataset.seoBound !== "1") {
        slug.dataset.seoBound = "1";

        slug.addEventListener("input", () => {
          slug.dataset.touched = "1";
          slug.value = slugifyVi(slug.value);
          this.update();
        });
      }

      if (seoTitle && seoTitle.dataset.seoBound !== "1") {
        seoTitle.dataset.seoBound = "1";

        seoTitle.addEventListener("input", () => {
          seoTitle.dataset.touched = "1";
          this.update();
        });
      }

      if (seoDesc && seoDesc.dataset.seoBound !== "1") {
        seoDesc.dataset.seoBound = "1";
        seoDesc.addEventListener("input", () => this.update());
      }

      if (generateBtn && generateBtn.dataset.seoBound !== "1") {
        generateBtn.dataset.seoBound = "1";
        generateBtn.addEventListener("click", () => this.generate());
      }

      if (copyNameBtn && copyNameBtn.dataset.seoBound !== "1") {
        copyNameBtn.dataset.seoBound = "1";
        copyNameBtn.addEventListener("click", () => this.copyName());
      }

      this.update();
    },

    makeTitle() {
      const name = getFieldValue(SELECTOR.productName);
      const brand = getBrandName();

      if (!name) return "";

      if (name.toLowerCase().includes(brand.toLowerCase())) {
        return name;
      }

      return `${name} | ${brand}`;
    },

    makeDescription() {
      const name = getFieldValue(SELECTOR.productName) || "Sản phẩm MMESTLINE";
      const tags = getFieldValue(SELECTOR.tagsHidden);

      const tagText = tags
        ? ` Gợi ý phong cách: ${tags
            .split(",")
            .map((x) => cleanText(x))
            .filter(Boolean)
            .slice(0, 3)
            .join(", ")}.`
        : "";

      return `${name} ${getGenderText()}, thiết kế tối giản, dễ phối đồ và phù hợp sử dụng hằng ngày.${tagText}`.slice(0, 170);
    },

    makeKeywords() {
      const name = getFieldValue(SELECTOR.productName);
      const brand = getBrandName();
      const gender = document.querySelector("[name='gender']")?.value || "";
      const tags = getFieldValue(SELECTOR.tagsHidden);

      return [
        name,
        brand,
        gender,
        tags,
        "local brand",
        "thời trang basic"
      ]
        .join(", ")
        .split(",")
        .map((x) => cleanText(x))
        .filter(Boolean)
        .filter((x, index, arr) => {
          return arr.findIndex((y) => y.toLowerCase() === x.toLowerCase()) === index;
        })
        .slice(0, 12)
        .join(", ");
    },

    generate() {
      const seoTitle = $(SELECTOR.seoTitle);
      const seoDesc = $(SELECTOR.seoDescription);
      const seoKeywords = $(SELECTOR.seoKeywords);
      const searchKeywords = $(SELECTOR.searchKeywords);

      if (seoTitle) {
        seoTitle.value = this.makeTitle().slice(0, 70);
        seoTitle.dataset.touched = "1";
      }

      if (seoDesc) {
        seoDesc.value = this.makeDescription();
      }

      const keywords = this.makeKeywords();

      if (seoKeywords && !seoKeywords.value.trim()) {
        seoKeywords.value = keywords;
      }

      if (searchKeywords && !searchKeywords.value.trim()) {
        searchKeywords.value = keywords;
      }

      this.update();
    },

    copyName() {
      const seoTitle = $(SELECTOR.seoTitle);

      if (seoTitle) {
        seoTitle.value = this.makeTitle().slice(0, 70);
        seoTitle.dataset.touched = "1";
        seoTitle.focus();
      }

      this.update();
    },

    update() {
      const nameLen = getFieldValue(SELECTOR.productName).length;
      const title = getFieldValue(SELECTOR.seoTitle);
      const desc = getFieldValue(SELECTOR.seoDescription);
      const slug = getFieldValue(SELECTOR.productSlug);

      const titleLen = title.length;
      const descLen = desc.length;

      setText(SELECTOR.seoTitleCount, titleLen);
      setText(SELECTOR.seoDescriptionCount, descLen);

      const nameOk = nameLen >= 8;
      const titleOk = titleLen >= 30 && titleLen <= 70;
      const descOk = descLen >= 80 && descLen <= 170;

      this.setState(SELECTOR.seoCheckName, nameOk);
      this.setState(SELECTOR.seoCheckTitle, titleOk);
      this.setState(SELECTOR.seoCheckDesc, descOk);

      this.setCounterState(SELECTOR.seoTitleCounterState, titleLen, 30, 70);
      this.setCounterState(SELECTOR.seoDescriptionCounterState, descLen, 80, 170);

      const score = [nameOk, titleOk, descOk].filter(Boolean).length;

      setText(SELECTOR.seoScoreBadge, `${score}/3`);
      setText(SELECTOR.seoPreviewTitle, title || this.makeTitle() || "Tên sản phẩm | MMESTLINE");
      setText(
        SELECTOR.seoPreviewDescription,
        desc || "Mô tả ngắn giúp khách hàng hiểu sản phẩm, chất liệu, form dáng và điểm nổi bật."
      );
      setText(SELECTOR.seoPreviewUrl, "/product/" + (slug || "duong-dan-san-pham"));
    },

    setCounterState(selector, value, min, max) {
      const el = $(selector);
      if (!el) return;

      el.classList.remove("is-ok", "is-warning", "is-bad");

      if (value === 0) {
        el.classList.add("is-warning");
      } else if (value >= min && value <= max) {
        el.classList.add("is-ok");
      } else if (value > max) {
        el.classList.add("is-bad");
      } else {
        el.classList.add("is-warning");
      }
    },

    setState(selector, ok) {
      const el = $(selector);
      if (!el) return;

      el.classList.toggle("is-ok", Boolean(ok));

      const icon = $("i", el);
      if (icon) {
        icon.className = ok ? "fa-solid fa-circle-check" : "fa-solid fa-circle";
      }
    }
  };

  const Tags = {
    items: [],
    options: [],

    normalize(value) {
      return String(value || "")
        .trim()
        .replace(/^#+/, "")
        .replace(/\s+/g, " ")
        .slice(0, 60);
    },

    unique(list) {
      const seen = new Set();
      const output = [];

      (list || []).forEach((item) => {
        const tag = this.normalize(item);
        const key = tag.toLowerCase();

        if (!tag || seen.has(key)) return;

        seen.add(key);
        output.push(tag);
      });

      return output;
    },

    init() {
      const input = $(SELECTOR.tagInput);
      const dropdown = $(SELECTOR.tagDropdown);
      const list = $(SELECTOR.tagList);

      if (!input || !dropdown || !list) return;
      if (input.dataset.tagsBound === "1") return;

      input.dataset.tagsBound = "1";

      const current = readJsonScript(SELECTOR.currentTagsJson, []);
      const options = readJsonScript(SELECTOR.tagOptionsJson, []);

      this.items = this.unique(
        Array.isArray(current) ? current : String(current || "").split(",")
      );

      this.options = this.unique([
        ...(Array.isArray(options) ? options : String(options || "").split(",")),
        ...this.items
      ]).sort((a, b) => a.localeCompare(b, "vi"));

      this.render();

      input.addEventListener("focus", () => this.show());
      input.addEventListener("input", () => this.filter());

      input.addEventListener("blur", () => {
        window.setTimeout(() => dropdown.classList.add("hidden"), 160);
      });

      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === ",") {
          event.preventDefault();
          this.add(input.value);
          input.value = "";
          this.show();
        }

        if (event.key === "Backspace" && !input.value && this.items.length) {
          this.remove(this.items[this.items.length - 1]);
        }

        if (event.key === "Escape") {
          dropdown.classList.add("hidden");
        }
      });

      document.addEventListener("click", (event) => {
        const box = $(SELECTOR.tagBox);

        if (box && !box.contains(event.target)) {
          dropdown.classList.add("hidden");
        }
      });
    },

    add(value) {
      const tag = this.normalize(value);
      if (!tag) return;

      if (this.items.some((item) => item.toLowerCase() === tag.toLowerCase())) {
        return;
      }

      this.items.push(tag);

      if (!this.options.some((item) => item.toLowerCase() === tag.toLowerCase())) {
        this.options.push(tag);
        this.options = this.unique(this.options).sort((a, b) => a.localeCompare(b, "vi"));
      }

      this.render();
      SeoChecker.update();
    },

    remove(value) {
      const key = this.normalize(value).toLowerCase();

      this.items = this.items.filter((tag) => tag.toLowerCase() !== key);

      this.render();
      SeoChecker.update();
    },

    sync() {
      const hidden = $(SELECTOR.tagsHidden);
      if (hidden) hidden.value = this.items.join(", ");
    },

    render() {
      this.renderTags();
      this.renderDropdown();
      this.sync();
      this.filter();
    },

    renderTags() {
      const list = $(SELECTOR.tagList);
      if (!list) return;

      list.innerHTML = this.items.map((tag) => `
        <span class="mm-tag-chip">
          <span>#${escapeHtml(tag)}</span>
          <button type="button" data-remove-tag="${escapeHtml(tag)}" aria-label="Xóa tag ${escapeHtml(tag)}">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </span>
      `).join("");
    },

    renderDropdown() {
      const dropdown = $(SELECTOR.tagDropdown);
      if (!dropdown) return;

      dropdown.innerHTML = this.options.map((tag) => `
        <button type="button" class="mm-tag-option" data-add-tag="${escapeHtml(tag)}">
          <span>#${escapeHtml(tag)}</span>
          <small>Chọn</small>
        </button>
      `).join("");
    },

    show() {
      const dropdown = $(SELECTOR.tagDropdown);
      if (!dropdown) return;

      dropdown.classList.remove("hidden");
      this.filter();
    },

    filter() {
      const input = $(SELECTOR.tagInput);
      const dropdown = $(SELECTOR.tagDropdown);

      if (!input || !dropdown) return;

      const query = this.normalize(input.value).toLowerCase();
      const selected = new Set(this.items.map((tag) => tag.toLowerCase()));

      $$(".mm-tag-option", dropdown).forEach((button) => {
        const tag = this.normalize(button.dataset.addTag);
        const key = tag.toLowerCase();
        const hide = selected.has(key) || Boolean(query && !key.includes(query));

        button.classList.toggle("is-hidden", hide);
      });

      const visible = $$(".mm-tag-option:not(.is-hidden)", dropdown).length;
      dropdown.classList.toggle("hidden", visible === 0 && !input.value.trim());
    }
  };

  const Codes = {
    init() {
      const sku = $(SELECTOR.productSku);
      const barcode = $(SELECTOR.productBarcode);

      if (sku && sku.dataset.codeBound !== "1") {
        sku.dataset.codeBound = "1";

        sku.addEventListener("input", () => {
          sku.value = sku.value.toUpperCase().replace(/\s+/g, "-");
        });
      }

      if (barcode && barcode.dataset.codeBound !== "1") {
        barcode.dataset.codeBound = "1";

        barcode.addEventListener("input", () => {
          barcode.value = barcode.value.replace(/[^\dA-Za-z\-]/g, "").toUpperCase();
        });
      }
    },

    generateSku() {
      const sku = $(SELECTOR.productSku);
      const name = $(SELECTOR.productName)?.value || "";

      if (!sku) return;

      sku.value = makeSku(name);
      sku.focus();
    },

    generateBarcode() {
      const barcode = $(SELECTOR.productBarcode);

      if (!barcode) return;

      barcode.value = makeBarcode();
      barcode.focus();
    },

    normalizeBeforeSubmit() {
      const barcode = $(SELECTOR.productBarcode);

      if (barcode) {
        barcode.value = barcode.value.replace(/[^\dA-Za-z\-]/g, "").toUpperCase();
      }

      const sku = $(SELECTOR.productSku);

      if (sku) {
        sku.value = sku.value.toUpperCase().replace(/\s+/g, "-");
      }
    }
  };

  const DescriptionEditor = {
  init() {
    const textarea = $(SELECTOR.descriptionEditor);

    if (!textarea) return;

    if (
      window.CKEDITOR &&
      typeof window.CKEDITOR.replace === "function" &&
      !window.CKEDITOR.instances.descriptionEditor
    ) {
      window.CKEDITOR.config.versionCheck = false;

      window.CKEDITOR.replace("descriptionEditor", {
        height: 430,
        versionCheck: false,
        allowedContent: true,
        removePlugins: "elementspath",
        resize_enabled: true,
        toolbar: [
          { name: "document", items: ["Source"] },
          { name: "clipboard", items: ["Undo", "Redo"] },
          { name: "styles", items: ["Format", "FontSize"] },
          { name: "basicstyles", items: ["Bold", "Italic", "Underline", "Strike", "RemoveFormat"] },
          { name: "paragraph", items: ["NumberedList", "BulletedList", "Blockquote"] },
          { name: "alignment", items: ["JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"] },
          { name: "links", items: ["Link", "Unlink"] },
          { name: "insert", items: ["Image", "Table", "HorizontalRule", "SpecialChar"] },
          { name: "tools", items: ["Maximize"] }
        ]
      });
    }

    window.MMDescriptionEditor = window.MMDescriptionEditor || {};
    window.MMDescriptionEditor.sync = () => this.sync();
  },

  sync() {
    if (
      window.CKEDITOR &&
      window.CKEDITOR.instances &&
      window.CKEDITOR.instances.descriptionEditor
    ) {
      window.CKEDITOR.instances.descriptionEditor.updateElement();
    }
  }
};

  const Submit = {
    init() {
      const form = $(SELECTOR.form);

      if (!form || form.dataset.productFormJsBound === "1") return;

      form.dataset.productFormJsBound = "1";

      form.addEventListener("submit", () => {
        Codes.normalizeBeforeSubmit();
        MoneyInputs.normalizeBeforeSubmit();
        Tags.sync();
        DescriptionEditor.sync();

        if (
          window.MM &&
          window.MM.VariantsLite &&
          typeof window.MM.VariantsLite.normalizeBeforeSubmit === "function"
        ) {
          window.MM.VariantsLite.normalizeBeforeSubmit();
        }

        if (
          window.MM &&
          window.MM.ProductMedia &&
          typeof window.MM.ProductMedia.refreshOrder === "function"
        ) {
          window.MM.ProductMedia.refreshOrder();
        }

        this.disableSubmitButtons(form);
      });
    },

    disableSubmitButtons(form) {
      $$(".mm-save-btn", form).forEach((button) => {
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
      });
    }
  };

  function bindDelegatedEvents() {
    if (document.documentElement.dataset.productDelegatedBound === "1") return;

    document.documentElement.dataset.productDelegatedBound = "1";

    document.addEventListener("click", (event) => {
      const addTagBtn = event.target.closest("[data-add-tag]");
      if (addTagBtn) {
        Tags.add(addTagBtn.dataset.addTag);

        const input = $(SELECTOR.tagInput);
        if (input) {
          input.value = "";
          input.focus();
        }

        Tags.show();
        return;
      }

      const removeTagBtn = event.target.closest("[data-remove-tag]");
      if (removeTagBtn) {
        Tags.remove(removeTagBtn.dataset.removeTag);
        return;
      }

      if (event.target.closest(SELECTOR.generateSkuBtn)) {
        Codes.generateSku();
        return;
      }

      if (event.target.closest(SELECTOR.generateBarcodeBtn)) {
        Codes.generateBarcode();
      }
    });
  }

  function init() {
    MoneyInputs.init(document);
    PricePreview.update();

    Tags.init();
    SeoChecker.init();
    Codes.init();
    DescriptionEditor.init();

    bindDelegatedEvents();
    Submit.init();

    console.info("[MMProductForm] ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.MM = window.MM || {};

  window.MM.ProductForm = {
    digits: moneyDigits,
    formatMoney: formatMoneyInput,
    formatVnd,
    slugifyVi,
    updatePricePreview: () => PricePreview.update(),
    generateSku: () => Codes.generateSku(),
    generateBarcode: () => Codes.generateBarcode(),
    syncDescription: () => DescriptionEditor.sync(),
    normalizeBeforeSubmit: () => {
      Codes.normalizeBeforeSubmit();
      MoneyInputs.normalizeBeforeSubmit();
      Tags.sync();
      DescriptionEditor.sync();
    }
  };

  window.ProductForm = window.ProductForm || {};
  window.ProductForm.generateSku = () => Codes.generateSku();
  window.ProductForm.generateBarcode = () => Codes.generateBarcode();
})();
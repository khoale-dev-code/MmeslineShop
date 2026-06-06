(function () {
  "use strict";

  const VND = new Intl.NumberFormat("vi-VN");

  const SELECTOR = {
    form: "#productForm",

    productName: "#productName",
    productSlug: "#productSlug",

    seoTitle: "#seoTitle",
    seoDescription: "#seoDescription",
    seoTitleCount: "#seoTitleCount",
    seoDescriptionCount: "#seoDescriptionCount",
    seoCheckName: "#seoCheckName",
    seoCheckTitle: "#seoCheckTitle",
    seoCheckDesc: "#seoCheckDesc",

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
    tagOptionsJson: "tagOptionsJson"
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const digits = (value) => String(value || "").replace(/[^\d]/g, "");
  const toNumber = (value) => Number(digits(value) || 0);
  const formatMoney = (value) => digits(value) ? VND.format(Number(digits(value))) : "";
  const formatVnd = (value) => VND.format(Number(value || 0)) + "đ";

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
      return JSON.parse(el.textContent || "[]");
    } catch {
      return fallback;
    }
  }

  function setText(selector, value) {
    const el = $(selector);
    if (el) el.textContent = String(value);
  }

  function setHidden(selector, hidden) {
    const el = $(selector);
    if (el) el.classList.toggle("hidden", Boolean(hidden));
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

  const MoneyInputs = {
    init(context = document) {
      $$("[data-money]", context).forEach((input) => {
        if (input.dataset.moneyBound === "1") return;

        input.dataset.moneyBound = "1";
        input.value = formatMoney(input.value);

        input.addEventListener("input", () => {
          input.value = formatMoney(input.value);

          try {
            input.setSelectionRange(input.value.length, input.value.length);
          } catch {}

          PricePreview.update();
        });

        input.addEventListener("blur", () => {
          input.value = formatMoney(input.value);
          PricePreview.update();
        });
      });
    },

    normalizeBeforeSubmit() {
      $$("[data-money]").forEach((input) => {
        input.value = digits(input.value);
      });
    }
  };

  const PricePreview = {
    update() {
      const price = toNumber($("[name='price']")?.value);
      const compare = toNumber($("[name='compare_at_price']")?.value);
      const cost = toNumber($("[name='cost_price']")?.value);

      setText(SELECTOR.pricePreview, price ? formatVnd(price) : "0đ");

      const validCompare = Boolean(compare && price && compare > price);

      setHidden(SELECTOR.comparePreview, !validCompare);
      setHidden(SELECTOR.discountPreview, !validCompare);

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

      if (name) {
        name.addEventListener("input", () => {
          if (slug && !slug.dataset.touched && !slug.value.trim()) {
            slug.value = slugifyVi(name.value);
          }

          if (seoTitle && !seoTitle.dataset.touched) {
            seoTitle.value = name.value.slice(0, 70);
          }

          this.update();
        });
      }

      if (slug) {
        slug.addEventListener("input", () => {
          slug.dataset.touched = "1";
          slug.value = slugifyVi(slug.value);
        });
      }

      if (seoTitle) {
        seoTitle.addEventListener("input", () => {
          seoTitle.dataset.touched = "1";
          this.update();
        });
      }

      if (seoDesc) {
        seoDesc.addEventListener("input", () => this.update());
      }

      this.update();
    },

    update() {
      const nameLen = ($(SELECTOR.productName)?.value || "").trim().length;
      const titleLen = ($(SELECTOR.seoTitle)?.value || "").trim().length;
      const descLen = ($(SELECTOR.seoDescription)?.value || "").trim().length;

      setText(SELECTOR.seoTitleCount, titleLen);
      setText(SELECTOR.seoDescriptionCount, descLen);

      this.setState(SELECTOR.seoCheckName, nameLen >= 8);
      this.setState(SELECTOR.seoCheckTitle, titleLen >= 30 && titleLen <= 70);
      this.setState(SELECTOR.seoCheckDesc, descLen >= 80 && descLen <= 170);
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
        setTimeout(() => dropdown.classList.add("hidden"), 160);
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

      if (this.items.some((item) => item.toLowerCase() === tag.toLowerCase())) return;

      this.items.push(tag);

      if (!this.options.some((item) => item.toLowerCase() === tag.toLowerCase())) {
        this.options.push(tag);
        this.options = this.unique(this.options).sort((a, b) => a.localeCompare(b, "vi"));
      }

      this.render();
    },

    remove(value) {
      const key = this.normalize(value).toLowerCase();
      this.items = this.items.filter((tag) => tag.toLowerCase() !== key);
      this.render();
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
        const hide = selected.has(key) || (query && !key.includes(query));

        button.classList.toggle("is-hidden", Boolean(hide));
      });

      const visible = $$(".mm-tag-option:not(.is-hidden)", dropdown).length;
      dropdown.classList.toggle("hidden", visible === 0 && !input.value.trim());
    }
  };

  const Codes = {
    init() {
      const sku = $(SELECTOR.productSku);
      const barcode = $(SELECTOR.productBarcode);

      if (sku) {
        sku.addEventListener("input", () => {
          sku.value = sku.value.toUpperCase().replace(/\s+/g, "-");
        });
      }

      if (barcode) {
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

      if (barcode && !barcode.value.trim()) {
        barcode.value = makeBarcode();
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

        if (window.MMDescriptionEditor && typeof window.MMDescriptionEditor.sync === "function") {
          window.MMDescriptionEditor.sync();
        }

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
      const buttons = $$(".mm-save-btn", form);

      buttons.forEach((button) => {
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
      });
    }
  };

  function bindDelegatedEvents() {
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

    SeoChecker.init();
    Tags.init();
    Codes.init();

    bindDelegatedEvents();
    Submit.init();
  }

  document.addEventListener("DOMContentLoaded", init);

  window.MM = window.MM || {};

  window.MM.ProductForm = {
    formatMoney,
    digits,
    updatePricePreview: () => PricePreview.update(),
    generateSku: () => Codes.generateSku(),
    generateBarcode: () => Codes.generateBarcode()
  };

  window.ProductForm = window.ProductForm || {};
  window.ProductForm.generateSku = () => Codes.generateSku();
  window.ProductForm.generateBarcode = () => Codes.generateBarcode();
})();
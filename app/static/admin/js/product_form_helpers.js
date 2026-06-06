(function () {
  "use strict";

  const formatter = new Intl.NumberFormat("vi-VN");

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function onlyDigits(value) {
    return String(value || "").replace(/[^\d]/g, "");
  }

  function formatMoneyValue(value) {
    const digits = onlyDigits(value);
    if (!digits) return "";
    return formatter.format(Number(digits));
  }

  function parseMoney(value) {
    return Number(onlyDigits(value) || 0);
  }

  function moneyNumber(selector, root = document) {
    const input = qs(selector, root);
    return input ? parseMoney(input.value) : 0;
  }

  function formatVnd(value) {
    const number = Number(value || 0);
    return formatter.format(number) + "đ";
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

  function readJson(id, fallback) {
    const el = document.getElementById(id);
    if (!el) return fallback;

    try {
      return JSON.parse(el.textContent || "[]");
    } catch (err) {
      return fallback;
    }
  }

  function randomDigits(length) {
    let output = "";

    if (window.crypto && window.crypto.getRandomValues) {
      const arr = new Uint8Array(length);
      window.crypto.getRandomValues(arr);

      for (let i = 0; i < length; i += 1) {
        output += String(arr[i] % 10);
      }

      return output;
    }

    for (let i = 0; i < length; i += 1) {
      output += String(Math.floor(Math.random() * 10));
    }

    return output;
  }

  function makeInternalBarcode() {
    return "290" + randomDigits(10);
  }

  function makeSkuFromName(name, suffix) {
    const clean = slugifyVi(name || "MMESTLINE")
      .split("-")
      .filter(Boolean)
      .slice(0, 4)
      .map((part) => part.slice(0, 4).toUpperCase())
      .join("-");

    return "MM-" + (clean || "ITEM") + "-" + (suffix || randomDigits(4));
  }

  function normalizeText(value, maxLength) {
    let text = String(value || "").trim().replace(/\s+/g, " ");

    if (maxLength) {
      text = text.slice(0, maxLength);
    }

    return text;
  }

  function debounce(fn, delay) {
    let timer = null;

    return function (...args) {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => fn.apply(this, args), delay);
    };
  }

  window.MMProductAdmin = {
    formatter,
    qs,
    qsa,
    onlyDigits,
    formatMoneyValue,
    parseMoney,
    moneyNumber,
    formatVnd,
    escapeHtml,
    slugifyVi,
    readJson,
    randomDigits,
    makeInternalBarcode,
    makeSkuFromName,
    normalizeText,
    debounce
  };
})();
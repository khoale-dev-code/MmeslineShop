(function () {
  "use strict";

  window.GUA = window.GUA || {};

  const modal = document.getElementById("addr-modal");
  const form = document.getElementById("addr-form");

  const els = {
    title: document.getElementById("modal-title"),
    addrId: document.getElementById("addr-id"),
    name: document.getElementById("inp-name"),
    phone: document.getElementById("inp-phone"),
    address: document.getElementById("inp-addr"),
    note: document.getElementById("inp-note"),
    isDefault: document.getElementById("chk-default"),

    province: document.getElementById("sel-prov"),
    district: document.getElementById("sel-dist"),
    ward: document.getElementById("sel-ward"),

    provinceCode: document.getElementById("hid-prov-code"),
    districtCode: document.getElementById("hid-dist-code"),
    wardCode: document.getElementById("hid-ward-code"),

    provinceName: document.getElementById("hid-prov"),
    districtName: document.getElementById("hid-dist"),
    wardName: document.getElementById("hid-ward"),

    provinceAlias: document.getElementById("hid-province-alias"),
    districtAlias: document.getElementById("hid-district-alias"),
    wardAlias: document.getElementById("hid-ward-alias"),

    btn: document.getElementById("btn-submit"),
    btnText: document.getElementById("btn-text"),
    btnSpin: document.getElementById("btn-spin")
  };

  function getOptionText(select) {
    if (!select) return "";
    const option = select.options[select.selectedIndex];
    return option ? option.textContent.trim() : "";
  }

  function getOptionValue(select) {
    return select ? String(select.value || "").trim() : "";
  }

  function syncLocationHiddenFields() {
    const provinceCode = getOptionValue(els.province);
    const districtCode = getOptionValue(els.district);
    const wardCode = getOptionValue(els.ward);

    const provinceName = getOptionText(els.province);
    const districtName = getOptionText(els.district);
    const wardName = getOptionText(els.ward);

    if (els.provinceCode) els.provinceCode.value = provinceCode;
    if (els.districtCode) els.districtCode.value = districtCode;
    if (els.wardCode) els.wardCode.value = wardCode;

    if (els.provinceName) els.provinceName.value = provinceName;
    if (els.districtName) els.districtName.value = districtName;
    if (els.wardName) els.wardName.value = wardName;

    if (els.provinceAlias) els.provinceAlias.value = provinceName;
    if (els.districtAlias) els.districtAlias.value = districtName;
    if (els.wardAlias) els.wardAlias.value = wardName;
  }

  function setSubmitting(isSubmitting) {
    if (!els.btn) return;

    els.btn.disabled = Boolean(isSubmitting);

    if (els.btnText) {
      els.btnText.textContent = isSubmitting ? "Đang lưu..." : "Lưu địa chỉ";
    }

    if (els.btnSpin) {
      els.btnSpin.classList.toggle("hidden", !isSubmitting);
    }
  }

  function resetForm() {
    if (!form) return;

    form.reset();
    form.action = "/profile/addresses/add";

    if (els.addrId) els.addrId.value = "";

    [
      els.provinceCode,
      els.districtCode,
      els.wardCode,
      els.provinceName,
      els.districtName,
      els.wardName,
      els.provinceAlias,
      els.districtAlias,
      els.wardAlias
    ].forEach((input) => {
      if (input) input.value = "";
    });

    setSubmitting(false);
  }

  function fillForm(addr) {
    if (!addr) return;

    if (els.addrId) els.addrId.value = addr.id || "";
    if (els.name) els.name.value = addr.full_name || "";
    if (els.phone) els.phone.value = addr.phone || "";
    if (els.address) els.address.value = addr.address_line || "";
    if (els.note) els.note.value = addr.note || "";
    if (els.isDefault) els.isDefault.checked = Boolean(addr.is_default);

    if (els.provinceName) els.provinceName.value = addr.province_name || addr.province || "";
    if (els.districtName) els.districtName.value = addr.district_name || addr.district || "";
    if (els.wardName) els.wardName.value = addr.ward_name || addr.ward || "";

    if (els.provinceAlias) els.provinceAlias.value = addr.province || addr.province_name || "";
    if (els.districtAlias) els.districtAlias.value = addr.district || addr.district_name || "";
    if (els.wardAlias) els.wardAlias.value = addr.ward || addr.ward_name || "";
  }

  function open(mode, id, addr) {
    if (!modal || !form) return;

    const isEdit = mode === "edit";

    resetForm();

    if (isEdit) {
      form.action = `/profile/addresses/edit/${id || addr?.id || ""}`;
      if (els.title) els.title.textContent = "Chỉnh sửa địa chỉ";
      if (els.btnText) els.btnText.textContent = "Cập nhật địa chỉ";
      fillForm(addr);
    } else {
      form.action = "/profile/addresses/add";
      if (els.title) els.title.textContent = "Thêm địa chỉ mới";
      if (els.btnText) els.btnText.textContent = "Lưu địa chỉ";
    }

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    setTimeout(() => {
      els.name?.focus();
    }, 120);
  }

  function close() {
    if (!modal) return;

    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function initFormSubmit() {
    if (!form) return;

    form.addEventListener("submit", function (event) {
      syncLocationHiddenFields();

      const required = [
        els.name,
        els.phone,
        els.address,
        els.province,
        els.district,
        els.ward
      ];

      const invalid = required.find((el) => !el || !String(el.value || "").trim());

      if (invalid) {
        event.preventDefault();
        invalid?.focus();

        if (window.showToast) {
          window.showToast("Vui lòng nhập đầy đủ thông tin địa chỉ.", "error");
        }

        return;
      }

      setSubmitting(true);
    });
  }

  els.province?.addEventListener("change", syncLocationHiddenFields);
  els.district?.addEventListener("change", syncLocationHiddenFields);
  els.ward?.addEventListener("change", syncLocationHiddenFields);

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      close();
    }
  });

  window.GUA.modal = {
    open,
    close,
    syncLocationHiddenFields
  };

  initFormSubmit();
})();
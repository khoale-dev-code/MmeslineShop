(() => {
  "use strict";

  const selectionForm = document.querySelector("[data-newsletter-selection]");

  if (selectionForm) {
    const pageToggle = selectionForm.querySelector("[data-select-page]");
    const checkboxes = Array.from(selectionForm.querySelectorAll("[data-select-subscriber]"));
    const bar = selectionForm.querySelector("[data-selection-bar]");
    const count = selectionForm.querySelector("[data-selection-count]");

    const syncSelection = () => {
      const selected = checkboxes.filter((item) => item.checked).length;
      if (count) count.textContent = String(selected);
      if (bar) bar.hidden = selected === 0;
      if (pageToggle) {
        pageToggle.checked = selected > 0 && selected === checkboxes.length;
        pageToggle.indeterminate = selected > 0 && selected < checkboxes.length;
      }
    };

    pageToggle?.addEventListener("change", () => {
      checkboxes.forEach((item) => {
        item.checked = pageToggle.checked;
      });
      syncSelection();
    });
    checkboxes.forEach((item) => item.addEventListener("change", syncSelection));
    syncSelection();
  }

  const runner = document.querySelector("[data-campaign-runner]");
  if (!runner) return;

  const startButton = runner.querySelector("[data-start-campaign]");
  const pauseButton = runner.querySelector("[data-pause-campaign]");
  const message = runner.querySelector("[data-run-message]");
  const csrf = runner.querySelector("[data-csrf-token]")?.value || "";
  const sendUrl = runner.dataset.sendUrl || "";
  let running = false;
  let pauseRequested = false;

  const setMessage = (text, tone = "info") => {
    if (!message) return;
    message.dataset.tone = tone;
    const target = message.querySelector("span");
    if (target) target.textContent = text;
  };

  const setText = (selector, value) => {
    const node = runner.querySelector(selector);
    if (node) node.textContent = String(value);
  };

  const updateCampaign = (payload) => {
    const campaign = payload.campaign;
    if (!campaign) return;
    setText("[data-count-pending]", campaign.pending_count);
    setText("[data-count-processing]", campaign.processing_count);
    setText("[data-count-sent]", campaign.sent_count);
    setText("[data-count-failed]", campaign.failed_count);
    setText("[data-count-skipped]", campaign.skipped_count);
    setText("[data-campaign-sent]", campaign.sent_count);
    setText("[data-campaign-percent]", `${campaign.progress_percent}%`);
    setText("[data-progress-title]", `${campaign.sent_count} / ${campaign.target_count} email thành công`);
    setText("[data-daily-sent]", payload.quota?.daily_sent ?? 0);
    const bar = runner.querySelector("[data-campaign-progress]");
    if (bar) bar.style.width = `${campaign.progress_percent}%`;
    runner.dataset.campaignStatus = campaign.status;
  };

  const finishRun = (label, tone = "info") => {
    running = false;
    pauseRequested = false;
    if (startButton) {
      startButton.disabled = false;
      const labelNode = startButton.querySelector("span");
      if (labelNode) labelNode.textContent = "Tiếp tục gửi";
    }
    if (pauseButton) pauseButton.hidden = true;
    setMessage(label, tone);
  };

  const sendNextBatch = async () => {
    if (!running || pauseRequested) {
      finishRun("Đã dừng sau lô hiện tại. Bạn có thể tiếp tục bất kỳ lúc nào.");
      return;
    }

    try {
      const response = await fetch(sendUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "X-CSRFToken": csrf,
          "X-CSRF-Token": csrf,
        },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        throw new Error(payload.message || "Không thể gửi lô email này.");
      }

      updateCampaign(payload);
      const batch = payload.batch || {};
      setMessage(
        `Lô gần nhất: ${batch.sent || 0} thành công, ${batch.failed || 0} lỗi. Đang chuẩn bị lô tiếp theo…`,
        batch.failed ? "warning" : "success",
      );

      if (payload.stop_reason === "daily_limit") {
        finishRun("Đã chạm hạn mức gửi trong 24 giờ. Chiến dịch được tạm dừng an toàn.", "warning");
        return;
      }
      if (payload.stop_reason === "completed" || payload.campaign?.status === "completed") {
        finishRun("Chiến dịch đã xử lý xong toàn bộ người nhận.", "success");
        window.setTimeout(() => window.location.reload(), 900);
        return;
      }
      if (payload.stop_reason === "no_pending") {
        finishRun("Không còn email nào trong hàng chờ.");
        return;
      }

      window.setTimeout(sendNextBatch, 450);
    } catch (error) {
      finishRun(error instanceof Error ? error.message : "Đã có lỗi khi gửi email.", "error");
    }
  };

  startButton?.addEventListener("click", () => {
    if (running) return;
    const confirmed = window.confirm(
      "Xác nhận bắt đầu gửi cho danh sách của chiến dịch? Hệ thống sẽ gửi từng email riêng và tự bỏ qua khách đã hủy nhận tin.",
    );
    if (!confirmed) return;
    running = true;
    pauseRequested = false;
    startButton.disabled = true;
    const label = startButton.querySelector("span");
    if (label) label.textContent = "Đang gửi…";
    if (pauseButton) pauseButton.hidden = false;
    setMessage("Đang xác nhận hạn mức và lấy lô người nhận đầu tiên…");
    sendNextBatch();
  });

  pauseButton?.addEventListener("click", () => {
    pauseRequested = true;
    pauseButton.disabled = true;
    setMessage("Đã yêu cầu dừng. Lô đang gửi sẽ được hoàn tất trước.");
  });
})();

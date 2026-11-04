function normalize(value) {
  return String(value || "")
    .replace(/\s+/g, "")
    .replace(/[‐-‒–—―ー－]/g, "-")
    .toLowerCase();
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function visible(element) {
  if (!element || element.hidden || element.type === "hidden") return false;
  const style = window.getComputedStyle(element);
  if (style.display === "none" || style.visibility === "hidden") return false;
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function fillableElement(element) {
  return Boolean(element && visible(element) && !element.disabled && !element.readOnly);
}

function choiceElementAvailable(element) {
  if (!element || (element.type !== "radio" && element.type !== "checkbox")) return false;
  if (element.disabled) return false;
  const label = element.closest("label");
  return visible(element) || visible(label);
}

function eventInput(element) {
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
  element.dispatchEvent(new Event("blur", { bubbles: true }));
}

function byId(id) {
  return id ? document.getElementById(id) : null;
}

function byName(name) {
  if (!name) return [];
  return Array.from(document.querySelectorAll(`[name="${cssEscape(name)}"]`));
}

function isRasensOfferFormPage() {
  // RASENSの生成ID(select_256097 等)はシステム更新で振り直されるため使わない。
  // 申請フォームは form#frm の中に item[N] 形式のnameを持つselectが並ぶ構造で判定する。
  return Boolean(document.querySelector("form#frm select[name^='item[']"));
}

function rowContainer(element) {
  return element?.closest("dl, tr, .c-input, .form-group, fieldset, section, div") || null;
}

function textForControl(element) {
  const id = element.id;
  const label = id ? document.querySelector(`label[for="${cssEscape(id)}"]`) : null;
  const row = rowContainer(element);
  return `${label?.innerText || ""} ${row?.innerText || ""} ${element.value || ""}`;
}

function choiceTextForControl(element) {
  const id = element.id;
  const label = id ? document.querySelector(`label[for="${cssEscape(id)}"]`) : null;
  const wrappedLabel = element.closest("label");
  return `${label?.innerText || ""} ${wrappedLabel?.innerText || ""} ${element.value || ""}`;
}

function findByLabel(row, selector = "input[name], input[id], select[name], select[id], textarea[name], textarea[id]", expectedType = "") {
  const wanted = normalize(row.label);
  if (!wanted) return null;

  const controls = Array.from(document.querySelectorAll(selector))
    .filter((element) => usableElement(element, expectedType) && expectedElementMatches(element, expectedType));
  const scored = controls
    .map((element) => {
      const text = normalize(textForControl(element));
      if (!text) return null;
      if (text.includes(wanted) || wanted.includes(text.slice(0, 20))) return { element, score: text.includes(wanted) ? 2 : 1 };
      return null;
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score);

  return scored[0]?.element || null;
}

function chooseSelect(select, rawValue) {
  if (!select?.options) return false;
  const wanted = normalize(rawValue);
  const options = Array.from(select.options);
  const textExact = options.find((option) => normalize(option.textContent) === wanted);
  const partial = options.find((option) => {
    const text = normalize(option.textContent);
    return text.includes(wanted) || wanted.includes(text);
  });
  const valueExact = options.find((option) => normalize(option.value) === wanted);
  const option = textExact || partial || valueExact;
  if (!option) return false;
  select.value = option.value;
  eventInput(select);
  return true;
}

function chooseRadioOrCheckbox(elements, rawValue) {
  const wanted = normalize(rawValue);
  const candidates = elements.filter(choiceElementAvailable);
  const target = candidates.find((element) => {
    if (["true", "1", "checked", "確認済み"].includes(wanted) && element.type === "checkbox") return true;
    const text = normalize(choiceTextForControl(element));
    return normalize(element.value) === wanted || text.includes(wanted) || wanted.includes(text);
  });

  if (!target) return false;
  if (target.type === "checkbox") {
    target.checked = true;
  } else {
    const label = target.closest("label");
    if (visible(target)) {
      target.click();
    } else if (visible(label)) {
      label.click();
    } else {
      target.click();
    }
  }
  eventInput(target);
  return true;
}

function fillText(element, value) {
  element.focus();
  element.value = value;
  eventInput(element);
  return true;
}

function expectedElementMatches(element, expectedType) {
  if (!element) return false;
  if (!expectedType) return true;
  if (expectedType === "select") return element.tagName === "SELECT";
  if (expectedType === "radio" || expectedType === "checkbox") return element.type === expectedType;
  if (expectedType === "file") return element.type === "file";
  if (expectedType === "textarea") return element.tagName === "TEXTAREA";
  if (["text", "date", "number", "month"].includes(expectedType)) {
    if (element.tagName === "TEXTAREA") return true;
    if (element.tagName !== "INPUT") return false;
    return !["radio", "checkbox", "file", "hidden"].includes(element.type);
  }
  return false;
}

function usableElement(element, expectedType) {
  if (expectedType === "radio" || expectedType === "checkbox") {
    return choiceElementAvailable(element);
  }
  return fillableElement(element);
}

function matchingElements(elements, expectedType) {
  return elements.filter((element) => usableElement(element, expectedType) && expectedElementMatches(element, expectedType));
}

function requiresStrictIdentity(row, options) {
  return options.allowLabelFallback === false && Boolean(row.field_id) && Boolean(row.field_name);
}

function targetForRow(row, options = {}) {
  const expectedType = (row.input_type || "").toLowerCase();
  const idElement = byId(row.field_id);
  const named = matchingElements(byName(row.field_name), expectedType);
  const idCandidate = usableElement(idElement, expectedType) && expectedElementMatches(idElement, expectedType) ? idElement : null;
  const allowLabelFallback = options.allowLabelFallback !== false;

  if (requiresStrictIdentity(row, options)) {
    return idCandidate && idCandidate.name === row.field_name ? idCandidate : null;
  }

  if (expectedType === "select") {
    return (
      named.find((element) => element.tagName === "SELECT") ||
      idCandidate ||
      (allowLabelFallback ? findByLabel(row, "select[name], select[id]", expectedType) : null)
    );
  }

  return idCandidate || named[0] || (allowLabelFallback ? findByLabel(row, undefined, expectedType) : null);
}

function fillRow(row, options = {}) {
  const value = (row.fill_value || row.display_value || "").trim();
  if (!value || row.input_type === "file") return { status: "skipped", reason: "empty-or-file" };

  const expectedType = (row.input_type || "").toLowerCase();
  const idElement = byId(row.field_id);
  const namedRaw = byName(row.field_name);
  const named = matchingElements(namedRaw, expectedType);

  if (expectedType === "select") {
    const select = targetForRow(row, options);

    if (!select) {
      if (requiresStrictIdentity(row, options)) {
        if (idElement && idElement.name === row.field_name && expectedElementMatches(idElement, expectedType)) {
          return { status: "skipped", reason: "not-visible-or-disabled" };
        }
        return { status: "missed", reason: "strict-target-mismatch" };
      }
      return { status: "missed", reason: "select-not-found" };
    }
    return chooseSelect(select, value) ? { status: "filled" } : { status: "missed", reason: "option-not-found" };
  }

  const primary = targetForRow(row, options);
  const elements = (named.length ? named : primary ? [primary] : []).filter(Boolean);

  if (requiresStrictIdentity(row, options) && !primary) {
    if (idElement && idElement.name === row.field_name && expectedElementMatches(idElement, expectedType)) {
      return { status: "skipped", reason: "not-visible-or-disabled" };
    }
    return { status: "missed", reason: "strict-target-mismatch" };
  }

  if (!primary && !elements.length) {
    if (namedRaw.length) return { status: "skipped", reason: "not-visible-or-disabled" };
    return { status: "missed", reason: "element-not-found" };
  }

  const type = expectedType || primary?.tagName.toLowerCase() || "";
  if (type === "select" || primary?.tagName === "SELECT") {
    return chooseSelect(primary, value) ? { status: "filled" } : { status: "missed", reason: "option-not-found" };
  }

  if (type === "radio" || type === "checkbox" || primary?.type === "radio" || primary?.type === "checkbox") {
    return chooseRadioOrCheckbox(elements.length ? elements : [primary].filter(fillableElement), value)
      ? { status: "filled" }
      : { status: "missed", reason: "choice-not-found" };
  }

  if (primary?.tagName === "TEXTAREA" || primary?.tagName === "INPUT") {
    return fillText(primary, value) ? { status: "filled" } : { status: "missed", reason: "text-fill-failed" };
  }

  return { status: "missed", reason: "unsupported-element" };
}

function selectedOptionText() {
  return Array.from(document.querySelectorAll("select"))
    .filter(visible)
    .map((select) => select.options?.[select.selectedIndex]?.textContent || "")
    .join(" ");
}

function textBlocksNearTitle(labelText) {
  const wanted = normalize(labelText);
  const titles = Array.from(document.querySelectorAll("dt, th, label, .c-input__title"))
    .filter(visible)
    .filter((element) => normalize(element.innerText || element.textContent).includes(wanted));

  return titles.map((title) => {
    const next = title.nextElementSibling;
    const row = title.closest("dl, tr, .c-input, .form-group, fieldset, section, div");
    return `${next && visible(next) ? next.innerText || next.textContent || "" : ""} ${row && visible(row) ? row.innerText || row.textContent || "" : ""}`;
  });
}

function currentPageText() {
  return `${document.title || ""} ${document.body?.innerText || ""} ${selectedOptionText()}`;
}

function detectApplicationTypeFromText(text) {
  const normalizedText = normalize(text);
  if (normalizedText.includes(normalize("在留資格認定証明書交付申請"))) return "certificate_of_eligibility";
  if (normalizedText.includes(normalize("在留資格変更許可申請"))) return "change_of_status";
  if (normalizedText.includes(normalize("在留期間更新許可申請"))) return "extension_of_stay";
  return "";
}

function detectApplicationType() {
  return detectApplicationTypeFromText(selectedOptionText()) || detectApplicationTypeFromText(currentPageText());
}

function detectTargetStatusFromText(text) {
  const normalizedText = normalize(text);
  if (normalizedText.includes(normalize("特定技能"))) return "specified_skilled_worker";
  if (
    normalizedText.includes(normalize("技術・人文知識・国際業務")) ||
    normalizedText.includes(normalize("技術・人文知識・国際"))
  ) {
    return "engineer_humanities_international";
  }
  return "";
}

function detectTargetStatus(formProfile) {
  const title = formProfile?.application_type === "extension_of_stay" ? "現在の在留資格" : "希望する在留資格";
  for (const text of textBlocksNearTitle(title)) {
    const detected = detectTargetStatusFromText(text);
    if (detected) return detected;
  }
  return "";
}

function profileMismatch(formProfile) {
  if (!formProfile) return "入力データの対象手続き情報がありません。visa-appからデータを再読み込みしてください";
  if (!formProfile.application_type || !formProfile.target_status) {
    return "入力データの対象手続き情報が不足しています。visa-appからデータを再読み込みしてください";
  }
  const currentApplicationType = detectApplicationType();
  const currentTargetStatus = detectTargetStatus(formProfile);

  if (formProfile.application_type && currentApplicationType && formProfile.application_type !== currentApplicationType) {
    return "開いているRASENS画面の手続きが、選択した案件と一致しません";
  }
  if (formProfile.target_status && currentTargetStatus && formProfile.target_status !== currentTargetStatus) {
    return "開いているRASENS画面の在留資格が、選択した案件と一致しません";
  }
  if (formProfile.application_type && !currentApplicationType) {
    return "開いているRASENS画面の手続きを確認できません";
  }
  if (formProfile.target_status && !currentTargetStatus) {
    return "開いているRASENS画面の在留資格を確認できません";
  }
  return "";
}

async function waitForRowTarget(row, options = {}, timeoutMs = 1200) {
  const startedAt = Date.now();
  let element = targetForRow(row, options);
  while (!element && Date.now() - startedAt < timeoutMs) {
    await sleep(100);
    element = targetForRow(row, options);
  }
  return element;
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function randomDelay(min, max) {
  return Math.floor(min + Math.random() * (max - min + 1));
}

function ensureAgentStyle() {
  if (document.getElementById("visa-autofill-agent-style")) return;

  const style = document.createElement("style");
  style.id = "visa-autofill-agent-style";
  style.textContent = `
    .visa-autofill-highlight-running {
      outline: 3px solid #2f6fed !important;
      outline-offset: 2px !important;
      box-shadow: 0 0 0 6px rgba(47, 111, 237, 0.18) !important;
      transition: outline-color 160ms ease, box-shadow 160ms ease !important;
    }
    .visa-autofill-highlight-filled {
      outline: 3px solid #1f9d55 !important;
      outline-offset: 2px !important;
      box-shadow: 0 0 0 6px rgba(31, 157, 85, 0.16) !important;
      transition: outline-color 160ms ease, box-shadow 160ms ease !important;
    }
    .visa-autofill-highlight-missed {
      outline: 3px solid #d94d2b !important;
      outline-offset: 2px !important;
      box-shadow: 0 0 0 6px rgba(217, 77, 43, 0.14) !important;
      transition: outline-color 160ms ease, box-shadow 160ms ease !important;
    }
    #visa-autofill-agent-panel {
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 2147483647;
      width: min(320px, calc(100vw - 36px));
      border: 1px solid #b8c2d6;
      border-radius: 8px;
      background: #ffffff;
      color: #172033;
      box-shadow: 0 12px 30px rgba(23, 32, 51, 0.18);
      font: 13px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      padding: 12px;
    }
    #visa-autofill-agent-panel strong {
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }
    #visa-autofill-agent-panel .visa-autofill-agent-label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #40506a;
    }
    #visa-autofill-agent-panel progress {
      width: 100%;
      height: 8px;
      margin-top: 8px;
      vertical-align: top;
    }
  `;
  document.documentElement.append(style);
}

function agentPanel() {
  ensureAgentStyle();
  let panel = document.getElementById("visa-autofill-agent-panel");
  if (panel) return panel;

  panel = document.createElement("div");
  panel.id = "visa-autofill-agent-panel";
  panel.innerHTML = `
    <strong>AI Agent入力中</strong>
    <div class="visa-autofill-agent-count"></div>
    <div class="visa-autofill-agent-label"></div>
    <progress value="0" max="1"></progress>
  `;
  document.documentElement.append(panel);
  return panel;
}

function updateAgentPanel({ current, total, label, done = false }) {
  const panel = agentPanel();
  panel.querySelector("strong").textContent = done ? "AI Agent入力完了" : "AI Agent入力中";
  panel.querySelector(".visa-autofill-agent-count").textContent = `${current} / ${total}`;
  panel.querySelector(".visa-autofill-agent-label").textContent = label || "";
  const progress = panel.querySelector("progress");
  progress.max = Math.max(total, 1);
  progress.value = Math.min(current, total);
}

function clearHighlight(element) {
  if (!element) return;
  element.classList.remove(
    "visa-autofill-highlight-running",
    "visa-autofill-highlight-filled",
    "visa-autofill-highlight-missed"
  );
}

function highlightElement(element, status) {
  if (!element) return;
  ensureAgentStyle();
  clearHighlight(element);
  element.classList.add(`visa-autofill-highlight-${status}`);
}

function maskedValue(value) {
  if (!value) return "";
  return `[masked:${String(value).length}]`;
}

function resultSummary(results) {
  const filled = results.filter(({ result }) => result.status === "filled").length;
  const skipped = results.filter(({ result }) => result.status === "skipped").length;
  const missed = results.filter(({ result }) => result.status === "missed");

  console.table(results.map(({ row, result }) => ({
    label: row.label,
    value: maskedValue(row.fill_value),
    status: result.status,
    reason: result.reason || ""
  })));

  return `入力完了: ${filled}件入力、${skipped}件スキップ、${missed.length}件未検出。詳細はDevTools consoleを確認してください。`;
}

async function fillRows(rows, options = {}) {
  const results = [];
  for (const row of rows) {
    try {
      await waitForRowTarget(row, options);
      const result = fillRow(row, options);
      results.push({ row, result });
      if (result.status === "filled") await sleep(120);
    } catch (error) {
      results.push({ row, result: { status: "missed", reason: error.message || "unexpected-error" } });
    }
  }
  return resultSummary(results);
}

async function fillRowsProgressively(rows, options = {}) {
  const results = [];
  let previousElement = null;

  for (const [index, row] of rows.entries()) {
    const current = index + 1;
    const element = await waitForRowTarget(row, options);
    clearHighlight(previousElement);
    previousElement = element;
    updateAgentPanel({ current, total: rows.length, label: row.label });

    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
      highlightElement(element, "running");
    }

    await sleep(randomDelay(350, 900));

    let result;
    try {
      result = fillRow(row, options);
    } catch (error) {
      result = { status: "missed", reason: error.message || "unexpected-error" };
    }

    results.push({ row, result });
    if (element) highlightElement(element, result.status === "filled" ? "filled" : "missed");
    await sleep(randomDelay(180, 420));
  }

  updateAgentPanel({ current: rows.length, total: rows.length, label: "完了", done: true });
  window.setTimeout(() => clearHighlight(previousElement), 1400);
  return resultSummary(results);
}

var VISA_AUTOFILL_CONTENT_VERSION = "0.4.1";

if (window.__visaAutofillContentHandler) {
  chrome.runtime.onMessage.removeListener(window.__visaAutofillContentHandler);
}

window.__visaAutofillContentInstalled = true;
window.__visaAutofillContentVersion = VISA_AUTOFILL_CONTENT_VERSION;
window.__visaAutofillContentHandler = (message, _sender, sendResponse) => {
  if (!isRasensOfferFormPage()) {
    sendResponse({ message: "在留申請オンラインシステムの申請フォーム画面で実行してください" });
    return true;
  }
  const mismatch = profileMismatch(message.formProfile);
  if (mismatch) {
    sendResponse({ message: `${mismatch}\nvisa-appの案件とRASENS画面を確認してください。入力は実行していません。` });
    return true;
  }
  const options = {
    allowLabelFallback: message.formProfile?.target_status !== "specified_skilled_worker",
  };
  if (message.type === "VISA_AUTOFILL_FILL") {
    fillRows(message.rows || [], options).then((messageText) => {
      sendResponse({ message: messageText });
    });
    return true;
  }
  if (message.type === "VISA_AUTOFILL_FILL_PROGRESSIVE") {
    fillRowsProgressively(message.rows || [], options).then((messageText) => {
      sendResponse({ message: messageText });
    });
    return true;
  }
  return false;
};

chrome.runtime.onMessage.addListener(window.__visaAutofillContentHandler);

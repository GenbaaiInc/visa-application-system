const elements = {
  statusBox: document.querySelector("#status"),
  statusFilter: document.querySelector("#statusFilter"),
  caseSelect: document.querySelector("#caseSelect"),
  caseListStatus: document.querySelector("#caseListStatus"),
  refreshCases: document.querySelector("#refreshCases"),
  loadFromApi: document.querySelector("#loadFromApi"),
  fill: document.querySelector("#fill"),
  fillProgressive: document.querySelector("#fillProgressive"),
  workflowWarning: document.querySelector("#workflowWarning"),
  workflowReady: document.querySelector("#workflowReady"),
  workflowState: document.querySelector("#wfState"),
  authSection: document.querySelector("#authSection"),
  appSection: document.querySelector("#appSection"),
  authEmail: document.querySelector("#authEmail"),
  authPassword: document.querySelector("#authPassword"),
  authStatus: document.querySelector("#authStatus"),
  signInButton: document.querySelector("#signInButton"),
  signInBrowserButton: document.querySelector("#signInBrowserButton"),
  signOutButton: document.querySelector("#signOutButton"),
  userEmail: document.querySelector("#userEmail"),
};
const RASENS_URL_PATTERNS = ["https://www.rasens-immi.moj.go.jp/*"];
let availableCases = [];

function setStatus(message) {
  elements.statusBox.textContent = message;
}

function setCaseListStatus(message) {
  elements.caseListStatus.textContent = message;
}

function setFillButtonsEnabled(enabled) {
  elements.fill.disabled = !enabled;
  elements.fillProgressive.disabled = !enabled;
}

function resetWorkflowBanners() {
  elements.workflowWarning.hidden = true;
  elements.workflowReady.hidden = true;
  elements.workflowState.textContent = "";
}

async function clearRows(message) {
  await chrome.storage.local.remove([
    "visaRows",
    "visaDataSource",
    "visaFillable",
    "visaFormProfile",
    "visaMissingRequiredFields",
    "visaPendingManualFields",
  ]);
  setFillButtonsEnabled(false);
  if (message) {
    setStatus(message);
  }
}

async function saveRows(rows, source, canFill = true, formProfile = null, missingRequiredFields = [], pendingManualFields = []) {
  const inputRows = rows.filter((row) => (row.fill_value || "").trim());
  await chrome.storage.local.set({
    visaRows: inputRows,
    visaDataSource: source,
    visaFillable: inputRows.length > 0 && Boolean(canFill),
    visaFormProfile: formProfile,
    visaMissingRequiredFields: missingRequiredFields,
    visaPendingManualFields: pendingManualFields,
  });
  setFillButtonsEnabled(inputRows.length > 0 && Boolean(canFill));
  setStatus(`${source}\n${inputRows.length}件の入力値を保存しました`);
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function isRasensTab(tab) {
  try {
    const url = new URL(tab?.url || "");
    return url.protocol === "https:" && url.hostname === "www.rasens-immi.moj.go.jp";
  } catch {
    return false;
  }
}

async function getRasensTab() {
  const activeTab = await getActiveTab();
  if (isRasensTab(activeTab)) return activeTab;

  const rasensTabs = await chrome.tabs.query({ url: RASENS_URL_PATTERNS });
  if (rasensTabs.length === 1) return rasensTabs[0];
  if (rasensTabs.length > 1) {
    throw new Error("RASENSタブが複数あります。入力したいRASENSタブをアクティブにしてから実行してください");
  }
  throw new Error("在留申請オンラインシステムのページを開いてから実行してください");
}

async function ensureContentScript(tab) {
  if (!tab?.id) throw new Error("アクティブなタブを取得できませんでした");
  if (!isRasensTab(tab)) {
    throw new Error("在留申請オンラインシステムのページで実行してください");
  }

  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content.js"]
  });
}

async function sendMessageOrThrow(tab, type, rows, formProfile) {
  const response = await chrome.tabs.sendMessage(tab.id, { type, rows, formProfile });
  if (!response?.message) {
    throw new Error("ページ側の入力スクリプトが古いか、応答が空です");
  }
  return response.message;
}

async function sendToTab(type) {
  const { visaRows, visaFillable, visaFormProfile, visaPendingManualFields } = await chrome.storage.local.get([
    "visaRows",
    "visaFillable",
    "visaFormProfile",
    "visaPendingManualFields",
  ]);
  if (!visaRows?.length) {
    setStatus("先にデータを読み込んでください");
    return;
  }
  if (!visaFillable) {
    setStatus("このケースはまだ入力可能状態ではありません。");
    return;
  }

  try {
    const tab = await getRasensTab();
    setStatus("ページへ接続しています...");
    await ensureContentScript(tab);
    const message = await sendMessageOrThrow(tab, type, visaRows, visaFormProfile);
    setStatus([message, formatManualFields(visaPendingManualFields)].filter(Boolean).join("\n"));
  } catch (error) {
    setStatus(`ページに接続できませんでした\n${error.message}`);
  }
}

const workflowStateLabel = {
  draft: "未抽出",
  extracting: "抽出中",
  extracted: "抽出済み",
  failed: "抽出失敗"
};

function toWorkflowDisplayState(workflowState) {
  if (workflowState === "extracting") return "extracting";
  if (workflowState === "needs_review" || workflowState === "ready_to_fill" || workflowState === "extracted") {
    return "extracted";
  }
  if (workflowState === "extraction_failed" || workflowState === "launch_failed" || workflowState === "failed") {
    return "failed";
  }
  return "draft";
}

function formatWorkflowState(workflowState) {
  if (!workflowState) {
    return "未抽出";
  }
  const displayState = toWorkflowDisplayState(workflowState);
  return workflowStateLabel[displayState] || workflowState;
}

const applicationTypeLabel = {
  certificate_of_eligibility: "認定・COE",
  change_of_status: "変更",
  extension_of_stay: "更新"
};

const targetStatusLabel = {
  engineer_humanities_international: "技人国",
  specified_skilled_worker: "特定技能"
};

const targetStatusVariantLabel = {
  ssw_1: "1号",
  ssw_2: "2号"
};

function formatProfile(formProfile) {
  if (!formProfile) return "";
  const applicationType = applicationTypeLabel[formProfile.application_type] || formProfile.application_type || "";
  const targetStatus = targetStatusLabel[formProfile.target_status] || formProfile.target_status || "";
  return [applicationType, targetStatus].filter(Boolean).join(" / ");
}

function formatMissingFields(fields) {
  if (!Array.isArray(fields) || !fields.length) return "";
  const lines = fields.slice(0, 5).map((field) => {
    const label = field.label || field.canonical_path || "未入力項目";
    return `- ${label}${field.reason ? `: ${field.reason}` : ""}`;
  });
  const rest = fields.length > lines.length ? `\nほか${fields.length - lines.length}件` : "";
  return `未入力の必須項目があります\n${lines.join("\n")}${rest}`;
}

function formatManualFields(fields) {
  if (!Array.isArray(fields) || !fields.length) return "";
  const lines = fields.slice(0, 5).map((field) => {
    const label = field.label || field.canonical_path || "手動確認項目";
    return `- ${label}${field.reason ? `: ${field.reason}` : ""}`;
  });
  const rest = fields.length > lines.length ? `\nほか${fields.length - lines.length}件` : "";
  return `該当する場合にRASENSで入力・確認する項目があります\n${lines.join("\n")}${rest}`;
}

function formatCaseOptionLabel(caseSummary) {
  const applicationType = applicationTypeLabel[caseSummary.application_type] || caseSummary.application_type || "";
  const targetStatus = targetStatusLabel[caseSummary.target_status] || caseSummary.target_status || "";
  const variant = caseSummary.target_status === "specified_skilled_worker"
    ? targetStatusVariantLabel[caseSummary.target_status_variant] || ""
    : "";
  const typeLabel = [applicationType === "認定・COE" ? "認定" : applicationType, `${targetStatus}${variant}`]
    .filter(Boolean).join("・");
  const displayName = caseSummary.display_name || caseSummary.case_id;
  const applicantName = caseSummary.applicant_name || "-";
  const employerName = caseSummary.employer_name || "-";
  const workflowState = formatWorkflowState(caseSummary.workflow_state);
  return `${typeLabel ? `[${typeLabel}] ` : ""}${displayName} | 申請人: ${applicantName} | 所属先: ${employerName} | 状態: ${workflowState}`;
}

function getCaseSummary(caseId) {
  return availableCases.find((caseSummary) => caseSummary.case_id === caseId) || null;
}

function renderCaseOptions(cases, selectedCaseId = "", placeholderText = "案件を選択してください") {
  elements.caseSelect.replaceChildren();

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = placeholderText;
  elements.caseSelect.appendChild(placeholder);

  for (const caseSummary of cases) {
    const option = document.createElement("option");
    option.value = caseSummary.case_id;
    option.textContent = formatCaseOptionLabel(caseSummary);
    elements.caseSelect.appendChild(option);
  }

  elements.caseSelect.value = cases.some((caseSummary) => caseSummary.case_id === selectedCaseId)
    ? selectedCaseId
    : "";
  elements.caseSelect.disabled = cases.length === 0;
}

function renderFilteredCases(selectedCaseId = elements.caseSelect.value) {
  const status = elements.statusFilter.value;
  const filteredCases = status
    ? availableCases.filter((caseSummary) => caseSummary.target_status === status)
    : availableCases;
  renderCaseOptions(
    filteredCases,
    selectedCaseId,
    availableCases.length ? "案件を選択してください" : "案件がありません"
  );
  setCaseListStatus(
    status ? `${filteredCases.length}件を表示（全${availableCases.length}件）` : `${availableCases.length}件の案件を取得しました`
  );
}

async function loadCases() {
  const { visaSelectedCaseId = "" } = await chrome.storage.local.get(["visaSelectedCaseId"]);

  elements.refreshCases.disabled = true;
  elements.caseSelect.disabled = true;
  setCaseListStatus("案件一覧を取得中...");

  try {
    const cases = await window.apiClient.listCases();
    availableCases = Array.isArray(cases)
      ? cases.filter((caseSummary) => caseSummary?.case_id)
      : [];

    if (availableCases.length) {
      renderFilteredCases(visaSelectedCaseId);
    } else {
      renderCaseOptions([], "", "案件がありません");
      setCaseListStatus("案件がありません");
    }
  } catch (error) {
    availableCases = [];
    renderCaseOptions([], "", "案件一覧を取得できませんでした");
    setCaseListStatus(`案件一覧の取得に失敗しました: ${error.message}`);
  } finally {
    elements.refreshCases.disabled = false;
  }
}

function getRequestedCase() {
  const selectedCaseId = elements.caseSelect.value.trim();
  if (selectedCaseId) {
    return { caseId: selectedCaseId, caseSummary: getCaseSummary(selectedCaseId) };
  }
  return null;
}

function getCaseSourceLabel(caseId, caseSummary) {
  const displayName = caseSummary?.display_name?.trim();
  if (displayName) {
    return `visa-app: ${displayName} (${caseId})`;
  }
  return `visa-app: ${caseId}`;
}

async function showSection(auth) {
  elements.authSection.hidden = Boolean(auth);
  elements.appSection.hidden = !auth;
  elements.userEmail.textContent = auth?.email || "";
}

elements.signInButton.addEventListener("click", async () => {
  elements.signInButton.disabled = true;
  elements.authStatus.textContent = "ログイン中...";
  try {
    await window.apiClient.signIn(elements.authEmail.value.trim(), elements.authPassword.value);
    elements.authPassword.value = "";
    await showSection(await window.apiClient.getAuthState());
    await loadCases();
  } catch (error) {
    elements.authStatus.textContent = error.message;
  } finally {
    elements.signInButton.disabled = false;
  }
});

elements.signInBrowserButton.addEventListener("click", async () => {
  elements.signInBrowserButton.disabled = true;
  elements.authStatus.textContent = "ブラウザでログイン中...";
  try {
    await window.apiClient.signInWithBrowser();
    elements.authStatus.textContent = "visa-appのアカウントでログインしてください";
    await showSection(await window.apiClient.getAuthState());
    await loadCases();
  } catch (error) {
    elements.authStatus.textContent = error.message;
  } finally {
    elements.signInBrowserButton.disabled = false;
  }
});

elements.signOutButton.addEventListener("click", async () => {
  await window.apiClient.signOut();
  await clearRows();
  elements.authStatus.textContent = "visa-appのアカウントでログインしてください";
  await showSection(null);
});

elements.fill.addEventListener("click", () => sendToTab("VISA_AUTOFILL_FILL"));
elements.fillProgressive.addEventListener("click", () => sendToTab("VISA_AUTOFILL_FILL_PROGRESSIVE"));

elements.caseSelect.addEventListener("change", async () => {
  const selectedCaseId = elements.caseSelect.value.trim();
  await chrome.storage.local.set({ visaSelectedCaseId: selectedCaseId });
});

elements.statusFilter.addEventListener("change", () => {
  renderFilteredCases();
});

elements.refreshCases.addEventListener("click", () => {
  loadCases();
});

elements.loadFromApi.addEventListener("click", async () => {
  const requestedCase = getRequestedCase();
  if (!requestedCase) {
    setStatus("案件一覧から選択してください");
    return;
  }

  resetWorkflowBanners();

  try {
    setStatus("visa-app から取得中...");
    const applicationData = await window.apiClient.getApplicationData(requestedCase.caseId);

    const workflowState = applicationData.workflow_state;
    const displayState = toWorkflowDisplayState(workflowState);
    elements.workflowState.textContent = workflowStateLabel[displayState];
    if (applicationData.fillable) {
      elements.workflowReady.hidden = false;
    } else {
      elements.workflowWarning.hidden = false;
    }

    const rows = applicationData.rows || [];
    if (!rows.length) {
      await clearRows("入力対象の値がありません。visa-app のレビュー内容を確認してください。");
      return;
    }

    const sourceLabel = getCaseSourceLabel(requestedCase.caseId, requestedCase.caseSummary);
    const warningText = (applicationData.warnings || []).join("\n");
    const profileText = formatProfile(applicationData.form_profile);
    const missingText = formatMissingFields(applicationData.missing_required_fields);
    const manualText = formatManualFields(applicationData.pending_manual_fields);
    await saveRows(
      rows,
      sourceLabel,
      applicationData.fillable,
      applicationData.form_profile || null,
      applicationData.missing_required_fields || [],
      applicationData.pending_manual_fields || []
    );
    await chrome.storage.local.set({ visaSelectedCaseId: requestedCase.caseSummary ? requestedCase.caseId : "" });

    const messages = [
      `${sourceLabel}\n${rows.length}件の入力値を保存しました`,
      profileText ? `対象: ${profileText}` : "",
      missingText,
      manualText,
      warningText,
    ].filter(Boolean);
    if (messages.length) {
      setStatus(messages.join("\n"));
    }
  } catch (error) {
    await clearRows(`読込エラー\n${error.message}`);
  }
});

async function initializePopup() {
  const auth = await window.apiClient.getAuthState();
  await showSection(auth);
  if (!auth) return;

  const {
    visaRows,
    visaDataSource,
    visaFillable,
    visaFormProfile,
    visaMissingRequiredFields,
    visaPendingManualFields,
  } = await chrome.storage.local.get([
    "visaRows",
    "visaDataSource",
    "visaFillable",
    "visaFormProfile",
    "visaMissingRequiredFields",
    "visaPendingManualFields",
  ]);

  if (visaRows?.length) {
    setFillButtonsEnabled(Boolean(visaFillable));
    const profileText = formatProfile(visaFormProfile);
    const missingText = formatMissingFields(visaMissingRequiredFields);
    const manualText = formatManualFields(visaPendingManualFields);
    setStatus([
      `${visaDataSource || "保存済みデータ"}\n${visaRows.length}件の入力値が保存されています`,
      profileText ? `対象: ${profileText}` : "",
      missingText,
      manualText,
    ].filter(Boolean).join("\n"));
  } else {
    setFillButtonsEnabled(false);
  }

  await loadCases();
}

initializePopup();

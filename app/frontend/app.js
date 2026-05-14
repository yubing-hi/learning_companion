const STORAGE_KEYS = {
  studentId: "la_student_id",
  chatHistory: "la_chat_history",
  currentExercise: "la_current_exercise",
  currentPlan: "la_current_plan",
};

const state = {
  studentId: "",
  profile: null,
  chatHistory: [],
  currentExercise: null,
  currentPlan: null,
};

document.addEventListener("DOMContentLoaded", () => {
  hydrateState();
  bindCommonControls();
  renderGlobalState();
  initializePage();
  checkHealth();
  loadProfileSilently();
});

function hydrateState() {
  state.studentId = localStorage.getItem(STORAGE_KEYS.studentId) || "";
  state.chatHistory = readJson(STORAGE_KEYS.chatHistory, []);
  state.currentExercise = readJson(STORAGE_KEYS.currentExercise, null);
  state.currentPlan = readJson(STORAGE_KEYS.currentPlan, null);
}

function bindCommonControls() {
  document.querySelectorAll("[data-student-input]").forEach((input) => {
    input.value = state.studentId;
  });

  document.querySelectorAll('[data-form="student-switch"]').forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const studentId = new FormData(form).get("student_id")?.toString().trim() || "";
      if (!studentId) {
        showToast("请先输入学生 ID。");
        return;
      }
      setStudentId(studentId);
      showToast("当前学生已切换。");
      loadProfileSilently();
    });
  });

  document.querySelectorAll('[data-action="load-profile"]').forEach((button) => {
    button.addEventListener("click", async () => {
      if (!ensureStudent()) return;
      await loadProfile();
    });
  });
}

function initializePage() {
  const page = document.body.dataset.page;
  if (page === "dashboard") initDashboardPage();
  if (page === "chat") initChatPage();
  if (page === "practice") initPracticePage();
  if (page === "plan") initPlanPage();
  if (page === "profile") initProfilePage();
}

function initDashboardPage() {
  document.querySelector('[data-form="profile-init"]')?.addEventListener("submit", handleInitProfile);
  renderDashboardProfileSummary();
}

function initChatPage() {
  const form = document.querySelector('[data-form="chat"]');
  const input = document.querySelector("[data-chat-input]");

  form?.addEventListener("submit", handleChatSubmit);
  document.querySelectorAll("[data-chat-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      if (input) input.value = button.dataset.chatPrompt || "";
      input?.focus();
    });
  });

  document.querySelector('[data-action="clear-chat"]')?.addEventListener("click", () => {
    state.chatHistory = [];
    localStorage.setItem(STORAGE_KEYS.chatHistory, JSON.stringify(state.chatHistory));
    renderChatTimeline();
    showToast("对话记录已清空。");
  });

  renderChatTimeline();
}

function initPracticePage() {
  document.querySelector('[data-form="exercise-generate"]')?.addEventListener("submit", handleGenerateExercise);
  renderPracticeHints();
  renderExercisePanel();
}

function initPlanPage() {
  document.querySelectorAll("[data-plan-duration]").forEach((button) => {
    button.addEventListener("click", () => handleGeneratePlan(button.dataset.planDuration || "3天"));
  });
  renderPlanFocusSummary();
  renderPlanPanel();
}

function initProfilePage() {
  document.querySelector('[data-form="profile-init"]')?.addEventListener("submit", handleInitProfile);
  renderProfilePanel();
}

async function checkHealth() {
  if (!isServedOverHttp()) {
    updateHealthDisplay("offline", "请通过启动脚本打开");
    return;
  }

  updateHealthDisplay("connecting", "正在连接后端");
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    updateHealthDisplay(data.status === "ok" ? "online" : "offline", data.status === "ok" ? "后端在线" : "服务异常");
  } catch (error) {
    updateHealthDisplay("offline", "后端未连接");
  }
}

function updateHealthDisplay(status, label) {
  document.querySelectorAll("[data-health-label]").forEach((node) => {
    node.textContent = label;
  });
  document.querySelectorAll("[data-health-dot]").forEach((node) => {
    node.classList.toggle("is-online", status === "online");
  });
}

function renderGlobalState() {
  document.querySelectorAll("[data-active-student]").forEach((node) => {
    node.textContent = state.studentId || "未绑定";
  });
  document.querySelectorAll("[data-student-input]").forEach((input) => {
    if (document.activeElement !== input) {
      input.value = state.studentId;
    }
  });
}

function setStudentId(studentId) {
  state.studentId = studentId;
  localStorage.setItem(STORAGE_KEYS.studentId, studentId);
  renderGlobalState();
}

async function handleInitProfile(event) {
  event.preventDefault();
  if (!ensureAppServed()) return;

  const form = event.currentTarget;
  const payload = {
    student_id: readFormValue(form, "student_id"),
    target: readFormValue(form, "target"),
    available_time: readFormValue(form, "available_time"),
  };

  if (!payload.student_id || !payload.target || !payload.available_time) {
    showToast("请把学生 ID、学习目标和可投入时间填写完整。");
    return;
  }

  try {
    const profile = await apiRequest("/profile/init", {
      method: "POST",
      body: payload,
    });
    setStudentId(payload.student_id);
    state.profile = profile;
    renderAllProfileViews();
    showToast("学生画像初始化成功。");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadProfile() {
  if (!ensureAppServed()) return;

  try {
    state.profile = await apiRequest(`/profile/${encodeURIComponent(state.studentId)}`);
    renderAllProfileViews();
    showToast("学生画像读取成功。");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadProfileSilently() {
  if (!state.studentId) {
    renderAllProfileViews();
    return;
  }
  if (!isServedOverHttp()) {
    state.profile = null;
    renderAllProfileViews();
    return;
  }

  try {
    state.profile = await apiRequest(`/profile/${encodeURIComponent(state.studentId)}`);
    renderAllProfileViews();
  } catch (error) {
    state.profile = null;
    renderAllProfileViews();
  }
}

async function handleChatSubmit(event) {
  event.preventDefault();
  if (!ensureAppServed()) return;
  if (!ensureStudent()) return;

  const form = event.currentTarget;
  const message = readFormValue(form, "message");
  if (!message) {
    showToast("请输入问题内容。");
    return;
  }

  pushChatMessage({
    role: "user",
    text: message,
    time: new Date().toLocaleString("zh-CN"),
  });
  form.reset();

  try {
    const response = await apiRequest("/chat", {
      method: "POST",
      body: {
        student_id: state.studentId,
        message,
      },
    });
    pushChatMessage({
      role: "assistant",
      text: response.data?.answer || "本次没有返回回答。",
      time: new Date().toLocaleString("zh-CN"),
      sources: response.data?.sources || [],
      points: response.data?.knowledge_points || [],
    });
    await loadProfileSilently();
  } catch (error) {
    pushChatMessage({
      role: "assistant",
      text: `请求失败：${error.message}`,
      time: new Date().toLocaleString("zh-CN"),
    });
    showToast(error.message);
  }
}

function pushChatMessage(message) {
  state.chatHistory.push(message);
  state.chatHistory = state.chatHistory.slice(-20);
  localStorage.setItem(STORAGE_KEYS.chatHistory, JSON.stringify(state.chatHistory));
  renderChatTimeline();
}

function renderChatTimeline() {
  const panel = document.getElementById("chatTimeline");
  if (!panel) return;

  if (!state.chatHistory.length) {
    panel.innerHTML = `
      <div class="empty-panel">
        <p>还没有对话。你可以从左侧选择提示问题，或者直接输入新的问题。</p>
      </div>
    `;
    return;
  }

  panel.innerHTML = state.chatHistory.map((item) => `
    <article class="message message--${item.role}">
      <div class="message__role">${item.role === "user" ? "学生" : "AI"}</div>
      <div>
        <div class="message__meta">${item.role === "user" ? "学生提问" : "学伴回复"} · ${escapeHtml(item.time || "")}</div>
        <div class="message__text">${escapeHtml(item.text || "")}</div>
        ${renderTagRow(item.points, item.sources)}
      </div>
    </article>
  `).join("");
  panel.scrollTop = panel.scrollHeight;
}

async function handleGenerateExercise(event) {
  event.preventDefault();
  if (!ensureAppServed()) return;
  if (!ensureStudent()) return;

  const form = event.currentTarget;
  const payload = {
    student_id: state.studentId,
    knowledge_point: readFormValue(form, "knowledge_point"),
    question_type: readFormValue(form, "question_type") || "choice",
    difficulty: readFormValue(form, "difficulty") || "easy",
    count: 1,
  };

  if (!payload.knowledge_point) {
    showToast("请先填写知识点。");
    return;
  }

  try {
    const response = await apiRequest("/exercise/generate", {
      method: "POST",
      body: payload,
    });
    const item = response.data?.items?.[0];
    if (!item) {
      throw new Error("本次没有生成有效题目。");
    }
    state.currentExercise = item;
    localStorage.setItem(STORAGE_KEYS.currentExercise, JSON.stringify(item));
    renderExercisePanel();
    await loadProfileSilently();
    showToast("练习题已生成。");
  } catch (error) {
    showToast(error.message);
  }
}

function renderExercisePanel() {
  const panel = document.getElementById("exercisePanel");
  if (!panel) return;

  const item = state.currentExercise;
  if (!item) {
    panel.className = "empty-panel";
    panel.innerHTML = "<p>还没有练习题，先在左侧生成一题。</p>";
    return;
  }

  const optionHtml = item.question_type === "choice"
    ? `
      <div class="option-list">
        ${(item.options || []).map((option, index) => {
          const label = String.fromCharCode(65 + index);
          const optionText = stripChoicePrefix(option);
          return `
            <label class="option-item">
              <input type="radio" name="exerciseOption" value="${label}">
              <span><strong>${label}.</strong> ${escapeHtml(optionText)}</span>
            </label>
          `;
        }).join("")}
      </div>
    `
    : `
      <label class="field">
        <span>你的答案</span>
        <textarea id="exerciseAnswer" rows="7" placeholder="请输入你的作答内容"></textarea>
      </label>
    `;

  panel.className = "";
  panel.innerHTML = `
    <div class="question-card">
      <div class="question-meta">
        <span class="tag">${escapeHtml(item.knowledge_point)}</span>
        <span class="tag">${escapeHtml(item.question_type)}</span>
        <span class="tag">${escapeHtml(item.difficulty)}</span>
      </div>
      <h3>${escapeHtml(item.question)}</h3>
      ${optionHtml}
      <div class="inline-actions" style="margin-top: 16px;">
        <button class="button button--primary" type="button" id="submitExerciseBtn">提交答案</button>
      </div>
      <div id="evaluationPanel"></div>
    </div>
  `;
  document.getElementById("submitExerciseBtn")?.addEventListener("click", handleEvaluateExercise);
}

async function handleEvaluateExercise() {
  if (!ensureAppServed()) return;
  if (!ensureStudent() || !state.currentExercise) return;

  let studentAnswer = "";
  if (state.currentExercise.question_type === "choice") {
    const checked = document.querySelector('input[name="exerciseOption"]:checked');
    if (!checked) {
      showToast("请先选择一个选项。");
      return;
    }
    studentAnswer = checked.value;
  } else {
    studentAnswer = document.getElementById("exerciseAnswer")?.value.trim() || "";
    if (!studentAnswer) {
      showToast("请先输入你的答案。");
      return;
    }
  }

  try {
    const response = await apiRequest("/exercise/evaluate", {
      method: "POST",
      body: {
        student_id: state.studentId,
        question_id: state.currentExercise.question_id,
        student_answer: studentAnswer,
      },
    });
    renderEvaluation(response.data);
    await loadProfileSilently();
    showToast("答案评估完成。");
  } catch (error) {
    showToast(error.message);
  }
}

function renderEvaluation(result) {
  const panel = document.getElementById("evaluationPanel");
  if (!panel || !result) return;
  panel.innerHTML = `
    <div class="evaluation-card" style="margin-top: 16px;">
      <div class="score-strip">
        <span class="tag">${result.correct ? "回答正确" : "需要改进"}</span>
        <span class="tag">得分 ${Math.round(Number(result.score || 0) * 100)}%</span>
        ${result.error_type ? `<span class="tag">${escapeHtml(result.error_type)}</span>` : ""}
      </div>
      <div class="detail-list" style="margin-top: 14px;">
        <div><strong>反馈：</strong>${escapeHtml(result.feedback || "-")}</div>
        <div><strong>建议：</strong>${escapeHtml(result.suggestion || "-")}</div>
      </div>
    </div>
  `;
}

async function handleGeneratePlan(duration) {
  if (!ensureAppServed()) return;
  if (!ensureStudent()) return;

  try {
    const response = await apiRequest("/plan/generate", {
      method: "POST",
      body: {
        student_id: state.studentId,
        duration,
      },
    });
    state.currentPlan = response.data || null;
    localStorage.setItem(STORAGE_KEYS.currentPlan, JSON.stringify(state.currentPlan));
    renderPlanPanel();
    await loadProfileSilently();
    showToast("学习计划已生成。");
  } catch (error) {
    showToast(error.message);
  }
}

function renderPlanPanel() {
  const panel = document.getElementById("planPanel");
  if (!panel) return;

  const plan = state.currentPlan;
  if (!plan) {
    panel.className = "empty-panel";
    panel.innerHTML = "<p>还没有学习计划，点击左侧按钮即可生成。</p>";
    return;
  }

  const goals = Array.isArray(plan.goals) ? plan.goals : [];
  const focusTopics = Array.isArray(plan.focus_topics) ? plan.focus_topics : [];
  const dailyPlan = Array.isArray(plan.daily_plan) ? plan.daily_plan : [];

  panel.className = "";
  panel.innerHTML = `
    <div class="plan-card">
      <div class="question-meta">
        <span class="tag">周期 ${escapeHtml(plan.duration || "-")}</span>
        ${focusTopics.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}
      </div>
      <h3>计划目标</h3>
      <ul class="bullet-list">
        ${(goals.length ? goals : ["暂无"]).map((item) => `<li>${escapeHtml(stringifyItem(item))}</li>`).join("")}
      </ul>
      <h3 style="margin-top: 18px;">每日安排</h3>
      <div class="detail-list">
        ${(dailyPlan.length ? dailyPlan : ["暂无安排"]).map((item, index) => `
          <div class="profile-card">
            <strong>安排 ${index + 1}</strong>
            <div style="margin-top: 8px; line-height: 1.8;">${renderPlanItem(item)}</div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function renderPlanFocusSummary() {
  const panel = document.getElementById("planFocusSummary");
  if (!panel) return;
  if (!state.profile) {
    panel.innerHTML = "<p>加载画像后，这里会给出当前适合重点复习的方向。</p>";
    return;
  }

  const weakTopics = profileWeakTopics(state.profile);
  panel.innerHTML = `
    <p><strong>建议重点：</strong>${weakTopics.length ? weakTopics.map(escapeHtml).join("、") : "当前没有明显薄弱项，可继续均衡复习。"}</p>
    <p><strong>可投入时间：</strong>${escapeHtml(state.profile.available_time || "-")}</p>
  `;
}

function renderPracticeHints() {
  const panel = document.getElementById("practiceHints");
  if (!panel) return;
  if (!state.profile) {
    panel.innerHTML = "<p>加载学生画像后，这里会显示近期主题与薄弱知识点提示。</p>";
    return;
  }

  const recentTopics = state.profile.history?.recent_topics || [];
  const weakTopics = profileWeakTopics(state.profile);
  panel.innerHTML = `
    <p><strong>薄弱知识点：</strong>${weakTopics.length ? weakTopics.map(escapeHtml).join("、") : "暂无明显薄弱项"}</p>
    <p><strong>近期主题：</strong>${recentTopics.length ? recentTopics.map(escapeHtml).join("、") : "暂无记录"}</p>
  `;
}

function renderAllProfileViews() {
  renderDashboardProfileSummary();
  renderProfilePanel();
  renderPlanFocusSummary();
  renderPracticeHints();
}

function renderDashboardProfileSummary() {
  const panel = document.getElementById("dashboardProfileSummary");
  if (!panel) return;

  if (!state.profile) {
    panel.innerHTML = "<p>还没有加载学生画像。先在左侧创建或读取一个学生。</p>";
    panel.className = "empty-panel";
    return;
  }

  panel.className = "";
  panel.innerHTML = renderProfileSummaryMarkup(state.profile);
}

function renderProfilePanel() {
  const panel = document.getElementById("profilePanel");
  if (!panel) return;

  if (!state.profile) {
    panel.innerHTML = "<p>还没有加载学生画像。先在左侧初始化或读取一个学生。</p>";
    panel.className = "empty-panel";
    return;
  }

  const profile = state.profile;
  const weakTopics = profileWeakTopics(profile);
  const strongTopics = profileStrongTopics(profile);
  const recentQuestions = profile.history?.recent_questions || [];
  const recentTopics = profile.history?.recent_topics || [];
  const wrongQuestions = profile.wrong_questions || [];

  panel.className = "";
  panel.innerHTML = `
    <div class="detail-list">
      <div class="metric-grid">
        <div class="metric-card">
          <span>学生 ID</span>
          <strong>${escapeHtml(profile.student_id)}</strong>
        </div>
        <div class="metric-card">
          <span>最近更新</span>
          <strong>${escapeHtml(profile.updated_at || "-")}</strong>
        </div>
        <div class="metric-card">
          <span>薄弱知识点</span>
          <strong>${weakTopics.length}</strong>
        </div>
        <div class="metric-card">
          <span>掌握较好</span>
          <strong>${strongTopics.length}</strong>
        </div>
      </div>
      <div class="profile-card">
        <h3>基本信息</h3>
        <div class="detail-list">
          <div><strong>学习目标：</strong>${escapeHtml(profile.target || "-")}</div>
          <div><strong>可投入时间：</strong>${escapeHtml(profile.available_time || "-")}</div>
        </div>
      </div>
      <div class="profile-card">
        <h3>知识掌握</h3>
        <div class="tag-row">${renderKnowledgeStateTags(profile.knowledge_state)}</div>
      </div>
      <div class="profile-card">
        <h3>正确率概览</h3>
        <div class="tag-row">${renderAccuracyTags(profile.accuracy_by_topic)}</div>
      </div>
      <div class="content-grid">
        <div class="profile-card">
          <h3>近期主题</h3>
          <div class="tag-row">
            ${recentTopics.length ? recentTopics.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") : "<span class='tag'>暂无记录</span>"}
          </div>
        </div>
        <div class="profile-card">
          <h3>近期提问</h3>
          <ul class="bullet-list">
            ${(recentQuestions.length ? recentQuestions.slice(-5) : ["暂无记录"]).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </div>
      </div>
      <div class="profile-card">
        <h3>错题记录</h3>
        ${wrongQuestions.length ? `
          <div class="detail-list">
            ${wrongQuestions.slice(-5).map((item) => `
              <div class="summary-card">
                <span>${escapeHtml(item.knowledge_point || "-")}</span>
                <strong>${escapeHtml(item.question_id || "-")}</strong>
                <div style="margin-top: 8px; color: var(--muted);">${escapeHtml(item.error_type || "-")}</div>
              </div>
            `).join("")}
          </div>
        ` : "<p class='helper-text'>当前没有错题记录。</p>"}
      </div>
    </div>
  `;
}

function renderProfileSummaryMarkup(profile) {
  const weakTopics = profileWeakTopics(profile);
  const strongTopics = profileStrongTopics(profile);
  const recentTopics = profile.history?.recent_topics || [];

  return `
    <div class="summary-grid">
      <div class="summary-card">
        <span>学习目标</span>
        <strong>${escapeHtml(profile.target || "-")}</strong>
      </div>
      <div class="summary-card">
        <span>可投入时间</span>
        <strong>${escapeHtml(profile.available_time || "-")}</strong>
      </div>
      <div class="summary-card">
        <span>薄弱知识点</span>
        <strong>${weakTopics.length ? weakTopics.map(escapeHtml).join("、") : "暂无"}</strong>
      </div>
      <div class="summary-card">
        <span>掌握较好</span>
        <strong>${strongTopics.length ? strongTopics.map(escapeHtml).join("、") : "暂无"}</strong>
      </div>
    </div>
    <div class="tag-row" style="margin-top: 16px;">
      ${recentTopics.length ? recentTopics.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("") : "<span class='tag'>暂无近期主题</span>"}
    </div>
  `;
}

function renderKnowledgeStateTags(map) {
  const entries = Object.entries(map || {});
  if (!entries.length) {
    return "<span class='tag'>暂无数据</span>";
  }
  return entries.map(([key, value]) => `<span class="tag">${escapeHtml(key)} · ${escapeHtml(value)}</span>`).join("");
}

function renderAccuracyTags(map) {
  const entries = Object.entries(map || {});
  if (!entries.length) {
    return "<span class='tag'>暂无数据</span>";
  }
  return entries.map(([key, value]) => {
    const percent = Math.round(Number(value || 0) * 100);
    return `<span class="tag">${escapeHtml(key)} · ${percent}%</span>`;
  }).join("");
}

function profileWeakTopics(profile) {
  return Object.entries(profile?.knowledge_state || {})
    .filter(([, value]) => String(value).includes("薄弱"))
    .map(([key]) => key);
}

function profileStrongTopics(profile) {
  return Object.entries(profile?.knowledge_state || {})
    .filter(([, value]) => String(value).includes("掌握"))
    .map(([key]) => key);
}

function ensureStudent() {
  if (state.studentId) return true;
  const fallback = document.querySelector("[data-student-input]")?.value.trim() || "";
  if (fallback) {
    setStudentId(fallback);
    return true;
  }
  showToast("请先绑定学生 ID，再继续操作。");
  return false;
}

function isServedOverHttp() {
  return window.location.protocol === "http:" || window.location.protocol === "https:";
}

function ensureAppServed() {
  if (isServedOverHttp()) return true;
  updateHealthDisplay("offline", "请通过启动脚本打开");
  showToast("请先运行项目根目录下的 start_learning_assistant.bat，再在浏览器中使用系统。");
  return false;
}

async function apiRequest(path, options = {}) {
  const config = {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  };
  if (options.body !== undefined) {
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, config);
  const data = await tryReadJson(response);
  if (!response.ok) {
    throw new Error(data?.detail || `请求失败：${response.status}`);
  }
  return data;
}

async function tryReadJson(response) {
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

function readJson(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch (error) {
    return fallback;
  }
}

function readFormValue(form, name) {
  return new FormData(form).get(name)?.toString().trim() || "";
}

function renderPlanItem(item) {
  if (typeof item === "string") {
    return escapeHtml(item);
  }
  if (item && typeof item === "object") {
    const parts = [];
    if (item.day) parts.push(`<div><strong>时间：</strong>${escapeHtml(String(item.day))}</div>`);
    if (item.focus) parts.push(`<div><strong>重点：</strong>${escapeHtml(String(item.focus))}</div>`);
    if (Array.isArray(item.tasks)) {
      parts.push(`<ul class="bullet-list">${item.tasks.map((task) => `<li>${escapeHtml(String(task))}</li>`).join("")}</ul>`);
    }
    if (item.time_commitment) {
      parts.push(`<div><strong>投入：</strong>${escapeHtml(String(item.time_commitment))}</div>`);
    }
    return parts.join("");
  }
  return escapeHtml(String(item));
}

function stringifyItem(item) {
  if (typeof item === "string") return item;
  if (item && typeof item === "object") return JSON.stringify(item);
  return String(item);
}

function renderTagRow(points = [], sources = []) {
  const tags = [];
  if (Array.isArray(points)) {
    tags.push(...points.map((item) => `<span class="tag">${escapeHtml(item)}</span>`));
  }
  if (Array.isArray(sources)) {
    tags.push(...sources.map((item) => `<span class="tag">${escapeHtml(item)}</span>`));
  }
  return tags.length ? `<div class="tag-row">${tags.join("")}</div>` : "";
}

function stripChoicePrefix(value) {
  return String(value).replace(/^[A-Da-d][\.\)\:\：、\s]+/, "").trim();
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 2800);
}

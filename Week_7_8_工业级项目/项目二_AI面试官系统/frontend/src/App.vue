<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { apiRequest, clearStoredToken, getStoredToken, storeToken } from "./api/client";
import AuthPanel from "./components/AuthPanel.vue";
import CandidateAuthPanel from "./components/CandidateAuthPanel.vue";
import CandidateInterviewRoom from "./components/CandidateInterviewRoom.vue";
import CandidateInviteLanding from "./components/CandidateInviteLanding.vue";
import CandidateSetup from "./components/CandidateSetup.vue";
import DashboardPanel from "./components/DashboardPanel.vue";
import InterviewCreatePanel from "./components/InterviewCreatePanel.vue";
import InterviewWorkspace from "./components/InterviewWorkspace.vue";
import SessionsPanel from "./components/SessionsPanel.vue";

const token = ref(getStoredToken());
const isConsole =
  window.location.pathname.endsWith("/console") ||
  window.location.search.includes("mode=console") ||
  window.location.hash === "#console";
const activeView = ref(isConsole ? "dashboard" : "candidate");
const urlParams = new URLSearchParams(window.location.search);
const inviteToken = ref(urlParams.get("invite_token") || urlParams.get("invite") || "");
const showCandidateLogin = ref(false);
const sessions = ref([]);
const sessionsLoading = ref(false);
const detailLoading = ref(false);
const currentSession = ref(null);
const selectedQuestionId = ref("");
const answers = reactive({});
const streamEvents = ref([]);

const currentReport = computed(() => currentSession.value?.report || null);

function showNotice(message, type = "success") {
  ElMessage({ message, type, showClose: true });
}

function resetAnswers(nextAnswers = []) {
  Object.keys(answers).forEach((key) => delete answers[key]);
  nextAnswers.forEach((item) => {
    answers[item.question_id] = item.answer;
  });
}

function normalizeGeneratedSession(data) {
  return {
    ...data,
    status: "questions_generated",
    question_count: data.questions.length,
    answer_count: 0,
    follow_up_count: 0,
    overall_score: null,
    level: null,
    resume_text: "",
    answers: [],
    follow_ups: [],
    report: null,
    created_at: null,
    updated_at: null,
  };
}

function setCurrentSession(data) {
  currentSession.value = data;
  selectedQuestionId.value = data?.questions?.[0]?.id || "";
  resetAnswers(data?.answers || []);
  streamEvents.value = (data?.follow_ups || []).flatMap((followUp) =>
    followUp.follow_up_questions.map((question) => ({
      name: "follow_up",
      data: { question },
    })),
  );
}

async function fetchSessions(showSuccess = false) {
  if (!token.value) {
    sessions.value = [];
    return;
  }
  sessionsLoading.value = true;
  try {
    const data = await apiRequest("/interviews/sessions", {}, token.value);
    sessions.value = data.sessions;
    if (showSuccess) {
      showNotice("面试会话已刷新");
    }
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    sessionsLoading.value = false;
  }
}

async function openSession(sessionId) {
  if (!token.value) {
    showNotice("请先登录", "warning");
    return;
  }
  detailLoading.value = true;
  try {
    const detail = await apiRequest(`/interviews/sessions/${encodeURIComponent(sessionId)}`, {}, token.value);
    setCurrentSession(detail);
    activeView.value = "workspace";
  } catch (error) {
    showNotice(error.message, "error");
  } finally {
    detailLoading.value = false;
  }
}

function onLoggedIn(accessToken) {
  token.value = accessToken;
  storeToken(accessToken);
  showCandidateLogin.value = false;
  activeView.value = isConsole ? "dashboard" : "candidate";
  showNotice("登录成功");
  if (isConsole) {
    fetchSessions();
  }
}

function requireCandidateLogin() {
  showCandidateLogin.value = true;
  showNotice("请先登录候选人账号，登录后会回到邀请页", "info");
}

function clearInviteMode() {
  inviteToken.value = "";
  showCandidateLogin.value = false;
  const nextUrl = `${window.location.pathname}${window.location.hash || ""}`;
  window.history.replaceState({}, "", nextUrl);
}

function logout() {
  token.value = "";
  clearStoredToken();
  sessions.value = [];
  currentSession.value = null;
  activeView.value = isConsole ? "dashboard" : "candidate";
  showNotice("已退出登录", "info");
}

function onQuestionsGenerated(data) {
  setCurrentSession(normalizeGeneratedSession(data));
  activeView.value = isConsole ? "workspace" : "candidate";
  showNotice("面试题已生成");
  if (isConsole) {
    fetchSessions();
  }
}

function selectQuestion(questionId) {
  selectedQuestionId.value = questionId;
}

function updateAnswer({ questionId, answer }) {
  if (answer.trim()) {
    answers[questionId] = answer;
  } else {
    delete answers[questionId];
  }
}

function onStreamEvent(event) {
  streamEvents.value.push(event);
  if (event.name === "done") {
    fetchSessions();
  }
}

function onReportCreated(report) {
  currentSession.value = {
    ...currentSession.value,
    status: "evaluated",
    report,
    overall_score: report.overall_score,
    level: report.level,
    answer_count: Object.keys(answers).length,
  };
  showNotice("评分报告已生成");
  if (isConsole) {
    fetchSessions();
  }
}

onMounted(() => {
  if (isConsole) {
    fetchSessions();
  }
});
</script>

<template>
  <template v-if="!isConsole">
    <CandidateAuthPanel
      v-if="!token && (!inviteToken || showCandidateLogin)"
      @logged-in="onLoggedIn"
      @notice="showNotice"
    />
    <CandidateInviteLanding
      v-else-if="inviteToken && !currentSession"
      :invite-token="inviteToken"
      :token="token"
      @generated="onQuestionsGenerated"
      @login-required="requireCandidateLogin"
      @clear-invite="clearInviteMode"
      @logout="logout"
      @open-session="openSession"
      @notice="showNotice"
    />
    <CandidateSetup
      v-else-if="!currentSession"
      :token="token"
      @generated="onQuestionsGenerated"
      @logout="logout"
      @notice="showNotice"
    />
    <CandidateInterviewRoom
      v-else
      :token="token"
      :session="currentSession"
      :answers="answers"
      :stream-events="streamEvents"
      :report="currentReport"
      @update-answer="updateAnswer"
      @stream-event="onStreamEvent"
      @report-created="onReportCreated"
      @logout="logout"
      @notice="showNotice"
    />
  </template>

  <el-container v-else class="enterprise-shell">
    <el-aside class="sidebar" width="268px">
      <div class="brand-block">
        <div class="brand-mark">AI</div>
        <div>
          <strong>面试官控制台</strong>
          <span>Interview Operations</span>
        </div>
      </div>

      <el-menu :default-active="activeView" class="side-menu" @select="activeView = $event">
        <el-menu-item index="dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="sessions">
          <el-icon><Tickets /></el-icon>
          <span>面试会话</span>
        </el-menu-item>
        <el-menu-item index="create">
          <el-icon><CirclePlus /></el-icon>
          <span>创建面试</span>
        </el-menu-item>
        <el-menu-item index="workspace" :disabled="!currentSession">
          <el-icon><Monitor /></el-icon>
          <span>面试工作台</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <span>Phase 6 Enterprise UI</span>
        <strong>Vue · Element Plus · ECharts</strong>
      </div>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div>
          <p>HR / 面试官后台</p>
          <h1>AI 面试管理工作台</h1>
        </div>
        <div class="header-actions">
          <el-button v-if="token" :loading="sessionsLoading" @click="fetchSessions(true)">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
          <el-tag :type="token ? 'success' : 'info'" size="large">
            {{ token ? "已登录" : "未登录" }}
          </el-tag>
          <el-button v-if="token" plain @click="logout">退出</el-button>
        </div>
      </el-header>

      <el-main class="app-main" v-loading="detailLoading">
        <AuthPanel
          v-if="!token"
          @logged-in="onLoggedIn"
          @notice="showNotice"
        />

        <template v-else>
          <DashboardPanel
            v-if="activeView === 'dashboard'"
            :sessions="sessions"
            :loading="sessionsLoading"
            @create="activeView = 'create'"
            @open-sessions="activeView = 'sessions'"
          />
          <SessionsPanel
            v-else-if="activeView === 'sessions'"
            :sessions="sessions"
            :loading="sessionsLoading"
            :active-session-id="currentSession?.session_id || ''"
            @refresh="fetchSessions(true)"
            @open-session="openSession"
          />
          <InterviewCreatePanel
            v-else-if="activeView === 'create'"
            :token="token"
            @generated="onQuestionsGenerated"
            @notice="showNotice"
          />
          <InterviewWorkspace
            v-else
            :token="token"
            :session="currentSession"
            :selected-question-id="selectedQuestionId"
            :answers="answers"
            :stream-events="streamEvents"
            :report="currentReport"
            @select-question="selectQuestion"
            @update-answer="updateAnswer"
            @stream-event="onStreamEvent"
            @report-created="onReportCreated"
            @notice="showNotice"
          />
        </template>
      </el-main>
    </el-container>
  </el-container>
</template>

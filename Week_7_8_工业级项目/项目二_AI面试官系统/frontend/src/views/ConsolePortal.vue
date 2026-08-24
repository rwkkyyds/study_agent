<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import AuthPanel from "../components/AuthPanel.vue";
import DashboardPanel from "../components/DashboardPanel.vue";
import InterviewCreatePanel from "../components/InterviewCreatePanel.vue";
import InterviewWorkspace from "../components/InterviewWorkspace.vue";
import SessionsPanel from "../components/SessionsPanel.vue";
import { useAuthStore } from "../stores/authStore";
import { useSessionStore } from "../stores/sessionStore";

const authStore = useAuthStore();
const sessionStore = useSessionStore();
const activeView = ref("dashboard");

function showNotice(message, type = "success") {
  ElMessage({ message, type, showClose: true });
}

async function fetchSessions(showSuccess = false) {
  try {
    await sessionStore.fetchSessions(authStore.token);
    if (showSuccess) {
      showNotice("面试会话已刷新");
    }
  } catch (error) {
    showNotice(error.message, "error");
  }
}

async function openSession(sessionId) {
  if (!authStore.token) {
    showNotice("请先登录", "warning");
    return;
  }
  try {
    const { internalReportError } = await sessionStore.openSession(sessionId, authStore.token, {
      internalReport: true,
    });
    activeView.value = "workspace";
    if (internalReportError) {
      showNotice(`已打开会话，但完整内部报告读取失败：${internalReportError}`, "warning");
    }
  } catch (error) {
    showNotice(error.message, "error");
  }
}

function onLoggedIn(accessToken) {
  authStore.setToken(accessToken);
  activeView.value = "dashboard";
  showNotice("登录成功");
  fetchSessions();
}

function logout() {
  authStore.clearToken();
  sessionStore.clearSession();
  activeView.value = "dashboard";
  showNotice("已退出登录", "info");
}

function onQuestionsGenerated(data) {
  sessionStore.setGeneratedSession(data);
  activeView.value = "workspace";
  showNotice("面试题已生成");
  fetchSessions();
}

function onStreamEvent(event) {
  sessionStore.addStreamEvent(event);
  if (event.name === "done") {
    fetchSessions();
  }
}

async function onReportCreated(report) {
  sessionStore.setReport(report);
  try {
    await sessionStore.refreshInternalReport(authStore.token);
  } catch (error) {
    showNotice(`候选人版报告已生成，内部完整报告读取失败：${error.message}`, "warning");
  }
  showNotice("评分报告已生成");
  fetchSessions();
}

onMounted(() => {
  if (authStore.token) {
    fetchSessions();
  }
});
</script>

<template>
  <el-container class="enterprise-shell">
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
        <el-menu-item index="workspace" :disabled="!sessionStore.currentSession">
          <el-icon><Monitor /></el-icon>
          <span>面试工作台</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <span>Phase 8 P0 Console</span>
        <strong>Vue Router · Pinia · RBAC</strong>
      </div>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div>
          <p>HR / 面试官后台</p>
          <h1>AI 面试管理工作台</h1>
        </div>
        <div class="header-actions">
          <el-button v-if="authStore.token" :loading="sessionStore.sessionsLoading" @click="fetchSessions(true)">
            <el-icon><Refresh /></el-icon>
            刷新数据
          </el-button>
          <el-tag :type="authStore.token ? 'success' : 'info'" size="large">
            {{ authStore.token ? "已登录" : "未登录" }}
          </el-tag>
          <el-button v-if="authStore.token" plain @click="logout">退出</el-button>
        </div>
      </el-header>

      <el-main class="app-main" v-loading="sessionStore.detailLoading">
        <AuthPanel
          v-if="!authStore.token"
          @logged-in="onLoggedIn"
          @notice="showNotice"
        />

        <template v-else>
          <DashboardPanel
            v-if="activeView === 'dashboard'"
            :sessions="sessionStore.sessions"
            :loading="sessionStore.sessionsLoading"
            @create="activeView = 'create'"
            @open-sessions="activeView = 'sessions'"
          />
          <SessionsPanel
            v-else-if="activeView === 'sessions'"
            :sessions="sessionStore.sessions"
            :loading="sessionStore.sessionsLoading"
            :active-session-id="sessionStore.currentSession?.session_id || ''"
            @refresh="fetchSessions(true)"
            @open-session="openSession"
          />
          <InterviewCreatePanel
            v-else-if="activeView === 'create'"
            :token="authStore.token"
            @generated="onQuestionsGenerated"
            @notice="showNotice"
          />
          <InterviewWorkspace
            v-else
            :token="authStore.token"
            :session="sessionStore.currentSession"
            :selected-question-id="sessionStore.selectedQuestionId"
            :answers="sessionStore.answers"
            :stream-events="sessionStore.streamEvents"
            :report="sessionStore.currentReport"
            @select-question="sessionStore.selectQuestion"
            @update-answer="sessionStore.updateAnswer"
            @stream-event="onStreamEvent"
            @report-created="onReportCreated"
            @notice="showNotice"
          />
        </template>
      </el-main>
    </el-container>
  </el-container>
</template>

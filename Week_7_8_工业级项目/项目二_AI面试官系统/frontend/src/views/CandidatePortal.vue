<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import CandidateAuthPanel from "../components/CandidateAuthPanel.vue";
import CandidateInterviewRoom from "../components/CandidateInterviewRoom.vue";
import CandidateInviteLanding from "../components/CandidateInviteLanding.vue";
import CandidateSetup from "../components/CandidateSetup.vue";
import { useAuthStore } from "../stores/authStore";
import { useSessionStore } from "../stores/sessionStore";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const sessionStore = useSessionStore();
const showCandidateLogin = ref(false);
const inviteToken = computed(() => route.query.invite_token || route.query.invite || "");

function showNotice(message, type = "success") {
  ElMessage({ message, type, showClose: true });
}

async function openSession(sessionId) {
  if (!authStore.token) {
    showNotice("请先登录", "warning");
    return;
  }
  try {
    await sessionStore.openSession(sessionId, authStore.token);
  } catch (error) {
    showNotice(error.message, "error");
  }
}

function onLoggedIn(accessToken) {
  authStore.setToken(accessToken);
  showCandidateLogin.value = false;
  showNotice("登录成功");
}

function requireCandidateLogin() {
  showCandidateLogin.value = true;
  showNotice("请先登录候选人账号，登录后会回到邀请页", "info");
}

function clearInviteMode() {
  showCandidateLogin.value = false;
  router.replace({ path: "/candidate" });
}

function logout() {
  authStore.clearToken();
  sessionStore.clearSession();
  showNotice("已退出登录", "info");
}

function onQuestionsGenerated(data) {
  sessionStore.setGeneratedSession(data);
  showNotice("面试题已生成");
}

function onStreamEvent(event) {
  sessionStore.addStreamEvent(event);
}

function onReportCreated(report) {
  sessionStore.setReport(report);
  showNotice("评分报告已生成");
}
</script>

<template>
  <CandidateAuthPanel
    v-if="!authStore.token && (!inviteToken || showCandidateLogin)"
    @logged-in="onLoggedIn"
    @notice="showNotice"
  />
  <CandidateInviteLanding
    v-else-if="inviteToken && !sessionStore.currentSession"
    :invite-token="inviteToken"
    :token="authStore.token"
    @generated="onQuestionsGenerated"
    @login-required="requireCandidateLogin"
    @clear-invite="clearInviteMode"
    @logout="logout"
    @open-session="openSession"
    @notice="showNotice"
  />
  <CandidateSetup
    v-else-if="!sessionStore.currentSession"
    :token="authStore.token"
    @generated="onQuestionsGenerated"
    @logout="logout"
    @notice="showNotice"
  />
  <CandidateInterviewRoom
    v-else
    :token="authStore.token"
    :session="sessionStore.currentSession"
    :answers="sessionStore.answers"
    :stream-events="sessionStore.streamEvents"
    :report="sessionStore.currentReport"
    @update-answer="sessionStore.updateAnswer"
    @stream-event="onStreamEvent"
    @report-created="onReportCreated"
    @logout="logout"
    @notice="showNotice"
  />
</template>

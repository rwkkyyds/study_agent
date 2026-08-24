<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { apiRequest } from "../api/client";

const props = defineProps({
  inviteToken: { type: String, default: "" },
  token: { type: String, default: "" },
});
const emit = defineEmits(["generated", "login-required", "clear-invite", "logout", "open-session", "notice"]);

const loading = ref(false);
const busy = ref(false);
const resumeLoading = ref(false);
const invite = ref(null);
const existingSessionId = ref("");
const form = reactive({
  difficulty: "mid",
  questionCount: 5,
  resumeText:
    "候选人有 FastAPI、LangGraph、RAG、SQLAlchemy 项目经验，做过企业知识库问答、工单流转、JWT 鉴权、SSE 流式输出和 Docker 部署。",
});

const isInviteUsable = computed(() => invite.value?.status === "invited");
const canResumeInvite = computed(() => Boolean(props.token && existingSessionId.value));
const statusCopy = computed(() => {
  const status = invite.value?.status;
  if (status === "invited") {
    return { label: "邀请有效", type: "success" };
  }
  if (status === "accepted") {
    return { label: "已开始", type: "warning" };
  }
  if (status === "expired") {
    return { label: "已过期", type: "danger" };
  }
  return { label: status || "未知状态", type: "info" };
});

async function fetchInvite() {
  if (!props.inviteToken) {
    invite.value = null;
    return;
  }

  loading.value = true;
  try {
    invite.value = await apiRequest(`/hiring/invites/${encodeURIComponent(props.inviteToken)}`, {}, "");
    await fetchExistingInviteSession();
  } catch (error) {
    invite.value = null;
    emit("notice", error.message, "error");
  } finally {
    loading.value = false;
  }
}

async function fetchExistingInviteSession() {
  existingSessionId.value = "";
  if (!props.token || !invite.value?.id) {
    return;
  }

  resumeLoading.value = true;
  try {
    const data = await apiRequest("/interviews/sessions", {}, props.token);
    const matchedSession = data.sessions.find((session) => session.invite_id === invite.value.id);
    existingSessionId.value = matchedSession?.session_id || "";
  } catch (error) {
    emit("notice", error.message, "error");
  } finally {
    resumeLoading.value = false;
  }
}

async function startFromInvite() {
  if (!props.token) {
    emit("login-required");
    return;
  }
  if (canResumeInvite.value) {
    emit("open-session", existingSessionId.value);
    return;
  }
  if (!isInviteUsable.value) {
    emit("notice", "当前邀请状态不允许开始面试", "warning");
    return;
  }
  if (form.resumeText.trim().length < 20) {
    emit("notice", "请先填写至少 20 个字的简历或项目经历", "warning");
    return;
  }

  busy.value = true;
  try {
    const data = await apiRequest(
      "/interviews/questions",
      {
        method: "POST",
        body: JSON.stringify({
          invite_token: props.inviteToken,
          resume_text: form.resumeText.trim(),
          difficulty: form.difficulty,
          question_count: Number(form.questionCount),
        }),
      },
      props.token,
    );
    emit("generated", data);
  } catch (error) {
    emit("notice", error.message, "error");
  } finally {
    busy.value = false;
  }
}

watch(() => props.inviteToken, fetchInvite);
watch(() => props.token, fetchExistingInviteSession);
onMounted(fetchInvite);
</script>

<template>
  <main class="candidate-invite">
    <header class="candidate-setup-topbar invite-topbar">
      <div class="candidate-brand candidate-brand-dark">
        <span class="candidate-brand-mark">AI</span>
        <span>Interview invitation</span>
      </div>
      <div class="invite-top-actions">
        <button v-if="token" class="ghost-link" type="button" @click="$emit('logout')">
          退出登录
          <el-icon><Right /></el-icon>
        </button>
        <button class="ghost-link" type="button" @click="$emit('clear-invite')">
          自由练习
          <el-icon><Switch /></el-icon>
        </button>
      </div>
    </header>

    <section class="invite-layout" v-loading="loading">
      <section class="invite-hero-card">
        <p class="eyebrow">PRIVATE INVITATION</p>
        <h1>这是一场为你准备的面试。</h1>
        <p>
          Alex 会根据 HR 发来的岗位邀请、你的项目经历和岗位评分标准生成问题。先确认邀请，再补充你的经历，就可以进入面试间。
        </p>
        <div class="invite-ribbon">
          <span>Invite token</span>
          <strong>{{ inviteToken.slice(0, 10) }}...</strong>
        </div>
      </section>

      <section class="invite-panel">
        <template v-if="invite">
          <div class="invite-panel-heading">
            <div>
              <p class="eyebrow">邀请详情</p>
              <h2>{{ invite.job_title || "待确认岗位" }}</h2>
            </div>
            <el-tag :type="statusCopy.type" size="large">{{ statusCopy.label }}</el-tag>
          </div>

          <div class="invite-fact-grid">
            <div>
              <span>候选人</span>
              <strong>{{ invite.candidate_name || "候选人" }}</strong>
            </div>
            <div>
              <span>联系邮箱</span>
              <strong>{{ invite.candidate_email_masked || "未填写" }}</strong>
            </div>
            <div>
              <span>岗位级别</span>
              <strong>{{ invite.job_level || "待确认" }}</strong>
            </div>
            <div>
              <span>有效期至</span>
              <strong>{{ new Date(invite.expires_at).toLocaleString() }}</strong>
            </div>
          </div>

          <el-alert
            v-if="!token"
            class="invite-alert"
            title="请先登录候选人账号，再启动这场邀请面试。"
            type="info"
            :closable="false"
          />
          <el-alert
            v-else-if="!isInviteUsable"
            class="invite-alert"
            :title="canResumeInvite ? '已找到这封邀请对应的历史会话，可直接继续。' : '当前邀请无法直接开始；如果已经开始过，请从历史会话继续。'"
            type="warning"
            :closable="false"
          />

          <el-form class="invite-form" label-position="top" @submit.prevent>
            <div class="setup-form-row">
              <el-form-item label="面试难度">
                <el-select v-model="form.difficulty" size="large">
                  <el-option label="初级 · Junior" value="junior" />
                  <el-option label="中级 · Mid" value="mid" />
                  <el-option label="高级 · Senior" value="senior" />
                </el-select>
              </el-form-item>
              <el-form-item label="面试题数">
                <el-input-number v-model="form.questionCount" :min="3" :max="8" size="large" />
              </el-form-item>
            </div>
            <el-form-item label="简历或项目经历">
              <el-input
                v-model="form.resumeText"
                :rows="7"
                resize="vertical"
                type="textarea"
                placeholder="补充你最希望 AI 面试官追问的项目经历..."
              />
            </el-form-item>
          </el-form>

          <div class="invite-panel-footer">
            <span>
              {{
                canResumeInvite
                  ? "已自动匹配到这封邀请的面试会话。"
                  : token
                    ? "开始后邀请会绑定到当前账号。"
                    : "登录后会回到这个邀请页。"
              }}
            </span>
            <el-button :loading="busy || resumeLoading" class="candidate-primary-button" size="large" @click="startFromInvite">
              {{ canResumeInvite ? "继续上次面试" : token ? "确认并开始面试" : "登录后开始" }}
              <el-icon><Right /></el-icon>
            </el-button>
          </div>
        </template>

        <template v-else-if="!loading">
          <div class="invite-empty">
            <div class="ai-avatar ai-avatar-large" aria-hidden="true"><span>AI</span><i></i></div>
            <h2>没有找到这封邀请。</h2>
            <p>请确认链接是否完整，或返回自由练习模式。</p>
            <el-button class="candidate-secondary-button" size="large" @click="$emit('clear-invite')">
              返回自由练习
            </el-button>
          </div>
        </template>
      </section>
    </section>
  </main>
</template>

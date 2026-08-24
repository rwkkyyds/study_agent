<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { apiRequest } from "../api/client";

const props = defineProps({
  token: { type: String, default: "" },
  session: { type: Object, default: null },
  answers: { type: Object, default: () => ({}) },
  streamEvents: { type: Array, default: () => [] },
  report: { type: Object, default: null },
});
const emit = defineEmits(["update-answer", "stream-event", "report-created", "logout", "new-session", "notice"]);

const questionIndex = ref(0);
const answerText = ref("");
const streaming = ref(false);
const evaluating = ref(false);
const followUpReady = ref(false);
const timeLeft = ref(45 * 60);
const draftsLoaded = ref(false);
const draftStatus = ref("idle");
let source = null;
let timer = null;
let draftTimer = null;

const questions = computed(() => props.session?.questions || []);
const currentQuestion = computed(() => questions.value[questionIndex.value] || null);
const answeredCount = computed(() => Object.values(props.answers).filter((item) => item?.trim()).length);
const progressPercent = computed(() =>
  questions.value.length ? Math.round((answeredCount.value / questions.value.length) * 100) : 0,
);
const isLastQuestion = computed(() => questionIndex.value === questions.value.length - 1);
const timerText = computed(() => {
  const minutes = String(Math.floor(timeLeft.value / 60)).padStart(2, "0");
  const seconds = String(timeLeft.value % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
});
const draftStatusText = computed(() => {
  if (draftStatus.value === "loading") {
    return "正在恢复草稿";
  }
  if (draftStatus.value === "saving") {
    return "正在保存草稿";
  }
  if (draftStatus.value === "saved") {
    return "草稿已保存";
  }
  if (draftStatus.value === "error") {
    return "草稿保存失败";
  }
  return "草稿自动保存";
});
const stageItems = computed(() => {
  const stages = ["自我介绍", "项目经历", "技术深度", "问题解决", "系统设计", "场景判断", "团队协作", "反向提问"];
  const active = Math.min(Math.floor((questionIndex.value / Math.max(questions.value.length, 1)) * stages.length), stages.length - 1);
  return stages.map((label, index) => ({
    label,
    state: index < active ? "done" : index === active ? "current" : "todo",
  }));
});
const liveSignals = computed(() => [
  { label: "已完成回答", value: answeredCount.value, suffix: ` / ${questions.value.length}` },
  { label: "已触发追问", value: props.streamEvents.filter((item) => item.name === "follow_up").length, suffix: " 次" },
  { label: "面试进度", value: progressPercent.value, suffix: "%" },
]);
const conversation = computed(() => {
  const messages = [
    {
      id: "welcome",
      role: "ai",
      kind: "normal",
      text: `你好，我是 Alex，今天的 AI 面试官。接下来我会围绕「${props.session?.job_title || "目标岗位"}」和你的经历展开对话。你可以把它当成一次真实的交流，不用急着给出完美答案。`,
      time: "刚刚",
    },
  ];

  questions.value.forEach((question, index) => {
    if (index > questionIndex.value && !props.answers[question.id]) {
      return;
    }
    messages.push({
      id: `question-${question.id}`,
      role: "ai",
      kind: "question",
      text: question.question,
      time: index === questionIndex.value ? "当前问题" : "已提问",
    });
    if (props.answers[question.id]) {
      messages.push({
        id: `answer-${question.id}`,
        role: "user",
        kind: "normal",
        text: props.answers[question.id],
        time: "已提交",
      });
    }
  });

  props.streamEvents
    .filter((event) => event.name === "follow_up" && event.data?.question)
    .forEach((event, index) => {
      messages.push({
        id: `follow-up-${index}`,
        role: "ai",
        kind: "follow-up",
        text: event.data.question,
        time: "AI 追问",
      });
    });
  if (streaming.value) {
    messages.push({ id: "typing", role: "ai", kind: "typing", text: "", time: "正在思考" });
  }
  return messages;
});

function syncAnswer() {
  answerText.value = props.answers[currentQuestion.value?.id] || "";
}

function eventText(event) {
  return event.data?.question || event.data?.node || event.data?.message || "面试流程已更新";
}

function closeStream() {
  if (source) {
    source.close();
    source = null;
  }
}

async function restoreDrafts() {
  if (!props.token || !props.session?.session_id) {
    draftsLoaded.value = true;
    return;
  }

  draftsLoaded.value = false;
  draftStatus.value = "loading";
  try {
    const data = await apiRequest(`/interviews/sessions/${encodeURIComponent(props.session.session_id)}/drafts`, {}, props.token);
    const restored = {};
    data.drafts.forEach((draft) => {
      restored[draft.question_id] = draft.answer;
      emit("update-answer", { questionId: draft.question_id, answer: draft.answer });
    });
    if (currentQuestion.value && restored[currentQuestion.value.id]) {
      answerText.value = restored[currentQuestion.value.id];
    }
    draftStatus.value = data.drafts.length ? "saved" : "idle";
  } catch (error) {
    draftStatus.value = "error";
    emit("notice", error.message, "error");
  } finally {
    draftsLoaded.value = true;
  }
}

function scheduleDraftSave() {
  if (draftTimer) {
    window.clearTimeout(draftTimer);
  }
  draftTimer = window.setTimeout(saveCurrentDraft, 650);
}

async function saveCurrentDraft() {
  if (!props.token || !props.session?.session_id || !currentQuestion.value || props.report) {
    return;
  }

  draftStatus.value = "saving";
  try {
    await apiRequest(
      `/interviews/sessions/${encodeURIComponent(props.session.session_id)}/drafts`,
      {
        method: "PUT",
        body: JSON.stringify({
          question_id: currentQuestion.value.id,
          answer: answerText.value,
        }),
      },
      props.token,
    );
    draftStatus.value = answerText.value.trim() ? "saved" : "idle";
  } catch (error) {
    draftStatus.value = "error";
  }
}

function handleStreamEvent(name, event) {
  const data = JSON.parse(event.data);
  emit("stream-event", { name, data });
  if (name === "done") {
    streaming.value = false;
    followUpReady.value = true;
    closeStream();
    emit("notice", "Alex 已完成本题追问");
  }
  if (name === "error") {
    streaming.value = false;
    closeStream();
    emit("notice", data.message || "追问生成失败", "error");
  }
}

function openStream(streamToken) {
  closeStream();
  source = new EventSource(`/interviews/follow-up/stream?token=${encodeURIComponent(streamToken)}`);
  ["trace", "follow_up", "done", "error"].forEach((name) => {
    source.addEventListener(name, (event) => handleStreamEvent(name, event));
  });
  source.onerror = () => {
    if (streaming.value) {
      streaming.value = false;
      emit("notice", "流式连接中断，请重试", "error");
    }
  };
}

async function submitAnswer() {
  const answer = answerText.value.trim();
  if (!currentQuestion.value || !answer) {
    emit("notice", "请先输入回答", "warning");
    return;
  }
  emit("update-answer", { questionId: currentQuestion.value.id, answer });
  streaming.value = true;
  followUpReady.value = false;
  try {
    const data = await apiRequest(
      "/interviews/follow-up/stream-token",
      {
        method: "POST",
        body: JSON.stringify({
          session_id: props.session.session_id,
          question_id: currentQuestion.value.id,
          answer,
        }),
      },
      props.token,
    );
    openStream(data.stream_token);
  } catch (error) {
    streaming.value = false;
    emit("notice", error.message, "error");
  }
}

async function finishInterview() {
  if (!props.session) {
    return;
  }
  const answerList = Object.entries({
    ...props.answers,
    ...(currentQuestion.value && answerText.value.trim()
      ? { [currentQuestion.value.id]: answerText.value.trim() }
      : {}),
  })
    .filter(([, answer]) => answer?.trim())
    .map(([question_id, answer]) => ({ question_id, answer }));
  if (!answerList.length) {
    emit("notice", "请至少完成一道题", "warning");
    return;
  }

  evaluating.value = true;
  try {
    const report = await apiRequest(
      "/interviews/evaluate",
      {
        method: "POST",
        body: JSON.stringify({
          session_id: props.session.session_id,
          job_title: props.session.job_title,
          answers: answerList,
        }),
      },
      props.token,
    );
    emit("report-created", report);
    draftStatus.value = "idle";
    emit("notice", "面试报告已生成");
  } catch (error) {
    emit("notice", error.message, "error");
  } finally {
    evaluating.value = false;
  }
}

function continueInterview() {
  if (isLastQuestion.value) {
    finishInterview();
    return;
  }
  questionIndex.value += 1;
  followUpReady.value = false;
  syncAnswer();
}

function startTimer() {
  timer = window.setInterval(() => {
    if (timeLeft.value > 0) {
      timeLeft.value -= 1;
    }
  }, 1000);
}

watch(() => currentQuestion.value?.id, syncAnswer, { immediate: true });
watch(answerText, () => {
  if (!draftsLoaded.value || !currentQuestion.value || props.report) {
    return;
  }
  scheduleDraftSave();
});
watch(() => props.session?.session_id, restoreDrafts);
onMounted(() => {
  startTimer();
  restoreDrafts();
});
onBeforeUnmount(() => {
  closeStream();
  if (draftTimer) {
    window.clearTimeout(draftTimer);
  }
  if (timer) {
    window.clearInterval(timer);
  }
});
</script>

<template>
  <main class="candidate-room">
    <header class="room-topbar">
      <div class="room-brand">
        <div class="ai-avatar" aria-hidden="true"><span>AI</span><i></i></div>
        <div>
          <div class="room-title">Alex · AI 面试官</div>
          <div class="room-status"><span class="live-dot"></span>正在面试中</div>
        </div>
      </div>
      <div class="room-topbar-center">
        <span class="room-chip">{{ session.job_title }}</span>
        <span class="room-chip room-chip-dark">第 {{ questionIndex + 1 }} 题 / {{ questions.length }}</span>
      </div>
      <div class="room-topbar-actions">
        <button class="room-icon-button" type="button" title="退出面试" @click="$emit('logout')">
          <el-icon><Close /></el-icon>
        </button>
        <div class="candidate-mini-avatar">你</div>
      </div>
    </header>

    <div class="room-body">
      <section class="room-chat">
        <div class="chat-context">
          <div>
            <span class="eyebrow">LIVE INTERVIEW</span>
            <h1>让我们从你的经历开始。</h1>
          </div>
          <span class="context-hint">AI 会根据你的回答继续追问</span>
        </div>

        <div class="conversation" aria-live="polite">
          <article
            v-for="message in conversation"
            :key="message.id"
            :class="['conversation-row', message.role === 'user' ? 'conversation-row-user' : '']"
          >
            <div v-if="message.role === 'ai'" class="message-avatar ai-avatar" aria-hidden="true"><span>AI</span><i></i></div>
            <div class="message-stack">
              <div
                v-if="message.kind === 'typing'"
                class="message-bubble ai-bubble typing-bubble"
                aria-label="AI 正在输入"
              >
                <span></span><span></span><span></span>
              </div>
              <div
                v-else
                :class="[
                  'message-bubble',
                  message.role === 'user' ? 'user-bubble' : 'ai-bubble',
                  message.kind === 'question' ? 'question-bubble' : '',
                  message.kind === 'follow-up' ? 'follow-up-bubble' : '',
                ]"
              >
                {{ message.text }}
              </div>
              <span :class="['message-time', message.role === 'user' ? 'message-time-right' : '']">
                {{ message.time }}
              </span>
            </div>
            <div v-if="message.role === 'user'" class="message-avatar user-avatar">你</div>
          </article>
        </div>

        <div class="answer-composer">
          <div class="composer-label">
            <span>你的回答</span>
            <span>{{ draftStatusText }} · 按 Enter 发送</span>
          </div>
          <div class="composer-box">
            <el-input
              v-model="answerText"
              :rows="3"
              resize="none"
              type="textarea"
              placeholder="用你自己的语言回答，尽量结合具体项目和结果..."
              @keydown.enter.exact.prevent="submitAnswer"
            />
            <div class="composer-actions">
              <span :class="['composer-tip', `draft-${draftStatus}`]">
                <el-icon><DocumentChecked /></el-icon>{{ draftStatusText }}
              </span>
              <el-button
                :loading="streaming"
                class="send-answer-button"
                type="primary"
                @click="submitAnswer"
              >
                {{ streaming ? "Alex 正在思考" : "发送回答" }}
                <el-icon><Position /></el-icon>
              </el-button>
            </div>
          </div>
          <el-button
            v-if="followUpReady && !streaming"
            :loading="evaluating"
            class="continue-button"
            size="large"
            @click="continueInterview"
          >
            {{ isLastQuestion ? "完成面试并查看报告" : "继续下一题" }}
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </section>

      <aside class="room-sidebar">
        <div class="timer-card">
          <div class="timer-label">剩余面试时间</div>
          <strong>{{ timerText }}</strong>
          <div class="timer-track"><span :style="{ width: `${(timeLeft / (45 * 60)) * 100}%` }"></span></div>
        </div>

        <section class="room-side-section">
          <div class="side-section-heading">
            <span>面试进度</span>
            <strong>{{ progressPercent }}%</strong>
          </div>
          <div class="progress-list">
            <div v-for="(stage, index) in stageItems" :key="stage.label" class="progress-item">
              <span :class="['progress-circle', `progress-${stage.state}`]">
                <el-icon v-if="stage.state === 'done'"><Check /></el-icon>
                <template v-else>{{ index + 1 }}</template>
              </span>
              <span :class="['progress-label', stage.state === 'current' ? 'progress-label-current' : '']">
                {{ stage.label }}
              </span>
            </div>
          </div>
        </section>

        <section class="room-side-section signal-section">
          <div class="side-section-heading">
            <span>面试状态</span>
            <span class="signal-live"><i></i>实时</span>
          </div>
          <div class="signal-list">
            <div v-for="signal in liveSignals" :key="signal.label" class="signal-row">
              <span>{{ signal.label }}</span>
              <strong>{{ signal.value }}<small>{{ signal.suffix }}</small></strong>
            </div>
          </div>
        </section>

        <section class="ai-hint-card">
          <div class="ai-hint-heading"><span class="hint-spark">✦</span> Alex 的提示</div>
          <p v-if="streaming">正在根据你的回答生成下一轮追问，请稍候。</p>
          <p v-else-if="currentQuestion">可以从背景、行动和结果三个部分组织这道题的回答。</p>
          <p v-else>完成回答后，这里会显示你的面试反馈。</p>
        </section>

        <section v-if="report" class="report-mini-card">
          <div class="side-section-heading">
            <span>面试结果</span>
            <span class="report-level">{{ report.level }}</span>
          </div>
          <div class="report-score">{{ report.overall_score }}<small>/ 100</small></div>
          <p>你的报告已经生成，可以开始查看优势和改进建议。</p>
          <div class="report-dimension" v-for="item in report.dimensions.slice(0, 3)" :key="item.name">
            <span>{{ item.name }}</span>
            <strong>{{ item.score }}</strong>
            <div><i :style="{ width: `${item.score}%` }"></i></div>
          </div>
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { apiRequest } from "../api/client";
import ReportPanel from "./ReportPanel.vue";
import { useTaskStore } from "../stores/taskStore";

const props = defineProps({
  token: {
    type: String,
    default: "",
  },
  session: {
    type: Object,
    default: null,
  },
  selectedQuestionId: {
    type: String,
    default: "",
  },
  answers: {
    type: Object,
    default: () => ({}),
  },
  streamEvents: {
    type: Array,
    default: () => [],
  },
  report: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits([
  "select-question",
  "update-answer",
  "stream-event",
  "report-created",
  "notice",
]);

const answerText = ref("");
const streaming = ref(false);
const evaluating = ref(false);
const taskStore = useTaskStore();
let source = null;

const selectedQuestion = computed(() => {
  if (!props.session) {
    return null;
  }
  return props.session.questions.find((item) => item.id === props.selectedQuestionId) || null;
});
const answeredCount = computed(() => Object.values(props.answers).filter((item) => item.trim()).length);
const answerList = computed(() =>
  Object.entries(props.answers)
    .filter(([, answer]) => answer.trim())
    .map(([question_id, answer]) => ({ question_id, answer })),
);

watch(
  () => props.selectedQuestionId,
  () => {
    answerText.value = props.answers[props.selectedQuestionId] || "";
  },
  { immediate: true },
);

function saveAnswer(showNotice = true) {
  if (!selectedQuestion.value) {
    emit("notice", "请先选择题目", "warning");
    return;
  }
  emit("update-answer", {
    questionId: selectedQuestion.value.id,
    answer: answerText.value,
  });
  if (showNotice) {
    emit("notice", "回答已保存");
  }
}

function selectQuestion(questionId) {
  saveAnswer(false);
  emit("select-question", questionId);
}

function eventText(event) {
  return event.data.question || event.data.node || event.data.message || "完成";
}

async function generateFollowUpAsync() {
  if (!props.token || !props.session || !selectedQuestion.value) {
    emit("notice", "请先登录并选择面试题", "warning");
    return;
  }
  saveAnswer(false);
  const answer = answerText.value.trim();
  if (!answer) {
    emit("notice", "请先输入当前题回答", "warning");
    return;
  }

  streaming.value = true;
  try {
    const data = await taskStore.generateFollowUpAsync(
      {
        session_id: props.session.session_id,
        question_id: selectedQuestion.value.id,
        answer,
      },
      props.token,
    );
    data.workflow_trace.forEach((node) => emit("stream-event", { name: "trace", data: { node } }));
    data.follow_up_questions.forEach((question) => emit("stream-event", { name: "follow_up", data: { question } }));
    emit("stream-event", { name: "done", data });
    emit("notice", "追问已生成", "success");
  } catch (error) {
    emit("notice", error.message, "error");
  } finally {
    streaming.value = false;
  }
}

async function streamFollowUp() {
  if (!props.token || !props.session || !selectedQuestion.value) {
    emit("notice", "请先登录并选择面试题", "warning");
    return;
  }
  saveAnswer(false);
  const answer = answerText.value.trim();
  if (!answer) {
    emit("notice", "请先输入当前题回答", "warning");
    return;
  }

  streaming.value = true;
  try {
    const data = await apiRequest(
      "/interviews/follow-up/stream-token",
      {
        method: "POST",
        body: JSON.stringify({
          session_id: props.session.session_id,
          question_id: selectedQuestion.value.id,
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

function openStream(streamToken) {
  closeStream();
  source = new EventSource(`/interviews/follow-up/stream?token=${encodeURIComponent(streamToken)}`);
  ["trace", "follow_up", "done", "error"].forEach((name) => {
    source.addEventListener(name, (event) => {
      const data = JSON.parse(event.data);
      emit("stream-event", { name, data });
      if (name === "done" || name === "error") {
        streaming.value = false;
        closeStream();
      }
    });
  });
  source.onerror = () => {
    streaming.value = false;
  };
}

function closeStream() {
  if (source) {
    source.close();
    source = null;
  }
}

async function evaluateAnswers() {
  if (!props.session) {
    emit("notice", "请先创建或选择面试会话", "warning");
    return;
  }
  saveAnswer(false);
  if (!answerList.value.length) {
    emit("notice", "请先保存至少一题回答", "warning");
    return;
  }

  evaluating.value = true;
  try {
    const data = await taskStore.evaluateAsync(
      {
        session_id: props.session.session_id,
        job_title: props.session.job_title,
        answers: answerList.value,
      },
      props.token,
    );
    emit("report-created", data);
  } catch (error) {
    emit("notice", error.message, "error");
  } finally {
    evaluating.value = false;
  }
}

onBeforeUnmount(closeStream);
</script>

<template>
  <section class="workspace-view">
    <el-empty v-if="!session" description="请先创建或选择一场面试" />
    <template v-else>
      <div class="workspace-header">
        <div>
          <el-tag type="primary" effect="plain">{{ session.difficulty }}</el-tag>
          <h2>{{ session.job_title }}</h2>
          <p>{{ session.candidate_summary }}</p>
        </div>
        <div class="workspace-actions">
          <el-statistic title="题目" :value="session.questions.length" />
          <el-statistic title="已答" :value="answeredCount" />
          <el-statistic title="追问" :value="streamEvents.filter((item) => item.name === 'follow_up').length" />
        </div>
      </div>

      <el-row :gutter="18" class="workspace-grid">
        <el-col :lg="7" :xs="24">
          <el-card shadow="never" class="full-height-card">
            <template #header>
              <div class="card-title">
                <span>题目队列</span>
                <el-tag size="small">{{ session.status }}</el-tag>
              </div>
            </template>
            <el-scrollbar height="620px">
              <button
                v-for="question in session.questions"
                :key="question.id"
                :class="['question-row', question.id === selectedQuestionId ? 'active' : '']"
                type="button"
                @click="selectQuestion(question.id)"
              >
                <span>{{ question.id }} / {{ question.question_type }} / {{ question.source }}</span>
                <strong>{{ question.question }}</strong>
              </button>
            </el-scrollbar>
          </el-card>
        </el-col>

        <el-col :lg="10" :xs="24">
          <el-card shadow="never" class="full-height-card answer-card">
            <template #header>
              <div class="card-title">
                <span>候选人回答</span>
                <el-button-group>
                  <el-button @click="saveAnswer()">保存</el-button>
                  <el-button :loading="streaming" type="primary" @click="generateFollowUpAsync">
                    {{ streaming ? `异步追问中 · ${taskStore.activeTask?.progress || 0}%` : "异步追问" }}
                  </el-button>
                  <el-button :disabled="streaming" @click="streamFollowUp">SSE 预览</el-button>
                </el-button-group>
              </div>
            </template>

            <el-alert
              v-if="selectedQuestion"
              :closable="false"
              :title="selectedQuestion.question"
              show-icon
              type="info"
            />
            <el-input v-model="answerText" :rows="10" class="answer-input" resize="vertical" type="textarea" />

            <div class="expected-block" v-if="selectedQuestion?.expected_points?.length">
              <span>期望要点</span>
              <el-tag v-for="point in selectedQuestion.expected_points" :key="point" class="text-tag" effect="plain">
                {{ point }}
              </el-tag>
            </div>

            <el-button :loading="evaluating" class="evaluate-button" size="large" type="success" @click="evaluateAnswers">
              {{ evaluating ? `异步评分中 · ${taskStore.activeTask?.progress || 0}%` : "生成评分报告" }}
            </el-button>
          </el-card>
        </el-col>

        <el-col :lg="7" :xs="24">
          <el-card shadow="never" class="full-height-card">
            <template #header>
              <div class="card-title">
                <span>实时追问事件</span>
                <el-tag size="small" type="warning">SSE</el-tag>
              </div>
            </template>
            <el-empty v-if="!streamEvents.length" description="暂无追问事件" />
            <el-scrollbar v-else height="620px">
              <el-timeline>
                <el-timeline-item
                  v-for="(event, index) in streamEvents"
                  :key="`${event.name}-${index}`"
                  :type="event.name === 'error' ? 'danger' : event.name === 'done' ? 'success' : 'primary'"
                  :timestamp="event.name"
                >
                  {{ eventText(event) }}
                </el-timeline-item>
              </el-timeline>
            </el-scrollbar>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="report-card">
        <template #header>
          <div class="card-title">
            <span>评分报告</span>
            <el-tag :type="report ? 'success' : 'info'">{{ report ? '已生成' : '待生成' }}</el-tag>
          </div>
        </template>
        <ReportPanel :report="report" />
      </el-card>
    </template>
  </section>
</template>

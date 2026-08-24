import { computed, reactive, ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest } from "../api/client";

const INTERNAL_REPORT_STATUSES = new Set(["evaluated", "ai_reported", "reviewed"]);

function normalizeGeneratedSession(data) {
  return {
    ...data,
    status: data.status || "running",
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

export const useSessionStore = defineStore("session", () => {
  const sessions = ref([]);
  const sessionsLoading = ref(false);
  const detailLoading = ref(false);
  const currentSession = ref(null);
  const selectedQuestionId = ref("");
  const answers = reactive({});
  const streamEvents = ref([]);
  const currentReport = computed(() => currentSession.value?.report || null);

  function resetAnswers(nextAnswers = []) {
    Object.keys(answers).forEach((key) => delete answers[key]);
    nextAnswers.forEach((item) => {
      answers[item.question_id] = item.answer;
    });
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

  async function fetchSessions(token) {
    if (!token) {
      sessions.value = [];
      return [];
    }
    sessionsLoading.value = true;
    try {
      const data = await apiRequest("/interviews/sessions", {}, token);
      sessions.value = data.sessions;
      return sessions.value;
    } finally {
      sessionsLoading.value = false;
    }
  }

  async function openSession(sessionId, token, { internalReport = false } = {}) {
    detailLoading.value = true;
    let internalReportError = "";
    try {
      const detail = await apiRequest(`/interviews/sessions/${encodeURIComponent(sessionId)}`, {}, token);
      if (internalReport && (detail.report || INTERNAL_REPORT_STATUSES.has(detail.status))) {
        try {
          detail.report = await apiRequest(
            `/hiring/interview-sessions/${encodeURIComponent(sessionId)}/report`,
            {},
            token,
          );
        } catch (error) {
          internalReportError = error.message;
        }
      }
      setCurrentSession(detail);
      return { detail, internalReportError };
    } finally {
      detailLoading.value = false;
    }
  }

  async function refreshInternalReport(token) {
    const sessionId = currentSession.value?.session_id;
    if (!sessionId) {
      return null;
    }
    const report = await apiRequest(`/hiring/interview-sessions/${encodeURIComponent(sessionId)}/report`, {}, token);
    currentSession.value = {
      ...currentSession.value,
      report,
      overall_score: report.overall_score,
      level: report.level,
    };
    return report;
  }

  function setGeneratedSession(data) {
    setCurrentSession(normalizeGeneratedSession(data));
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

  function addStreamEvent(event) {
    streamEvents.value.push(event);
  }

  function setReport(report, status = "ai_reported") {
    currentSession.value = {
      ...currentSession.value,
      status,
      report,
      overall_score: report.overall_score,
      level: report.level,
      answer_count: Object.keys(answers).length,
    };
  }

  function clearSession() {
    sessions.value = [];
    currentSession.value = null;
    selectedQuestionId.value = "";
    resetAnswers();
    streamEvents.value = [];
  }

  return {
    sessions,
    sessionsLoading,
    detailLoading,
    currentSession,
    selectedQuestionId,
    answers,
    streamEvents,
    currentReport,
    fetchSessions,
    openSession,
    refreshInternalReport,
    setGeneratedSession,
    selectQuestion,
    updateAnswer,
    addStreamEvent,
    setReport,
    clearSession,
  };
});

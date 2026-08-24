import { ref } from "vue";
import { defineStore } from "pinia";
import { apiRequest } from "../api/client";

const POLL_INTERVAL_MS = 700;
const MAX_POLLS = 40;

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export const useTaskStore = defineStore("task", () => {
  const activeTask = ref(null);

  async function createQuestionTask(payload, token) {
    activeTask.value = await apiRequest(
      "/interviews/questions/async",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      token,
    );
    return activeTask.value;
  }

  async function createEvaluationTask(payload, token) {
    activeTask.value = await apiRequest(
      "/interviews/evaluate/async",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      token,
    );
    return activeTask.value;
  }

  async function createFollowUpTask(payload, token) {
    activeTask.value = await apiRequest(
      "/interviews/follow-up/async",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      token,
    );
    return activeTask.value;
  }

  async function pollTask(taskId, token) {
    activeTask.value = await apiRequest(`/interviews/tasks/${encodeURIComponent(taskId)}`, {}, token);
    return activeTask.value;
  }

  async function waitForTaskResult(taskId, token) {
    for (let index = 0; index < MAX_POLLS; index += 1) {
      const task = await pollTask(taskId, token);
      if (task.status === "succeeded") {
        return task.result;
      }
      if (task.status === "failed") {
        throw new Error(task.error || task.message || "异步任务执行失败");
      }
      await delay(POLL_INTERVAL_MS);
    }
    throw new Error("异步任务仍在执行，请稍后刷新任务状态");
  }

  async function generateQuestionsAsync(payload, token) {
    const task = await createQuestionTask(payload, token);
    return waitForTaskResult(task.task_id, token);
  }

  async function evaluateAsync(payload, token) {
    const task = await createEvaluationTask(payload, token);
    return waitForTaskResult(task.task_id, token);
  }

  async function generateFollowUpAsync(payload, token) {
    const task = await createFollowUpTask(payload, token);
    return waitForTaskResult(task.task_id, token);
  }

  return {
    activeTask,
    createQuestionTask,
    createEvaluationTask,
    createFollowUpTask,
    pollTask,
    waitForTaskResult,
    generateQuestionsAsync,
    evaluateAsync,
    generateFollowUpAsync,
  };
});

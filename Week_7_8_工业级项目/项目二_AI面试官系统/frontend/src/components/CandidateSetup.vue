<script setup>
import { reactive, ref } from "vue";
import { useTaskStore } from "../stores/taskStore";

const props = defineProps({
  token: {
    type: String,
    default: "",
  },
});
const emit = defineEmits(["generated", "logout", "notice"]);
const busy = ref(false);
const taskStore = useTaskStore();
const form = reactive({
  jobTitle: "AI 应用开发工程师",
  difficulty: "mid",
  questionCount: 5,
  resumeText:
    "候选人有 FastAPI、LangGraph、RAG、SQLAlchemy 项目经验，做过企业知识库问答、工单流转、JWT 鉴权、SSE 流式输出和 Docker 部署。",
});

async function startInterview() {
  if (form.resumeText.trim().length < 20) {
    emit("notice", "请先填写至少 20 个字的简历或项目经历", "warning");
    return;
  }

  busy.value = true;
  try {
    const data = await taskStore.generateQuestionsAsync(
      {
        resume_text: form.resumeText.trim(),
        job_title: form.jobTitle.trim(),
        difficulty: form.difficulty,
        question_count: Number(form.questionCount),
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
</script>

<template>
  <main class="candidate-setup">
    <header class="candidate-setup-topbar">
      <div class="candidate-brand candidate-brand-dark">
        <span class="candidate-brand-mark">AI</span>
        <span>Interview room</span>
      </div>
      <button class="ghost-link" type="button" @click="$emit('logout')">
        退出登录
        <el-icon><Right /></el-icon>
      </button>
    </header>

    <section class="setup-layout">
      <div class="setup-intro">
        <div class="ai-avatar ai-avatar-large" aria-hidden="true">
          <span>AI</span>
          <i></i>
        </div>
        <p class="eyebrow">准备开始</p>
        <h1>先让 Alex 认识你。</h1>
        <p>
          面试会围绕岗位要求和你的真实经历展开。信息越具体，追问就越接近真实面试。
        </p>
        <div class="setup-meta">
          <span><el-icon><Clock /></el-icon>约 30 - 45 分钟</span>
          <span><el-icon><ChatDotRound /></el-icon>支持实时追问</span>
          <span><el-icon><DataAnalysis /></el-icon>结束后生成报告</span>
        </div>
      </div>

      <section class="setup-panel">
        <div class="setup-panel-heading">
          <div>
            <p class="eyebrow">面试设置</p>
            <h2>告诉我这次面试的方向</h2>
          </div>
          <span class="setup-step">01 / 02</span>
        </div>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="目标岗位">
            <el-input v-model="form.jobTitle" size="large" placeholder="例如：高级前端工程师" />
          </el-form-item>
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
              :rows="8"
              resize="vertical"
              type="textarea"
              placeholder="写下你做过的项目、负责的模块、技术栈和结果..."
            />
          </el-form-item>
          <div class="setup-panel-footer">
            <span>你的内容只用于生成本次面试题。</span>
            <el-button :loading="busy" class="candidate-primary-button" size="large" @click="startInterview">
              {{ busy ? `异步生成中 · ${taskStore.activeTask?.progress || 0}%` : "进入面试间" }}
              <el-icon><Right /></el-icon>
            </el-button>
          </div>
        </el-form>
      </section>
    </section>
  </main>
</template>

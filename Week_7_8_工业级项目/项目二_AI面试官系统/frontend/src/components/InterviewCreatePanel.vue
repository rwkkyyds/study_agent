<script setup>
import { reactive, ref } from "vue";
import { useTaskStore } from "../stores/taskStore";

const props = defineProps({
  token: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["generated", "notice"]);
const busy = ref(false);
const taskStore = useTaskStore();
const form = reactive({
  jobTitle: "AI 应用开发工程师",
  difficulty: "mid",
  questionCount: 5,
  resumeText: "候选人有 FastAPI、LangGraph、RAG、SQLAlchemy 项目经验，做过企业知识库问答、工单流转、JWT 鉴权、SSE 流式输出和 Docker 部署。",
});

async function generateQuestions() {
  if (!props.token) {
    emit("notice", "请先登录", "warning");
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
  <section class="create-view">
    <el-card shadow="never" class="create-card">
      <template #header>
        <div class="card-title">
          <div>
            <span>创建面试</span>
            <small>生成面试会话后进入实时工作台</small>
          </div>
          <el-tag type="primary">New Session</el-tag>
        </div>
      </template>

      <el-steps :active="1" finish-status="success" simple>
        <el-step title="配置岗位" />
        <el-step title="生成题目" />
        <el-step title="实时追问" />
        <el-step title="评分报告" />
      </el-steps>

      <el-form class="create-form" label-position="top">
        <el-row :gutter="18">
          <el-col :md="12" :xs="24">
            <el-form-item label="目标岗位">
              <el-input v-model="form.jobTitle" size="large" />
            </el-form-item>
          </el-col>
          <el-col :md="6" :xs="12">
            <el-form-item label="面试难度">
              <el-select v-model="form.difficulty" size="large">
                <el-option label="Junior" value="junior" />
                <el-option label="Mid" value="mid" />
                <el-option label="Senior" value="senior" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :md="6" :xs="12">
            <el-form-item label="题目数量">
              <el-input-number v-model="form.questionCount" :min="3" :max="8" size="large" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="候选人简历文本">
          <el-input v-model="form.resumeText" :rows="11" resize="vertical" type="textarea" />
        </el-form-item>
      </el-form>

      <div class="create-footer">
        <div>
          <strong>生成后将写入真实面试会话</strong>
          <span>后续列表、看板和报告都从数据库聚合。</span>
        </div>
        <el-button :loading="busy" size="large" type="primary" @click="generateQuestions">
          {{ busy ? `异步生成中 · ${taskStore.activeTask?.progress || 0}%` : "生成面试题" }}
        </el-button>
      </div>
    </el-card>
  </section>
</template>

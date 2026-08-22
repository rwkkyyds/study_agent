<script setup>
import { reactive, ref } from "vue";
import { apiRequest } from "../api/client";

const emit = defineEmits(["logged-in", "notice"]);
const form = reactive({
  username: "candidate@example.com",
  password: "password123",
});
const busy = ref("");

async function submit(mode) {
  const username = form.username.trim();
  if (!username || !form.password) {
    emit("notice", "请输入账号和密码", "warning");
    return;
  }

  busy.value = mode;
  try {
    if (mode === "register") {
      await apiRequest(
        "/auth/register",
        {
          method: "POST",
          body: JSON.stringify({ username, password: form.password }),
        },
        "",
      );
      emit("notice", "账号已创建，请继续登录");
      return;
    }

    const data = await apiRequest(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ username, password: form.password }),
      },
      "",
    );
    emit("logged-in", data.access_token);
  } catch (error) {
    emit("notice", error.message, "error");
  } finally {
    busy.value = "";
  }
}
</script>

<template>
  <main class="candidate-auth">
    <section class="candidate-auth-hero">
      <div class="candidate-brand">
        <span class="candidate-brand-mark">AI</span>
        <span>Interview room</span>
      </div>
      <div class="candidate-hero-copy">
        <p class="eyebrow">AI 面试官系统</p>
        <h1>把一次面试，变成一场真正的对话。</h1>
        <p class="hero-description">
          Alex 会根据你的经历实时提问、追问和评估。没有固定脚本，只有围绕你回答展开的面试。
        </p>
      </div>
      <div class="auth-signal-list">
        <div>
          <span class="signal-index">01</span>
          <span>AI 会记住你的项目上下文</span>
        </div>
        <div>
          <span class="signal-index">02</span>
          <span>每个回答都会触发有针对性的追问</span>
        </div>
        <div>
          <span class="signal-index">03</span>
          <span>结束后得到可执行的能力反馈</span>
        </div>
      </div>
      <div class="auth-hero-footer">
        <span>Powered by structured interview workflow</span>
        <span>JWT · SSE · AI evaluation</span>
      </div>
    </section>

    <section class="candidate-auth-form">
      <div class="auth-form-heading">
        <span class="ai-status-dot"></span>
        <span>Alex 正在等你</span>
      </div>
      <h2>进入面试间</h2>
      <p>登录后即可开始一场专属的 AI 模拟面试。</p>

      <el-form class="candidate-form" label-position="top" @submit.prevent>
        <el-form-item label="邮箱或用户名">
          <el-input v-model="form.username" size="large" autocomplete="username" placeholder="candidate@example.com" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            size="large"
            autocomplete="current-password"
            placeholder="请输入密码"
            show-password
            type="password"
            @keyup.enter="submit('login')"
          />
        </el-form-item>
        <el-button :loading="busy === 'login'" class="candidate-primary-button" size="large" @click="submit('login')">
          开始面试
          <el-icon><Right /></el-icon>
        </el-button>
      </el-form>

      <div class="auth-divider"><span>还没有账号？</span></div>
      <el-button :loading="busy === 'register'" class="candidate-secondary-button" size="large" @click="submit('register')">
        创建候选人账号
      </el-button>
      <p class="auth-note">演示账号：candidate@example.com / password123</p>
    </section>
  </main>
</template>

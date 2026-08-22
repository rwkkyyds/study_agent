<script setup>
import { reactive, ref } from "vue";
import { apiRequest } from "../api/client";

const emit = defineEmits(["logged-in", "notice"]);

const form = reactive({
  username: "candidate@example.com",
  password: "password123",
});
const busy = ref("");

async function register() {
  busy.value = "register";
  try {
    await apiRequest(
      "/auth/register",
      {
        method: "POST",
        body: JSON.stringify({
          username: form.username.trim(),
          password: form.password,
        }),
      },
      "",
    );
    emit("notice", "账号已创建，可以登录");
  } catch (error) {
    emit("notice", error.message, "error");
  } finally {
    busy.value = "";
  }
}

async function login() {
  busy.value = "login";
  try {
    const data = await apiRequest(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({
          username: form.username.trim(),
          password: form.password,
        }),
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
  <section class="auth-layout">
    <div class="auth-copy">
      <el-tag type="success" effect="dark">Enterprise Interview Ops</el-tag>
      <h2>AI 面试管理工作台</h2>
      <p>
        统一管理候选人模拟面试、实时追问、评分报告和面试复盘数据，适合 HR 与技术面试官做流程演示。
      </p>
      <div class="auth-feature-grid">
        <div>
          <strong>JWT 权限</strong>
          <span>用户隔离访问面试数据</span>
        </div>
        <div>
          <strong>SSE 追问</strong>
          <span>实时展示追问生成过程</span>
        </div>
        <div>
          <strong>报告看板</strong>
          <span>评分和风险集中复盘</span>
        </div>
      </div>
    </div>

    <el-card class="auth-card" shadow="never">
      <template #header>
        <div class="card-title">
          <div>
            <span>账号登录</span>
            <small>默认演示账号可直接使用</small>
          </div>
          <el-icon><Lock /></el-icon>
        </div>
      </template>

      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            autocomplete="current-password"
            show-password
            size="large"
            type="password"
          />
        </el-form-item>
      </el-form>

      <div class="auth-actions">
        <el-button :loading="busy === 'register'" size="large" @click="register">
          注册
        </el-button>
        <el-button :loading="busy === 'login'" size="large" type="primary" @click="login">
          登录工作台
        </el-button>
      </div>
    </el-card>
  </section>
</template>

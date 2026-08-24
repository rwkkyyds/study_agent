<script setup>
defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  activeSessionId: {
    type: String,
    default: "",
  },
});

defineEmits(["refresh", "open-session"]);

function statusType(status) {
  return {
    running: "primary",
    evaluating: "warning",
    ai_reported: "success",
    reviewed: "success",
    archived: "info",
    questions_generated: "info",
    follow_up_generated: "warning",
    evaluated: "success",
  }[status] || "info";
}

function statusLabel(status) {
  return {
    running: "面试中",
    evaluating: "AI 评分中",
    ai_reported: "AI 报告完成",
    reviewed: "人工复核完成",
    archived: "已归档",
    questions_generated: "已生成题目",
    follow_up_generated: "已生成追问",
    evaluated: "已评分",
  }[status] || status;
}

function difficultyType(difficulty) {
  return {
    junior: "success",
    mid: "primary",
    senior: "danger",
  }[difficulty] || "info";
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}
</script>

<template>
  <el-card class="sessions-card" shadow="never">
    <template #header>
      <div class="card-title">
        <div>
          <span>面试会话</span>
          <small>真实历史记录，按创建时间倒序展示</small>
        </div>
        <el-button :loading="loading" @click="$emit('refresh')">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="sessions" empty-text="暂无面试会话" height="620" stripe>
      <el-table-column label="岗位 / 候选人摘要" min-width="280">
        <template #default="{ row }">
          <div class="session-title">
            <strong>{{ row.job_title }}</strong>
            <span>{{ row.candidate_summary }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="难度" width="100">
        <template #default="{ row }">
          <el-tag :type="difficultyType(row.difficulty)" effect="plain">{{ row.difficulty }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="题/答/追问" width="120">
        <template #default="{ row }">
          {{ row.question_count }} / {{ row.answer_count }} / {{ row.follow_up_count }}
        </template>
      </el-table-column>
      <el-table-column label="评分" width="110">
        <template #default="{ row }">
          <strong v-if="row.overall_score !== null">{{ row.overall_score }}</strong>
          <span v-else class="muted">待评分</span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="190">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column fixed="right" label="操作" width="120">
        <template #default="{ row }">
          <el-button
            :type="row.session_id === activeSessionId ? 'primary' : 'default'"
            link
            @click="$emit('open-session', row.session_id)"
          >
            查看详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

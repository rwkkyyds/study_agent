<script setup>
import { computed } from "vue";

const props = defineProps({
  sessions: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["create", "open-sessions"]);

const evaluatedSessions = computed(() => props.sessions.filter((item) => item.overall_score !== null));
const averageScore = computed(() => {
  if (!evaluatedSessions.value.length) {
    return 0;
  }
  const total = evaluatedSessions.value.reduce((sum, item) => sum + item.overall_score, 0);
  return Math.round(total / evaluatedSessions.value.length);
});
const followUpCount = computed(() =>
  props.sessions.reduce((sum, item) => sum + item.follow_up_count, 0),
);

const statusChart = computed(() => {
  const counts = props.sessions.reduce((acc, item) => {
    acc[item.status] = (acc[item.status] || 0) + 1;
    return acc;
  }, {});
  return {
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [
      {
        type: "pie",
        radius: ["48%", "72%"],
        data: Object.entries(counts).map(([name, value]) => ({ name, value })),
      },
    ],
  };
});

const scoreChart = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 32, right: 12, top: 28, bottom: 28 },
  xAxis: {
    type: "category",
    data: evaluatedSessions.value.map((item) => item.job_title),
    axisLabel: { interval: 0, width: 80, overflow: "truncate" },
  },
  yAxis: { type: "value", max: 100 },
  series: [
    {
      type: "bar",
      data: evaluatedSessions.value.map((item) => item.overall_score),
      itemStyle: { color: "#2563eb" },
      barMaxWidth: 36,
    },
  ],
}));
</script>

<template>
  <section v-loading="loading" class="dashboard-view">
    <div class="hero-band">
      <div>
        <el-tag type="primary" effect="plain">实时运营概览</el-tag>
        <h2>面试质量与候选人表现看板</h2>
        <p>基于真实面试会话、追问和评分报告聚合，不使用前端样例数据。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="$emit('open-sessions')">查看会话</el-button>
        <el-button type="primary" @click="$emit('create')">创建面试</el-button>
      </div>
    </div>

    <div class="metric-grid">
      <el-card shadow="never">
        <span>总面试数</span>
        <strong>{{ sessions.length }}</strong>
        <small>当前登录用户</small>
      </el-card>
      <el-card shadow="never">
        <span>已评分</span>
        <strong>{{ evaluatedSessions.length }}</strong>
        <small>完成报告生成</small>
      </el-card>
      <el-card shadow="never">
        <span>平均分</span>
        <strong>{{ averageScore }}</strong>
        <small>满分 100</small>
      </el-card>
      <el-card shadow="never">
        <span>追问次数</span>
        <strong>{{ followUpCount }}</strong>
        <small>SSE / 普通追问累计</small>
      </el-card>
    </div>

    <div class="chart-grid">
      <el-card shadow="never">
        <template #header>
          <div class="card-title">
            <span>会话状态分布</span>
            <el-tag size="small">Status</el-tag>
          </div>
        </template>
        <el-empty v-if="!sessions.length" description="暂无会话数据" />
        <v-chart v-else autoresize class="chart-box" :option="statusChart" />
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-title">
            <span>评分趋势</span>
            <el-tag size="small" type="success">Score</el-tag>
          </div>
        </template>
        <el-empty v-if="!evaluatedSessions.length" description="暂无评分报告" />
        <v-chart v-else autoresize class="chart-box" :option="scoreChart" />
      </el-card>
    </div>
  </section>
</template>

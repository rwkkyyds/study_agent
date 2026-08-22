<script setup>
import { computed } from "vue";

const props = defineProps({
  report: {
    type: Object,
    default: null,
  },
});

const dimensionChart = computed(() => {
  const dimensions = props.report?.dimensions || [];
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 14, top: 24, bottom: 36 },
    xAxis: {
      type: "category",
      data: dimensions.map((item) => item.name),
      axisLabel: { interval: 0, width: 70, overflow: "truncate" },
    },
    yAxis: { type: "value", max: 100 },
    series: [
      {
        type: "bar",
        data: dimensions.map((item) => item.score),
        itemStyle: { color: "#0f766e" },
        barMaxWidth: 34,
      },
    ],
  };
});

const radarChart = computed(() => {
  const dimensions = props.report?.dimensions || [];
  return {
    tooltip: {},
    radar: {
      indicator: dimensions.map((item) => ({ name: item.name, max: 100 })),
      radius: "62%",
    },
    series: [
      {
        type: "radar",
        data: [{ value: dimensions.map((item) => item.score), name: "评分" }],
        areaStyle: { color: "rgba(37, 99, 235, 0.16)" },
        lineStyle: { color: "#2563eb" },
      },
    ],
  };
});
</script>

<template>
  <div class="report-panel">
    <el-empty v-if="!report" description="提交评分后生成结构化报告" />
    <template v-else>
      <div class="score-summary">
        <div>
          <span>综合评分</span>
          <strong>{{ report.overall_score }}</strong>
        </div>
        <el-tag size="large" type="success">{{ report.level }}</el-tag>
      </div>

      <el-tabs class="report-tabs">
        <el-tab-pane label="维度图表">
          <div class="report-chart-grid">
            <v-chart autoresize class="chart-box compact" :option="dimensionChart" />
            <v-chart autoresize class="chart-box compact" :option="radarChart" />
          </div>
        </el-tab-pane>
        <el-tab-pane label="报告明细">
          <div class="report-list">
            <el-card shadow="never">
              <template #header>优势</template>
              <el-tag v-for="item in report.strengths" :key="item" class="text-tag" type="success">
                {{ item }}
              </el-tag>
            </el-card>
            <el-card shadow="never">
              <template #header>风险</template>
              <el-tag v-for="item in report.risks" :key="item" class="text-tag" type="danger">
                {{ item }}
              </el-tag>
            </el-card>
            <el-card shadow="never">
              <template #header>学习建议</template>
              <p>{{ report.learning_suggestions.join("；") }}</p>
            </el-card>
            <el-card shadow="never">
              <template #header>追问汇总</template>
              <p>{{ report.follow_up_questions.join("；") }}</p>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

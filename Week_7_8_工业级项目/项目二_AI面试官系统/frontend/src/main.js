import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import VChart from "vue-echarts";
import { createPinia } from "pinia";
import App from "./App.vue";
import "./chartSetup";
import router from "./router";
import "./style.css";

const app = createApp(App);

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.use(ElementPlus);
app.use(createPinia());
app.use(router);
app.component("VChart", VChart);
app.mount("#app");

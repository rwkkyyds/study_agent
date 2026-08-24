import { createRouter, createWebHistory } from "vue-router";
import CandidatePortal from "../views/CandidatePortal.vue";
import ConsolePortal from "../views/ConsolePortal.vue";

function legacyEntryRedirect(to) {
  if (to.query.mode === "console" || to.hash === "#console") {
    return { path: "/console", query: to.query };
  }
  return { path: "/candidate", query: to.query };
}

const router = createRouter({
  history: createWebHistory("/web/"),
  routes: [
    {
      path: "/",
      redirect: legacyEntryRedirect,
    },
    {
      path: "/candidate",
      name: "candidate-portal",
      component: CandidatePortal,
    },
    {
      path: "/console",
      name: "console-portal",
      component: ConsolePortal,
    },
  ],
});

export default router;

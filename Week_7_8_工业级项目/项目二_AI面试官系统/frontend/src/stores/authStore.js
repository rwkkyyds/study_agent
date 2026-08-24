import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { clearStoredToken, getStoredToken, storeToken } from "../api/client";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(getStoredToken());
  const isAuthenticated = computed(() => Boolean(token.value));

  function setToken(accessToken) {
    token.value = accessToken;
    storeToken(accessToken);
  }

  function clearToken() {
    token.value = "";
    clearStoredToken();
  }

  return {
    token,
    isAuthenticated,
    setToken,
    clearToken,
  };
});

import axios from "axios";

const apiBaseUrl = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

const API = axios.create({
  baseURL: apiBaseUrl,
  // Report generation can exceed 90s when Azure retries are involved.
  timeout: 240000,
  headers: {
    "Content-Type": "application/json",
  },
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");

      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export default API;

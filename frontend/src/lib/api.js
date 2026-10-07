import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("lm_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => {
    window.dispatchEvent(new CustomEvent("lm:online"));
    return r;
  },
  (err) => {
    if (err.response && err.response.status === 401 && localStorage.getItem("lm_token")) {
      localStorage.removeItem("lm_token");
      if (!window.location.pathname.includes("/login")) window.location.href = "/login";
    }
    if (!err.response) {
      window.dispatchEvent(new CustomEvent("lm:offline"));
    }
    return Promise.reject(err);
  }
);

export const eur = (n) =>
  new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR" }).format(Number(n || 0));

export const CATEGORY_COLORS = {
  Groceries: "#10B981", "Eating Out": "#F59E0B", Transport: "#6366F1", Shopping: "#EC4899",
  Entertainment: "#8B5CF6", Work: "#0EA5E9", Fitness: "#059669", Health: "#EF4444",
  Travel: "#14B8A6", Subscriptions: "#F97316", Bills: "#64748B", Other: "#94A3B8",
};

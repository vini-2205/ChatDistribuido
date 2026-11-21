import axios from "axios";

export const ACCESS_KEY = "jwt_token";
export const REFRESH_KEY = "jwt_refresh";

// Mesmo host para os dois serviços: o Nginx (ou o setupProxy, em dev) encaminha
// /api/auth/* para o Serviço de Autenticação e /api/chat/* para o Serviço de Chat.
const api = axios.create({
  baseURL: "/api",
});

// Chamado quando a sessão não pode mais ser renovada (registrado pelo AuthContext)
let onSessionExpired = () => {};
export const setOnSessionExpired = (callback) => {
  onSessionExpired = callback;
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Uma única renovação em andamento; requisições que falharem juntas aguardam a mesma
let refreshPromise = null;

export const renovarToken = () => {
  if (!refreshPromise) {
    const refresh = localStorage.getItem(REFRESH_KEY);
    refreshPromise = (refresh
      ? axios.post("/api/auth/refresh/", { refresh })
      : Promise.reject(new Error("Sem refresh token"))
    )
      .then(({ data }) => {
        localStorage.setItem(ACCESS_KEY, data.access);
        if (data.refresh) localStorage.setItem(REFRESH_KEY, data.refresh);
        return data.access;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

// Ao receber 401, renova o token e repete a requisição original
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const ehRotaPublica = ["/auth/login/", "/auth/refresh/", "/auth/registrar/"].includes(original?.url);

    if (error.response?.status !== 401 || !original || original._retry || ehRotaPublica) {
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      const access = await renovarToken();
      original.headers.Authorization = `Bearer ${access}`;
      return api(original);
    } catch (refreshError) {
      onSessionExpired();
      return Promise.reject(error);
    }
  }
);

// Mensagem de erro legível a partir da resposta do DRF
export const mensagemErro = (error, padrao = "Não foi possível concluir a operação.") => {
  const data = error?.response?.data;
  if (!data) return padrao;
  if (typeof data.detail === "string") return data.detail;
  const primeiro = Object.values(data)[0];
  return Array.isArray(primeiro) ? primeiro[0] : padrao;
};

export default api;

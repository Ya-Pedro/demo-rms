import { tokenStorage } from './tokenStorage';

import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const BASE_URL = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

export const tokenStore = {
  getAccess: () => tokenStorage.getAccess(),
  getRefresh: () => tokenStorage.getRefresh(),
  setAccess: (token) => tokenStorage.setAccess(token),
  setRefresh: (token) => tokenStorage.setRefresh(token),
  clear: () => tokenStorage.clear(),
};

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

let onSessionExpiredCallback = null;
export const setSessionExpiredHandler = (handler) => {
  onSessionExpiredCallback = handler;
};

const ERROR_MESSAGES = {
  400: 'Некорректный запрос. Проверьте введённые данные.',
  403: 'У вас недостаточно прав для этого действия.',
  404: 'Запрашиваемый ресурс не найден.',
  409: 'Конфликт данных. Возможно, такая запись уже существует.',
  422: 'Ошибка валидации данных.',
  429: 'Слишком много запросов. Подождите немного и попробуйте снова.',
  500: 'Внутренняя ошибка сервера. Попробуйте позже.',
  502: 'Сервер временно недоступен.',
  503: 'Сервис временно недоступен. Попробуйте позже.',
};

export const getErrorMessage = (error) => {
  if (!error.response) {
    if (error.code === 'ECONNABORTED') return 'Превышено время ожидания запроса.';
    return 'Нет соединения с сервером. Проверьте интернет-подключение.';
  }

  const status = error.response.status;
  const detail = error.response.data?.detail;

  if (status === 401) return null;

  if (detail && typeof detail === 'string') return detail;
  if (detail && Array.isArray(detail)) {
    return detail.map((e) => e.msg || e).join('; ');
  }

  return ERROR_MESSAGES[status] || `Ошибка сервера (${status})`;
};

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

apiClient.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = tokenStore.getRefresh();

      if (!refreshToken) {
        tokenStore.clear();
        if (onSessionExpiredCallback) {
          onSessionExpiredCallback();
        } else {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const resp = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const newAccessToken = resp.data.access_token;
        tokenStore.setAccess(newAccessToken);
        processQueue(null, newAccessToken);

        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        tokenStore.clear();
        if (onSessionExpiredCallback) {
          onSessionExpiredCallback();
        } else {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
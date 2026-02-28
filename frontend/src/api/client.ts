import axios from 'axios';
import { useAuthStore } from '@/store/authStore';
import { getApiBaseUrl, getBackendRoot } from '@/api/baseUrl';

const BASE_URL = getApiBaseUrl();
const BACKEND_ROOT = getBackendRoot();

export const api = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request Interceptor: Add Token
api.interceptors.request.use(
    (config) => {
        const token = useAuthStore.getState().token;
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response Interceptor: Handle Errors (e.g., 401 Logout)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        const status = error.response?.status;
        const detail = error.response?.data?.detail;
        const isInvalidCredentialError =
            status === 401 ||
            (status === 403 && detail === 'Could not validate credentials');

        if (isInvalidCredentialError) {
            // Auto-logout on unauthorized
            useAuthStore.getState().logout();
            // Optional: Redirect to login
            // window.location.href = '/login'; 
        }
        return Promise.reject(error);
    }
);

export function buildBackendUrl(path: string): string {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return BACKEND_ROOT ? `${BACKEND_ROOT}${normalizedPath}` : normalizedPath;
}

export const API_BASE = 'http://localhost:8000/api';

// Базовый fetch с авторизацией
export async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        // Токен истёк или невалиден
        localStorage.removeItem('access_token');
        window.location.href = '/frontend/login.html';
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Для 204 No Content возвращаем null
    if (response.status === 204) return null;
    return response.json();
}

// Удобные обёртки
export const api = {
    get: (endpoint) => apiRequest(endpoint, { method: 'GET' }),
    post: (endpoint, data) => apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    patch: (endpoint, data) => apiRequest(endpoint, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
    delete: (endpoint) => apiRequest(endpoint, { method: 'DELETE' }),
};
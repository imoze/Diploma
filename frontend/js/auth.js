// frontend/js/auth.js
import { api } from './api.js';

export async function login(email, password) {
    try {
        const data = await api.post('/auth/login', { email, password });
        localStorage.setItem('access_token', data.access_token);
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

export async function register(email, username, password) {
    try {
        await api.post('/auth/register', { email, username, password });
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

export function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/frontend/login.html';
}

export async function getCurrentUser() {
    try {
        return await api.get('/users/me/profile');
    } catch (e) {
        return null;
    }
}

export function isAuthenticated() {
    return !!localStorage.getItem('access_token');
}

// Редирект, если уже авторизован (для страниц логина/регистрации)
export function redirectIfAuthenticated() {
    if (isAuthenticated()) {
        window.location.href = '/frontend/index.html';
    }
}

// Редирект, если НЕ авторизован (для защищённых страниц)
export function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/frontend/login.html';
    }
}
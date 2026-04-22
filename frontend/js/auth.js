import { api } from './api.js';

export async function login(email, password) {
    const data = await api.post('/auth/login', { email, password });
    localStorage.setItem('access_token', data.access_token);
    return data;
}

export async function register(email, username, password) {
    await api.post('/auth/register', { email, username, password });
    // После регистрации нужно подтверждение email, но для простоты пока так
}

export function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login.html';
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
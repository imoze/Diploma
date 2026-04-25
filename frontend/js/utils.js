// Форматирование времени из секунд в MM:SS
export function formatTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Генерирует data URL плейсхолдера обложки на основе строки-идентификатора
 * @param {string} seed - название трека/плейлиста + id
 * @param {number} size - размер в пикселях
 * @returns {string} data:image/png;base64...
 */
export function generateCoverPlaceholder(seed, size = 250) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');

    // Простой хэш для детерминированности
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
        hash = ((hash << 5) - hash) + seed.charCodeAt(i);
        hash |= 0;
    }

    // Градиент
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    const hue1 = Math.abs(hash % 360);
    const hue2 = (hue1 + 40) % 360;
    gradient.addColorStop(0, `hsl(${hue1}, 30%, 15%)`);
    gradient.addColorStop(1, `hsl(${hue2}, 40%, 10%)`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);

    // Несколько абстрактных фигур
    ctx.globalAlpha = 0.3;
    for (let i = 0; i < 3; i++) {
        const x = (hash * (i+1)) % size;
        const y = (hash * (i+3)) % size;
        const r = Math.abs((hash * (i+5)) % (size/2) + 20);
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fillStyle = `hsl(${(hue1 + i*20) % 360}, 50%, 20%)`;
        ctx.fill();
    }

    // Текст (первые буквы)
    ctx.globalAlpha = 0.8;
    ctx.font = `bold ${size/6}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const text = seed.slice(0, 2).toUpperCase();
    ctx.fillText(text, size/2, size/2);

    return canvas.toDataURL();
}

export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
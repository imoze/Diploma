import { api, API_BASE } from './api.js';
import { formatTime, generateCoverPlaceholder } from './utils.js';

class Player {
    constructor() {
        this.audio = new Audio();
        this.currentTrack = null;
        this.isPlaying = false;
        this.queue = [];
        this.volume = 1.0;

        // Элементы DOM
        this.bar = document.getElementById('player-bar');
        this.playBtn = document.getElementById('player-play');
        this.nextBtn = document.getElementById('player-next');
        this.likeBtn = document.getElementById('player-like');
        this.waveBtn = document.getElementById('player-wave');
        this.expandBtn = document.getElementById('player-expand');
        this.progressBar = document.getElementById('player-progress');
        this.currentTimeEl = document.getElementById('player-current-time');
        this.durationEl = document.getElementById('player-duration');
        this.trackNameEl = document.getElementById('player-track-name');
        this.artistNameEl = document.getElementById('player-artist-name');
        this.coverEl = document.getElementById('player-cover');

        this.initEvents();
    }

    initEvents() {
        this.playBtn.addEventListener('click', () => this.togglePlay());
        this.nextBtn.addEventListener('click', () => this.nextTrack());
        this.likeBtn.addEventListener('click', () => this.toggleLike());
        this.waveBtn.addEventListener('click', () => this.openWaveView());
        this.expandBtn.addEventListener('click', () => this.openFullscreenPlayer());

        this.progressBar.addEventListener('input', () => {
            const duration = this.audio.duration;
            if (!isFinite(duration)) return;
            const time = (this.progressBar.value / 100) * duration;
            this.audio.currentTime = time;
        });

        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('loadedmetadata', () => {
            this.durationEl.textContent = formatTime(this.audio.duration);
            this.progressBar.max = 100;
        });
        this.audio.addEventListener('play', () => {
            this.isPlaying = true;
            this.playBtn.innerHTML = this.getPauseIcon();
        });
        this.audio.addEventListener('pause', () => {
            this.isPlaying = false;
            this.playBtn.innerHTML = this.getPlayIcon();
        });
        this.audio.addEventListener('ended', () => this.nextTrack());

        this.audio.addEventListener('loadedmetadata', () => {
            const audioDuration = this.audio.duration;
            if (isFinite(audioDuration) && audioDuration > 0) {
                this.durationEl.textContent = formatTime(audioDuration);
            } else if (this.currentTrack?.duration) {
                this.durationEl.textContent = formatTime(this.currentTrack.duration);
            } else {
                this.durationEl.textContent = '0:00';
            }
            this.progressBar.max = 100;
        }); 

        this.progressBar.addEventListener('input', () => {
            const duration = isFinite(this.audio.duration) && this.audio.duration > 0
                ? this.audio.duration
                : (this.currentTrack?.duration || 0);
            if (!duration) return;

            const time = (this.progressBar.value / 100) * duration;
            this.audio.currentTime = time;
        });
    }

    // Иконки (можно использовать текст или SVG)
    getPlayIcon() { return '▶'; }
    getPauseIcon() { return '⏸'; }

    async loadTrack(trackId) {
        try {
            const track = await api.get(`/tracks/${trackId}`);
            this.currentTrack = track;

            // Формируем URL стрима
            const streamUrl = `${API_BASE}/tracks/${trackId}/stream`;
            this.audio.src = streamUrl;
            this.audio.load();

            // Обновляем UI плеера
            this.trackNameEl.textContent = track.name;
            const artists = track.artists.map(a => a.name).join(', ');
            this.artistNameEl.textContent = artists || 'Unknown Artist';
            // Для обложки пока ставим плейсхолдер
            this.coverEl.src = generateCoverPlaceholder(`${track.name}${track.id}`, 64);

            const durationFromApi = track.duration || 0;
            this.durationEl.textContent = formatTime(durationFromApi);
            this.progressBar.max = 100;

            // Проверяем лайк (можно добавить эндпоинт для проверки)
            this.updateLikeButtonState();

            this.play();

            this.bar.style.display = 'flex';
        } catch (e) {
            console.error('Failed to load track', e);
        }
    }

    play() {
        this.audio.play();
    }

    pause() {
        this.audio.pause();
    }

    togglePlay() {
        if (this.isPlaying) this.pause();
        else this.play();
    }

    nextTrack() {
        // Пока просто заглушка
        if (this.queue.length > 0) {
            const nextId = this.queue.shift();
            this.loadTrack(nextId);
        }
    }

    updateProgress() {
        const duration = isFinite(this.audio.duration) && this.audio.duration > 0 
            ? this.audio.duration 
            : (this.currentTrack?.duration || 0);
        if (!duration) return;

        const percent = (this.audio.currentTime / duration) * 100;
        this.progressBar.value = percent;
        this.currentTimeEl.textContent = formatTime(this.audio.currentTime);
    }

    async toggleLike() {
        if (!this.currentTrack) return;
        try {
            await api.post(`/tracks/${this.currentTrack.id}/like`);
            this.likeBtn.classList.add('liked');
        } catch (e) {
            // Если уже лайкнут, удаляем
            if (e.message.includes('already')) {
                await api.delete(`/tracks/${this.currentTrack.id}/like`);
                this.likeBtn.classList.remove('liked');
            }
        }
    }

    updateLikeButtonState() {
        // Можно реализовать проверку через API
        // Пока оставим как есть
    }

    openWaveView() {
        if (!this.currentTrack) return;
        // Откроем страницу или модалку с поиском похожих
        window.location.href = `/pages/similar.html?track=${this.currentTrack.id}`;
    }

    openFullscreenPlayer() {
        // Реализуем позже
        alert('Fullscreen player coming soon');
    }
}

// Экспортируем синглтон
export const player = new Player();
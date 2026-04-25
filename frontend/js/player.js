import { api, API_BASE } from './api.js';
import { formatTime, generateCoverPlaceholder } from './utils.js';
import { WaveVisualizer } from './waveAnimation.js';

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
        this.fullscreenOverlay = null;
        this.waveCanvas = null;
        this.waveVisualizer = null;
        this.similarTracksContainer = null;

        this.initEvents();
        this.initFullscreenPlayer();
    }

    initEvents() {
        this.playBtn.addEventListener('click', () => this.togglePlay());
        this.nextBtn.addEventListener('click', () => this.nextTrack());
        this.likeBtn.addEventListener('click', () => this.toggleLike());
        this.waveBtn.addEventListener('click', () => this.openWaveView());
        this.expandBtn.addEventListener('click', () => this.openFullscreenPlayer());

        this.progressBar.addEventListener('input', () => {
            const duration = this.audio.duration;
            if (duration && isFinite(duration) && duration > 0) {
                const newTime = (this.progressBar.value / 100) * duration;
                this.audio.currentTime = newTime;
            }
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

            if (this.fullscreenOverlay && this.fullscreenOverlay.style.display === 'flex') {
                this.openFullscreenPlayer(); // обновит данные
            }

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

    initFullscreenPlayer() {
        // Создаём overlay, если его нет
        if (document.getElementById('fullscreen-player-overlay')) return;
        const overlay = document.createElement('div');
        overlay.id = 'fullscreen-player-overlay';
        overlay.className = 'fullscreen-player';
        overlay.innerHTML = `
            <div class="fullscreen-player-content">
                <div class="fullscreen-header">
                    <button class="fullscreen-close" id="fullscreen-close">✕</button>
                    <div class="fullscreen-track-info">
                        <span id="fullscreen-track-name"></span>
                        <span id="fullscreen-artist-name"></span>
                    </div>
                </div>
                <canvas id="wave-canvas" class="wave-canvas"></canvas>
                <div id="uv-index-display" class="uv-index">—</div>
                <div class="fullscreen-controls">
                    <div class="progress-container">
                        <span id="fullscreen-current-time">0:00</span>
                        <input type="range" id="fullscreen-progress" min="0" max="100" value="0">
                        <span id="fullscreen-duration">0:00</span>
                    </div>
                    <div class="control-buttons">
                        <button id="fullscreen-play">▶</button>
                        <button id="fullscreen-next">⏭</button>   <!-- новая кнопка -->
                        <button id="fullscreen-wave-action">🌊 Найти совпадения</button>
                        <button id="fullscreen-like">❤️</button>
                    </div>
                </div>
                <div id="similar-tracks-list" class="similar-tracks-list" style="display: none;"></div>
            </div>
        `;
        document.body.appendChild(overlay);
        this.fullscreenOverlay = overlay;
        this.waveCanvas = document.getElementById('wave-canvas');
        this.waveVisualizer = new WaveVisualizer(this.waveCanvas);
        
        // Привязка событий
        document.getElementById('fullscreen-close').addEventListener('click', () => this.closeFullscreen());
        document.getElementById('fullscreen-play').addEventListener('click', () => this.togglePlay());
        document.getElementById('fullscreen-next').addEventListener('click', () => this.nextTrack());
        document.getElementById('fullscreen-wave-action').addEventListener('click', () => this.findSimilarTracks());
        document.getElementById('fullscreen-like').addEventListener('click', () => this.toggleLike());
        const flplayBtn = document.getElementById('fullscreen-play');
        this.audio.addEventListener('play', () => {
            this.isPlaying = true;
            flplayBtn.textContent = this.getPauseIcon();
        });
        this.audio.addEventListener('pause', () => {
            this.isPlaying = false;
            flplayBtn.textContent = this.getPlayIcon();
        });

        const progressBar = document.getElementById('fullscreen-progress');
        progressBar.addEventListener('input', (e) => {
            const duration = this.audio.duration;
            if (duration && isFinite(duration) && duration > 0) {
                const newTime = (progressBar.value / 100) * duration;
                this.audio.currentTime = newTime;
            }
        });
        
        // Синхронизация с основным плеером
        this.audio.addEventListener('timeupdate', () => this.updateFullscreenProgress());
        this.audio.addEventListener('loadedmetadata', () => {
            document.getElementById('fullscreen-duration').textContent = formatTime(this.audio.duration || this.currentTrack?.duration || 0);
        });
        
        // Закрытие по Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.fullscreenOverlay.style.display === 'flex') {
                this.closeFullscreen();
            }
        });
    }

    openFullscreenPlayer() {
        if (!this.currentTrack) return;
        this.fullscreenOverlay.style.display = 'flex';

        document.getElementById('fullscreen-track-name').textContent = this.currentTrack.name;
        const artists = this.currentTrack.artists?.map(a => a.name).join(', ') || 'Unknown';
        document.getElementById('fullscreen-artist-name').textContent = artists;
        document.getElementById('fullscreen-like').classList.toggle('liked', this.isLiked);
        
        document.getElementById('fullscreen-play').innerHTML = this.isPlaying ? '⏸' : '▶';
        
        
        let duration = 0;
        if (this.audio.duration && isFinite(this.audio.duration) && this.audio.duration > 0) {
            duration = this.audio.duration;
        } else if (this.currentTrack?.duration && this.currentTrack.duration > 0) {
            duration = this.currentTrack.duration;
        }
        document.getElementById('fullscreen-duration').textContent = formatTime(duration);
        
        // Прогресс и текущее время
        const currentTime = this.audio.currentTime || 0;
        const progressPercent = duration ? (currentTime / duration) * 100 : 0;
        document.getElementById('fullscreen-progress').value = progressPercent;
        document.getElementById('fullscreen-current-time').textContent = formatTime(currentTime);
        
        // Обновление прогресса
        this.updateFullscreenProgress();
        
        // Запуск визуализации волны
        this.updateWaveVisualization();
        
        // Скрываем список похожих треков при открытии
        document.getElementById('similar-tracks-list').style.display = 'none';
        document.getElementById('uv-index-display').textContent = '—';
    }

    closeFullscreen() {
        this.fullscreenOverlay.style.display = 'none';
        this.waveVisualizer.stopAnimation();
    }

    updateFullscreenProgress() {
        if (!this.currentTrack) return;
        
        // Получаем актуальную длительность
        let duration = 0;
        if (this.audio.duration && isFinite(this.audio.duration) && this.audio.duration > 0) {
            duration = this.audio.duration;
        } else if (this.currentTrack?.duration && this.currentTrack.duration > 0) {
            duration = this.currentTrack.duration;
        }
        
        const currentTime = this.audio.currentTime || 0;
        
        if (duration > 0) {
            const percent = (currentTime / duration) * 100;
            document.getElementById('fullscreen-progress').value = percent;
        }
        document.getElementById('fullscreen-current-time').textContent = formatTime(currentTime);
        
        // Обновляем длительность на случай, если audio.duration стал известен позже
        if (duration > 0) {
            document.getElementById('fullscreen-duration').textContent = formatTime(duration);
        }
    }

    async updateWaveVisualization() {
        if (!this.currentTrack) return;
        try {
            // Получаем feature_vector трека (если есть)
            const trackData = await api.get(`/tracks/${this.currentTrack.id}`);
            const vector = trackData.feature_vector;
            const params = this.waveVisualizer.generateParams(vector);
            if (!this.waveVisualizer.currentParams) {
                this.waveVisualizer.startAnimation(params);
            } else {
                this.waveVisualizer.morphTo(params);
            }
        } catch (e) {
            console.warn('Could not load feature vector, using fallback');
            const params = this.waveVisualizer.generateParams(null);
            this.waveVisualizer.startAnimation(params);
        }
    }

    async findSimilarTracks() {
        if (!this.currentTrack) return;
        const listContainer = document.getElementById('similar-tracks-list');
        listContainer.innerHTML = '<div class="loading-dots">Поиск совпадений...</div>';
        listContainer.style.display = 'block';
        
        try {
            const similar = await api.get(`/tracks/${this.currentTrack.id}/similar?limit=10`);
            const maxSimilarity = similar.length ? Math.max(...similar.map(t => t.similarity || 0)) : 0;
            document.getElementById('uv-index-display').textContent = maxSimilarity ? `UV ${Math.round(maxSimilarity)}` : '—';

            const html = similar.map(t => {
                const artists = t.artists?.map(a => a.name).join(', ') || '';
                const similarity = t.similarity ? `${Math.round(t.similarity)}%` : '';
                return `
                    <div class="similar-track-item" data-id="${t.id}">
                        <div class="similar-track-info">
                            <span class="similar-track-name">${t.name}</span>
                            <span class="similar-track-artists">${artists}</span>
                        </div>
                        <span class="similar-track-uv">${similarity}</span>
                        <button class="play-similar-btn">▶</button>
                    </div>
                `;
            }).join('');
            listContainer.innerHTML = html || '<div>Совпадений не найдено</div>';
            
            // Обработчики воспроизведения
            listContainer.querySelectorAll('.similar-track-item').forEach(item => {
                const playBtn = item.querySelector('.play-similar-btn');
                playBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const trackId = item.dataset.id;
                    this.loadTrack(trackId);
                });
                item.addEventListener('click', () => {
                    const trackId = item.dataset.id;
                    this.loadTrack(trackId);
                });
            });
        } catch (e) {
            listContainer.innerHTML = '<div class="error">Ошибка загрузки</div>';
            console.error(e);
        }
    }
}

// Экспортируем синглтон
export const player = new Player();
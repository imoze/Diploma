// waveAnimation.js
export class WaveVisualizer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.width = canvas.width;
        this.height = canvas.height;
        this.animationFrame = null;
        this.currentParams = null;
        this.targetParams = null;
        this.morphStart = null;
        this.morphDuration = 800; // ms
    }

    // Генерирует параметры синусоид на основе вектора или хэша
    generateParams(featureVector) {
        // Если вектор отсутствует, используем случайный seed
        const seed = featureVector ? featureVector.reduce((a,b) => a+b, 0) : Math.random() * 1000;
        const pseudoRandom = (s) => {
            let x = Math.sin(s) * 10000;
            return x - Math.floor(x);
        };
        // 3-5 волн
        const count = 3 + Math.floor(pseudoRandom(seed) * 3);
        const waves = [];
        for (let i = 0; i < count; i++) {
            waves.push({
                amplitude: 20 + pseudoRandom(seed + i) * 60,
                frequency: 0.005 + pseudoRandom(seed + i*2) * 0.02,
                phase: pseudoRandom(seed + i*3) * Math.PI * 2,
                speed: 0.5 + pseudoRandom(seed + i*4) * 2,
                color: `rgba(138, 92, 255, ${0.3 + pseudoRandom(seed + i*5)*0.5})`
            });
        }
        return waves;
    }

    // Отрисовка волны с заданными параметрами
    draw(params, timeOffset = 0) {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.ctx.lineWidth = 2;
        
        for (const w of params) {
            this.ctx.beginPath();
            this.ctx.strokeStyle = w.color;
            const phaseShift = timeOffset * w.speed;
            for (let x = 0; x < this.width; x++) {
                const y = this.height/2 + 
                    w.amplitude * Math.sin(x * w.frequency + w.phase + phaseShift) +
                    (w.amplitude * 0.3) * Math.sin(x * w.frequency * 2.3 + w.phase * 1.5); // гармоника
                if (x === 0) this.ctx.moveTo(x, y);
                else this.ctx.lineTo(x, y);
            }
            this.ctx.stroke();
        }
    }

    // Запуск анимации (постоянное движение фазы)
    startAnimation(params) {
        this.currentParams = params;
        let startTime = performance.now();
        const animate = (now) => {
            const elapsed = (now - startTime) / 1000; // секунды
            this.draw(this.currentParams, elapsed);
            this.animationFrame = requestAnimationFrame(animate);
        };
        this.animationFrame = requestAnimationFrame(animate);
    }

    // Остановка анимации
    stopAnimation() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }

    // Морфинг между двумя наборами параметров
    morphTo(newParams, onComplete) {
        this.stopAnimation();
        const oldParams = this.currentParams || this.generateParams(null);
        this.targetParams = newParams;
        
        const startTime = performance.now();
        const duration = this.morphDuration;
        
        const interpolate = (oldArr, newArr, t) => {
            // Если разное количество волн, дополняем нулевыми
            const maxLen = Math.max(oldArr.length, newArr.length);
            const result = [];
            for (let i = 0; i < maxLen; i++) {
                const oldW = oldArr[i] || { amplitude:0, frequency:0, phase:0, speed:0, color: 'rgba(138,92,255,0)' };
                const newW = newArr[i] || { amplitude:0, frequency:0, phase:0, speed:0, color: 'rgba(138,92,255,0)' };
                result.push({
                    amplitude: oldW.amplitude * (1-t) + newW.amplitude * t,
                    frequency: oldW.frequency * (1-t) + newW.frequency * t,
                    phase: oldW.phase * (1-t) + newW.phase * t,
                    speed: oldW.speed * (1-t) + newW.speed * t,
                    color: this.interpolateColor(oldW.color, newW.color, t)
                });
            }
            return result;
        };
        
        const animateMorph = (now) => {
            const elapsed = now - startTime;
            const t = Math.min(elapsed / duration, 1);
            const interParams = interpolate.call(this, oldParams, newParams, t);
            this.draw(interParams, 0); // без смещения фазы во время морфинга
            if (t < 1) {
                this.animationFrame = requestAnimationFrame(animateMorph);
            } else {
                this.currentParams = newParams;
                this.startAnimation(newParams);
                if (onComplete) onComplete();
            }
        };
        this.animationFrame = requestAnimationFrame(animateMorph);
    }

    interpolateColor(c1, c2, t) {
        // простая интерполяция для rgba
        const parse = (c) => c.match(/[\d.]+/g).map(Number);
        const a = parse(c1);
        const b = parse(c2);
        const r = Math.round(a[0]*(1-t) + b[0]*t);
        const g = Math.round(a[1]*(1-t) + b[1]*t);
        const bb = Math.round(a[2]*(1-t) + b[2]*t);
        const alpha = a[3]*(1-t) + b[3]*t;
        return `rgba(${r}, ${g}, ${bb}, ${alpha})`;
    }

    resize(width, height) {
        this.width = width;
        this.height = height;
        this.canvas.width = width;
        this.canvas.height = height;
        if (this.currentParams) {
            this.draw(this.currentParams, 0);
        }
    }
}
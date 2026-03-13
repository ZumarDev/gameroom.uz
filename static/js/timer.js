class SessionTimer {
    constructor() {
        this.timers = new Map();
        this.intervals = new Map();
        this.fetchIntervalMs = 5000; // reduce server load: fetch at most every 5s per session
        this.init();
    }

    init() {
        // Find all timer elements on the page
        document.querySelectorAll('.timer, .timer-mini').forEach(timerEl => {
            const sessionId = timerEl.dataset.sessionId;
            const sessionType = timerEl.dataset.sessionType;
            const duration = timerEl.dataset.duration;
            
        this.timers.set(sessionId, {
            element: timerEl,
            sessionType: sessionType,
            duration: duration ? parseInt(duration) : null,
            lastFetchAt: 0,
            cachedData: null
        });
            
            this.startTimer(sessionId);
        });
    }

    startTimer(sessionId) {
        const timer = this.timers.get(sessionId);
        if (!timer) return;

        // Clear any existing interval
        if (this.intervals.has(sessionId)) {
            clearInterval(this.intervals.get(sessionId));
        }

        // Update timer immediately
        this.updateTimer(sessionId);

        // Set up interval to update every second
        const intervalId = setInterval(() => {
            this.updateTimer(sessionId);
        }, 1000);

        this.intervals.set(sessionId, intervalId);
    }

    async updateTimer(sessionId) {
        const timer = this.timers.get(sessionId);
        if (!timer) return;

        // Skip network work while tab is hidden; timers will catch up on focus
        if (document.visibilityState === 'hidden') {
            return;
        }

        try {
            const nowMs = Date.now();
            const shouldFetch = !timer.cachedData || (nowMs - timer.lastFetchAt) >= this.fetchIntervalMs;

            let data = timer.cachedData;
            if (shouldFetch) {
                const response = await fetch(`/api/session_time/${sessionId}`);
                data = await response.json();
                timer.cachedData = data;
                timer.lastFetchAt = nowMs;
            } else if (data) {
                const elapsedSinceFetch = Math.floor((nowMs - timer.lastFetchAt) / 1000);
                data = { ...data };
                if (typeof data.elapsed_seconds === 'number') {
                    data.elapsed_seconds = data.elapsed_seconds + elapsedSinceFetch;
                }
                if (typeof data.remaining_seconds === 'number' && timer.sessionType === 'fixed') {
                    data.remaining_seconds = Math.max(0, data.remaining_seconds - elapsedSinceFetch);
                }
            }
            
            const timeDisplay = timer.element.querySelector('.time-display');
            
            if (data.expired) {
                timeDisplay.innerHTML = '<span class="text-danger">VAQT TUGADI</span>';
                timeDisplay.parentElement.classList.add('text-danger');
                this.stopTimer(sessionId);
                
                // Auto-refresh the page after a few seconds
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
                
                return;
            }

            if (timer.sessionType === 'fixed') {
                // Show remaining time for fixed sessions (countdown)
                const remainingTime = this.formatTime(data.remaining_seconds);
                const isMini = timer.element.classList.contains('timer-mini');
                timeDisplay.innerHTML = isMini
                    ? `<span class="fw-semibold">${remainingTime}</span> <span class="text-muted">qoldi</span>`
                    : `<div>
                        <span class="text-warning d-block fs-4 fw-bold">${remainingTime}</span>
                        <small class="text-muted">qoldi</small>
                    </div>`;
                
                // Update the session price display in real-time for fixed sessions
                const sessionPriceEl = document.getElementById(`session-price-${sessionId}`);
                const totalPriceEl = document.getElementById(`total-price-${sessionId}`);
                if (sessionPriceEl && data.current_cost) {
                    sessionPriceEl.textContent = `${Math.round(data.current_cost).toLocaleString()} som`;
                }
                if (totalPriceEl && data.total_current) {
                    totalPriceEl.textContent = `${Math.round(data.total_current).toLocaleString()} som`;
                }
                
                // Add warning classes when time is running low
                if (data.remaining_seconds <= 300) { // 5 minutes
                    timeDisplay.innerHTML = isMini
                        ? `<span class="text-danger fw-semibold">${remainingTime}</span> <span class="text-danger">qoldi!</span>`
                        : `<div>
                            <span class="text-danger d-block fs-4 fw-bold">${remainingTime}</span>
                            <small class="text-danger">qoldi!</small>
                        </div>`;
                    timeDisplay.parentElement.classList.add('text-danger');
                } else if (data.remaining_seconds <= 600) { // 10 minutes
                    timeDisplay.innerHTML = isMini
                        ? `<span class="text-warning fw-semibold">${remainingTime}</span> <span class="text-warning">qoldi</span>`
                        : `<div>
                            <span class="text-warning d-block fs-4 fw-bold">${remainingTime}</span>
                            <small class="text-warning">qoldi</small>
                        </div>`;
                    timeDisplay.parentElement.classList.add('text-warning');
                }
            } else {
                // Show elapsed time for VIP sessions (counting up)
                const elapsedTime = this.formatTime(data.elapsed_seconds);
                const isMini = timer.element.classList.contains('timer-mini');
                timeDisplay.innerHTML = isMini
                    ? `<span class="fw-semibold">${elapsedTime}</span> <span class="text-muted">VIP</span>`
                    : `<div>
                        <span class="text-info d-block fs-4 fw-bold">${elapsedTime}</span>
                        <small class="text-success">VIP seans</small>
                    </div>`;
                
                // Update the session price display in real-time for VIP sessions
                const sessionPriceEl = document.getElementById(`session-price-${sessionId}`);
                const totalPriceEl = document.getElementById(`total-price-${sessionId}`);
                if (sessionPriceEl && data.current_cost) {
                    sessionPriceEl.textContent = `${Math.round(data.current_cost).toLocaleString()} som`;
                }
                if (totalPriceEl && data.total_current) {
                    totalPriceEl.textContent = `${Math.round(data.total_current).toLocaleString()} som`;
                }
            }
            
        } catch (error) {
            console.error('Error updating timer:', error);
            const timeDisplay = timer.element.querySelector('.time-display');
            timeDisplay.innerHTML = '<span class="text-muted">Error</span>';
        }
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }

    stopTimer(sessionId) {
        if (this.intervals.has(sessionId)) {
            clearInterval(this.intervals.get(sessionId));
            this.intervals.delete(sessionId);
        }
    }

    stopAllTimers() {
        this.intervals.forEach((intervalId) => {
            clearInterval(intervalId);
        });
        this.intervals.clear();
    }
}

// Initialize timers when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.sessionTimer = new SessionTimer();
});

// Clean up timers when page is unloaded
window.addEventListener('beforeunload', function() {
    if (window.sessionTimer) {
        window.sessionTimer.stopAllTimers();
    }
});

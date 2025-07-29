class SessionTimer {
    constructor() {
        this.timers = new Map();
        this.intervals = new Map();
        this.init();
    }

    init() {
        // Find all timer elements on the page
        document.querySelectorAll('.timer').forEach(timerEl => {
            const sessionId = timerEl.dataset.sessionId;
            const sessionType = timerEl.dataset.sessionType;
            const duration = timerEl.dataset.duration;
            
            this.timers.set(sessionId, {
                element: timerEl,
                sessionType: sessionType,
                duration: duration ? parseInt(duration) : null
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

        try {
            const response = await fetch(`/api/session_time/${sessionId}`);
            const data = await response.json();
            
            const timeDisplay = timer.element.querySelector('.time-display');
            
            if (data.expired) {
                timeDisplay.innerHTML = '<span class="text-danger">EXPIRED</span>';
                timeDisplay.parentElement.classList.add('text-danger');
                this.stopTimer(sessionId);
                
                // Auto-refresh the page after a few seconds
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
                
                return;
            }

            if (timer.sessionType === 'fixed') {
                // Show remaining time for fixed sessions
                const remainingTime = this.formatTime(data.remaining_seconds);
                timeDisplay.innerHTML = `<span class="text-warning">${remainingTime} left</span>`;
                
                // Add warning classes when time is running low
                if (data.remaining_seconds <= 300) { // 5 minutes
                    timeDisplay.innerHTML = `<span class="text-danger">${remainingTime} left</span>`;
                    timeDisplay.parentElement.classList.add('text-danger');
                } else if (data.remaining_seconds <= 600) { // 10 minutes
                    timeDisplay.parentElement.classList.add('text-warning');
                }
            } else {
                // Show elapsed time for VIP sessions
                const elapsedTime = this.formatTime(data.elapsed_seconds);
                timeDisplay.innerHTML = `<span class="text-info">${elapsedTime} elapsed</span>`;
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

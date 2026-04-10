class App {
    constructor() {
        this.ws = null;
        this.wsStatus = document.getElementById('wsStatus');
        this.chatHistory = document.getElementById('chatHistory');
        this.textInput = document.getElementById('textInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.recordBtn = document.getElementById('recordBtn');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.visionDot = document.querySelector('.recording-dot');
        
        this.frameIntervalId = null;
    }

    async init() {
        // Init controllers
        await window.webcamController.init();
        
        // Connect WebSocket
        this.connectWS();
        
        // Events
        this.sendBtn.addEventListener('click', () => this.handleSendText());
        this.textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSendText();
        });
        
        // Mic button hold to talk (simulated toggle for simplicity)
        this.recordBtn.addEventListener('mousedown', () => this.startVoiceInteraction());
        this.recordBtn.addEventListener('mouseup', () => this.stopVoiceInteraction());
        // For mobile
        this.recordBtn.addEventListener('touchstart', (e) => { e.preventDefault(); this.startVoiceInteraction(); });
        this.recordBtn.addEventListener('touchend', (e) => { e.preventDefault(); this.stopVoiceInteraction(); });
    }

    connectWS() {
        // Construct WS URL
        let wsUrl = '';
        if (window.location.protocol === 'file:') {
            wsUrl = 'ws://127.0.0.1:9000/ws/chat';
        } else {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Force port 9000 to ensure we hit the FastAPI backend, 
            // even if the frontend is hosted on a different port (e.g. 5500 via Live Server)
            wsUrl = `${protocol}//${window.location.hostname}:9000/ws/chat`;
        }
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.wsStatus.classList.remove('error');
            this.wsStatus.classList.add('connected');
            
            // Start continuous emotion detection via webcam frames every 3 seconds
            this.startEmotionTracking();
        };
        
        this.ws.onclose = () => {
            this.wsStatus.classList.remove('connected');
            this.wsStatus.classList.add('error');
            this.stopEmotionTracking();
            // Auto reconnect after 3s
            setTimeout(() => this.connectWS(), 3000);
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
        };
    }

    startEmotionTracking() {
        // Stop any existing interval
        this.stopEmotionTracking();
        
        // Send webcam frame every 3 seconds for emotion detection
        this.frameIntervalId = setInterval(() => {
            this.sendFrameOnly();
        }, 3000);
        
        // Also send one immediately
        setTimeout(() => this.sendFrameOnly(), 500);
        
        // Update vision dot to green (active tracking)
        if (this.visionDot) {
            this.visionDot.classList.add('active');
        }
        console.log('[App] Emotion tracking started (every 3s)');
    }

    stopEmotionTracking() {
        if (this.frameIntervalId) {
            clearInterval(this.frameIntervalId);
            this.frameIntervalId = null;
        }
        if (this.visionDot) {
            this.visionDot.classList.remove('active');
        }
    }

    handleServerMessage(data) {
        if (data.type === 'error') {
            console.error("Server Error:", data.message);
            this.hideTyping();
            // Show a generic error message to user as well
            this.addMessage("⚠️ " + data.message, 'ai');
        }
        else if (data.type === 'emotion_update') {
            window.avatarController.setEmotion(data.emotion);
            // Flash the vision dot to show it's actively detecting
            if (this.visionDot) {
                this.visionDot.classList.add('detecting');
                setTimeout(() => this.visionDot.classList.remove('detecting'), 800);
            }
        }
        else if (data.type === 'transcription') {
            this.addMessage(data.text, 'user');
        }
        else if (data.type === 'response') {
            this.hideTyping();
            
            // Add message to UI
            this.addMessage(data.text, 'ai');
            
            // Ensure avatar updates
            if (data.emotion) window.avatarController.setEmotion(data.emotion);
            
            // Play TTS
            if (data.audio_url) {
                let audioUrl = data.audio_url;
                // If it's a relative path and we might be hosted on a different port, force port 9000
                if (audioUrl.startsWith('/')) {
                    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
                    audioUrl = `${protocol}//${window.location.hostname}:9000${audioUrl}`;
                }
                window.audioController.playAudio(audioUrl);
            }
        }
    }

    // Send only webcam frame for continuous emotion tracking
    sendFrameOnly() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        
        const frame = window.webcamController.getFrameBase64();
        if (frame) {
            this.ws.send(JSON.stringify({
                type: 'chat',
                text: '', // Empty text means just evaluate emotion silently
                face_frame: frame,
                voice_audio: null
            }));
        }
    }

    handleSendText() {
        const text = this.textInput.value.trim();
        if (!text) return;
        
        this.textInput.value = '';
        this.addMessage(text, 'user');
        this.sendToServer(text);
    }
    
    startVoiceInteraction() {
        this.recordBtn.classList.add('recording');
        window.audioController.startRecording((audioBase64) => {
            this.recordBtn.classList.remove('recording');
            if (audioBase64) {
                // Send raw audio, text will be determined by server STT
                this.sendToServer('', audioBase64);
            }
        });
    }
    
    stopVoiceInteraction() {
        this.recordBtn.classList.remove('recording');
        window.audioController.stopRecording();
    }

    sendToServer(text, audioBase64 = null) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        this.showTyping();

        const frame = window.webcamController.getFrameBase64();

        this.ws.send(JSON.stringify({
            type: 'chat',
            text: text,
            face_frame: frame,
            voice_audio: audioBase64
        }));
    }

    addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `message ${sender}`;
        div.innerHTML = `<div class="bubble">${text}</div>`;
        
        // Insert before typing indicator
        this.chatHistory.insertBefore(div, this.typingIndicator);
        this.scrollToBottom();
    }

    showTyping() {
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    hideTyping() {
        this.typingIndicator.style.display = 'none';
    }

    scrollToBottom() {
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }
}

// Boot application
window.onload = () => {
    const app = new App();
    app.init();
};

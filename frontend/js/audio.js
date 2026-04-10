class AudioController {
    constructor() {
        this.ttsPlayer = document.getElementById('ttsPlayer');
        this.micStatus = document.getElementById('micStatus');
        this.isRecording = false;
        this.isOutputUnlocked = false;
        this.isTtsEnabled = this.getTtsEnabledPref();
        this.pendingAudioUrl = null;
        this.playbackContext = null;
        this.enablePromptEl = null;
        
        // Listen to TTS player events to drive Unity lip sync
        this.ttsPlayer.onplaying = () => {
            if (window.avatarController) window.avatarController.setSpeakingState(true);
        };
        this.ttsPlayer.onended = () => {
            if (window.avatarController) window.avatarController.setSpeakingState(false);
        };
        this.ttsPlayer.onpause = () => {
            if (window.avatarController) window.avatarController.setSpeakingState(false);
        };

        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.audioData = [];
        this.onResultCallback = null;

        this.setupOutputUnlockListeners();
        this.initSTT();
    }

    setupOutputUnlockListeners() {
        const unlock = () => this.unlockOutput();

        // A successful user gesture typically unlocks audio playback for future replies.
        document.addEventListener('click', unlock, { once: true });
        document.addEventListener('touchstart', unlock, { once: true, passive: true });
        document.addEventListener('keydown', unlock, { once: true });
    }

    async unlockOutput() {
        try {
            if (!this.playbackContext) {
                this.playbackContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (this.playbackContext.state === 'suspended') {
                await this.playbackContext.resume();
            }

            this.isOutputUnlocked = true;
            this.hideEnableAudioPrompt();

            if (this.pendingAudioUrl) {
                const retryUrl = this.pendingAudioUrl;
                this.pendingAudioUrl = null;
                this.ttsPlayer.src = retryUrl;
                await this.ttsPlayer.play();
            }
        } catch (e) {
            console.error('Audio unlock failed:', e);
            this.showEnableAudioPrompt();
        }
    }

    showEnableAudioPrompt() {
        if (this.enablePromptEl) {
            this.enablePromptEl.style.display = 'flex';
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.id = 'enableAudioPrompt';
        wrapper.style.position = 'fixed';
        wrapper.style.left = '16px';
        wrapper.style.right = '16px';
        wrapper.style.bottom = '16px';
        wrapper.style.zIndex = '1000';
        wrapper.style.display = 'flex';
        wrapper.style.justifyContent = 'space-between';
        wrapper.style.alignItems = 'center';
        wrapper.style.gap = '12px';
        wrapper.style.padding = '12px 14px';
        wrapper.style.border = '1px solid rgba(255,255,255,0.15)';
        wrapper.style.borderRadius = '12px';
        wrapper.style.background = 'rgba(17, 24, 39, 0.95)';
        wrapper.style.color = '#f9fafb';
        wrapper.style.fontSize = '14px';

        const text = document.createElement('span');
        text.textContent = 'Tap Enable Sound to hear voice replies.';

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = 'Enable Sound';
        btn.style.border = 'none';
        btn.style.borderRadius = '8px';
        btn.style.padding = '8px 12px';
        btn.style.background = '#3b82f6';
        btn.style.color = '#ffffff';
        btn.style.cursor = 'pointer';

        btn.addEventListener('click', () => this.unlockOutput());

        wrapper.appendChild(text);
        wrapper.appendChild(btn);
        document.body.appendChild(wrapper);

        this.enablePromptEl = wrapper;
    }

    hideEnableAudioPrompt() {
        if (!this.enablePromptEl) return;
        this.enablePromptEl.style.display = 'none';
    }

    getTtsEnabledPref() {
        const saved = localStorage.getItem('ttsEnabled');
        return saved === null ? true : saved === 'true';
    }

    setTtsEnabledPref(enabled) {
        this.isTtsEnabled = enabled;
        localStorage.setItem('ttsEnabled', enabled.toString());
    }

    buildPlayableUrl(url) {
        const separator = url.includes('?') ? '&' : '?';
        return `${url}${separator}t=${Date.now()}`;
    }

    async initSTT() {
        // Just show mic as ready
        this.micStatus.classList.add('connected');
    }

    async startRecording(onResultCallback) {
        if (this.isRecording) return;
        this.isRecording = true;
        this.onResultCallback = onResultCallback;
        this.audioData = [];

        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            // createScriptProcessor is deprecated but widely supported for simple PCM capture
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            
            this.processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                // Convert float32 to int16
                for (let i = 0; i < inputData.length; i++) {
                    const s = Math.max(-1, Math.min(1, inputData[i]));
                    this.audioData.push(s < 0 ? s * 0x8000 : s * 0x7FFF);
                }
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
        } catch (e) {
            console.error("Failed to start recording:", e);
            this.isRecording = false;
        }
    }

    stopRecording() {
        if (!this.isRecording) return;
        this.isRecording = false;
        
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        if (this.audioData.length === 0) {
            if (this.onResultCallback) this.onResultCallback(null);
            return;
        }

        // Convert this.audioData to base64
        const buffer = new Int16Array(this.audioData);
        let binary = '';
        const bytes = new Uint8Array(buffer.buffer);
        // Process in chunks to avoid max call stack size exceeded in String.fromCharCode.apply
        const chunkSize = 8192;
        for (let i = 0; i < bytes.length; i += chunkSize) {
            const chunk = bytes.subarray(i, i + chunkSize);
            binary += String.fromCharCode.apply(null, chunk);
        }
        const base64 = window.btoa(binary);
        
        if (this.onResultCallback) {
            this.onResultCallback(base64);
        }
    }
    
    async playAudio(url) {
        if (!this.isTtsEnabled) {
            console.log('[Audio] TTS is disabled');
            return;
        }

        const playableUrl = this.buildPlayableUrl(url);
        this.pendingAudioUrl = playableUrl;

        // Append cache buster to force reload
        this.ttsPlayer.src = playableUrl;

        try {
            await this.ttsPlayer.play();
            this.pendingAudioUrl = null;
            this.hideEnableAudioPrompt();
        } catch (e) {
            if (e && e.name === 'NotAllowedError') {
                this.showEnableAudioPrompt();
            } else {
                console.error('Audio play error:', e);
            }
        }
    }
}

const audioController = new AudioController();
window.audioController = audioController;

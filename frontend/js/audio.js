class AudioController {
    constructor() {
        this.ttsPlayer = document.getElementById('ttsPlayer');
        this.micStatus = document.getElementById('micStatus');
        this.isRecording = false;
        
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

        this.initSTT();
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
    
    playAudio(url) {
        // Append cache buster to force reload
        this.ttsPlayer.src = url + "?t=" + new Date().getTime();
        this.ttsPlayer.play().catch(e => console.error("Audio play error:", e));
    }
}

const audioController = new AudioController();
window.audioController = audioController;

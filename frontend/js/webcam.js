class WebcamController {
    constructor() {
        this.video = document.getElementById('webcamPreview');
        this.canvas = document.getElementById('webcamCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.stream = null;
        this.isActive = false;
        
        // Lower resolution for faster processing
        this.targetWidth = 320;
        this.targetHeight = 240;
    }

    async init() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                video: { width: this.targetWidth, height: this.targetHeight, facingMode: "user" }
            });
            this.video.srcObject = this.stream;
            
            // Wait for video meta data to set canvas size
            this.video.onloadedmetadata = () => {
                this.canvas.width = this.targetWidth;
                this.canvas.height = this.targetHeight;
                this.isActive = true;
            };
            return true;
        } catch (err) {
            console.error("Webcam init failed:", err);
            const visionDot = document.querySelector('.recording-dot');
            if (visionDot) visionDot.style.background = '#ef4444'; // Red showing camera failed
            return false;
        }
    }

    getFrameBase64() {
        if (!this.isActive) return null;
        
        // Draw video frame to canvas
        this.ctx.drawImage(this.video, 0, 0, this.targetWidth, this.targetHeight);
        
        // Convert to base64 jpeg string (compressed 0.7 for bandwidth)
        return this.canvas.toDataURL('image/jpeg', 0.7);
    }
}

const webcamController = new WebcamController();
window.webcamController = webcamController;

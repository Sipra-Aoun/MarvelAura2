class AvatarController {
    constructor() {
        this.element = document.getElementById('avatarBase'); // The fallback 2D element
        this.unityContainer = document.getElementById('unityContainer');
        this.emotionBadge = document.getElementById('currentEmotion');
        this.emotionToggleBtn = document.getElementById('emotionToggleBtn');
        this.toggleIcon = document.getElementById('toggleIcon');
        this.currentState = 'neutral';
        this.emotionVisible = false; // Hidden by default
        
        this.unityInstance = null;
        this.unityReady = false;

        // Wire up the toggle button
        if (this.emotionToggleBtn) {
            this.emotionToggleBtn.addEventListener('click', () => this.toggleEmotionDisplay());
        }

        // ==========================================
        //  UNITY CONFIGURATION
        // ==========================================
        // Change this exactly to the prefix of your Unity Build files
        // E.g., if you have "MyAvatar.loader.js", this should be "MyAvatar"
        this.unityBuildName = 'YourUnityBuildName'; 
        // ==========================================

        this.initUnity();
    }

    async initUnity() {
        const buildUrl = `assets/unity/Build`;
        const loaderUrl = `${buildUrl}/${this.unityBuildName}.loader.js`;

        // Check if the loader file actually exists
        try {
            const response = await fetch(loaderUrl, { method: 'HEAD' });
            if (!response.ok) {
                console.warn(`[Unity] No WebGL build found at: ${loaderUrl}. Falling back to 2D svg avatars.`);
                this.show2DFallback();
                return;
            }
        } catch (e) {
            console.warn(`[Unity] Fallback to 2D avatars. Error checking loader: ${e}`);
            this.show2DFallback();
            return;
        }

        // Setup Unity Configuration
        const config = {
            dataUrl: `${buildUrl}/${this.unityBuildName}.data`,
            frameworkUrl: `${buildUrl}/${this.unityBuildName}.framework.js`,
            codeUrl: `${buildUrl}/${this.unityBuildName}.wasm`,
            streamingAssetsUrl: "StreamingAssets",
            companyName: "MarvelAura",
            productName: "AI Companion",
            productVersion: "1.0",
        };

        const canvas = document.createElement("canvas");
        canvas.id = "unity-canvas";
        canvas.style.width = "100%";
        canvas.style.height = "100%";
        
        // Hide 2D, show Unity container
        this.element.style.display = 'none';
        this.unityContainer.style.display = 'block';
        this.unityContainer.appendChild(canvas);

        // Load the external loader.js dynamically
        const script = document.createElement("script");
        script.src = loaderUrl;
        script.onload = () => {
            createUnityInstance(canvas, config, (progress) => {
                this.emotionBadge.textContent = `Loading 3D... ${Math.round(progress * 100)}%`;
            }).then((unityInstance) => {
                this.unityInstance = unityInstance;
                this.unityReady = true;
                this.emotionBadge.textContent = this.currentState;
                console.log("[Unity] WebGL Avatar Loaded Successfully");
            }).catch((message) => {
                alert("Unity Load Error: " + message);
            });
        };
        document.body.appendChild(script);
    }

    show2DFallback() {
        this.unityContainer.style.display = 'none';
        this.element.style.display = 'flex';
        // Enforce 2D default state
        this.setEmotion(this.currentState);
    }

    toggleEmotionDisplay() {
        this.emotionVisible = !this.emotionVisible;
        
        if (this.emotionVisible) {
            this.emotionBadge.classList.remove('hidden');
            this.emotionToggleBtn.classList.add('active');
            this.emotionToggleBtn.title = 'Hide emotion display';
        } else {
            this.emotionBadge.classList.add('hidden');
            this.emotionToggleBtn.classList.remove('active');
            this.emotionToggleBtn.title = 'Show emotion display';
        }
    }

    setEmotion(emotion) {
        if (!emotion || emotion === this.currentState) return;
        
        this.currentState = emotion;
        this.emotionBadge.textContent = emotion;
        
        // Update badge color based on emotion
        const emotionColors = {
            'happy': 'var(--emo-happy)',
            'sad': 'var(--emo-sad)',
            'angry': 'var(--emo-angry)',
            'surprised': 'var(--emo-surprised)',
            'neutral': 'var(--emo-neutral)'
        };
        const color = emotionColors[emotion] || 'var(--emo-neutral)';
        this.emotionBadge.style.borderColor = color;
        this.emotionBadge.style.boxShadow = `0 0 12px ${color}33`;

        if (this.unityReady && this.unityInstance) {
            // Target GameObject Name, Method Name, Parameter
            try {
                this.unityInstance.SendMessage("AvatarController", "SetEmotion", emotion);
            } catch (e) {
                console.error("[Unity] Error sending emotion:", e);
            }
        } else {
            // 2D Fallback
            this.element.className = '';
            this.element.classList.add('avatar-state');
            this.element.classList.add(`${emotion}-state`);
        }
    }

    setSpeakingState(isSpeaking) {
        if (this.unityReady && this.unityInstance) {
            try {
                // Unity SendMessage only accepts strings, floats, ints. We send a string.
                this.unityInstance.SendMessage("AvatarController", "SetSpeaking", isSpeaking ? "true" : "false");
            } catch (e) {
                console.error("[Unity] Error sending speaking state:", e);
            }
        }
    }
}

const avatarController = new AvatarController();
window.avatarController = avatarController;

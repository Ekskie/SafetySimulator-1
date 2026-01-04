document.addEventListener('DOMContentLoaded', () => {
    // 1. Get Elements
    const video = document.getElementById('scenario-video');
    const playBtn = document.getElementById('play-pause-btn');
    const playIcon = document.getElementById('play-icon');
    const progressBar = document.getElementById('progress-bar');
    const timerDisplay = document.getElementById('timer-display');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    
    // Overlays
    const startOverlay = document.getElementById('start-overlay');
    const startBtn = document.getElementById('start-btn');
    const decisionOverlay = document.getElementById('decision-overlay');
    const decisionPrompt = document.getElementById('decision-prompt');
    const decisionChoices = document.getElementById('decision-choices');
    
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingContent = document.getElementById('loading-content');
    const errorContent = document.getElementById('error-content');
    
    // Feedback Overlays
    const feedbackOverlay = document.getElementById('feedback-overlay');
    const retryBtn = document.getElementById('retry-btn');
    const lifePoints = document.querySelectorAll('.life-point');

    // 2. Data from Template
    if (typeof SCENARIO_DATA === 'undefined') {
        console.error("SCENARIO_DATA not found.");
        return;
    }

    // --- LINK PROCESSING (Google Drive Support) ---
    processGDriveLinks(SCENARIO_DATA);

    // --- GAME STATE ---
    let lives = 3;
    let currentNode = null;
    let previousNodeId = null; 
    let nodesMap = {};
    let isDecisionActive = false;
    let hasPausedForCurrentNode = false;
    let activeDecisionData = null; 
    
    // --- NODE SYSTEM SETUP ---
    const isNodeBased = SCENARIO_DATA.nodes && SCENARIO_DATA.nodes.length > 0;
    
    if (isNodeBased) {
        SCENARIO_DATA.nodes.forEach(n => nodesMap[n.id] = n);
    }

    // 3. Initialize
    if (isNodeBased && SCENARIO_DATA.startNode) {
        loadNode(SCENARIO_DATA.startNode, false);
    }

    // Event: Video Ready to Play
    video.addEventListener('canplay', () => {
        loadingOverlay.classList.add('d-none');
        if (!video.paused) updatePlayIcon();
    });

    // Event: Video Error Handling
    video.addEventListener('error', (e) => {
        console.error("Video Error Event:", video.error);
        if (video.error) {
            console.error("Source not supported/403 Forbidden. Proxy might be failing.");
            showErrorUI();
        }
    });

    startBtn.addEventListener('click', () => {
        startOverlay.classList.add('d-none');
        video.play().catch(e => {
            console.log("Play failed on start click:", e);
        });
        updatePlayIcon();
    });

    // 4. Playback Controls
    playBtn.addEventListener('click', togglePlay);
    video.addEventListener('click', togglePlay);

    function togglePlay() {
        if (isDecisionActive) return;

        if (video.paused || video.ended) {
            video.play();
        } else {
            video.pause();
        }
        updatePlayIcon();
    }

    function updatePlayIcon() {
        if (video.paused) {
            playIcon.classList.remove('bi-pause-fill');
            playIcon.classList.add('bi-play-fill');
        } else {
            playIcon.classList.remove('bi-play-fill');
            playIcon.classList.add('bi-pause-fill');
        }
    }

    function showErrorUI() {
        loadingOverlay.classList.remove('d-none');
        loadingContent.classList.add('d-none');
        errorContent.classList.remove('d-none');
    }

    // 5. Node Loading Logic
    function loadNode(nodeId, autoPlay = true) {
        const node = nodesMap[nodeId];
        if (!node) {
            console.error("Node not found:", nodeId);
            return;
        }

        console.log("Loading Node:", nodeId);
        
        if (currentNode && currentNode.decisions && currentNode.decisions.length > 0) {
            previousNodeId = currentNode.id; 
        }

        currentNode = node;
        hasPausedForCurrentNode = false; 

        // Update Video Source - Using Proxy, so direct assignment is safe
        console.log("Setting Video Source to:", node.videoUrl);
        video.src = node.videoUrl;
        video.load(); 

        if (autoPlay) {
            const playPromise = video.play();
            if (playPromise !== undefined) {
                playPromise.then(() => updatePlayIcon())
                .catch(e => console.log("Autoplay waiting for interaction...", e));
            }
        }
    }

    // 6. Progress & Decision Checking
    video.addEventListener('timeupdate', () => {
        if (video.duration) {
            const percent = (video.currentTime / video.duration) * 100;
            progressBar.style.width = `${percent}%`;
            timerDisplay.textContent = formatTime(video.currentTime);
        }

        if (isNodeBased && currentNode && currentNode.pauseAt) {
            if (video.currentTime >= currentNode.pauseAt && !isDecisionActive && !hasPausedForCurrentNode) {
                triggerDecision(currentNode.decisions);
            }
        } 
    });

    function triggerDecision(decisions) {
        if (!decisions || decisions.length === 0) return;
        
        video.pause();
        isDecisionActive = true;
        hasPausedForCurrentNode = true;
        updatePlayIcon();

        decisionPrompt.textContent = "Select Protocol"; 
        decisionChoices.innerHTML = '';

        decisions.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'btn choice-btn w-100';
            btn.innerHTML = `<i class="bi bi-caret-right-fill me-2"></i> ${opt.label}`;
            
            btn.addEventListener('click', () => {
                handleChoice(opt);
            });
            decisionChoices.appendChild(btn);
        });

        decisionOverlay.classList.remove('d-none');
        decisionOverlay.classList.add('d-flex');
    }

    function handleChoice(opt) {
        decisionOverlay.classList.remove('d-flex');
        decisionOverlay.classList.add('d-none');
        isDecisionActive = false;
        
        activeDecisionData = opt;

        if (opt.nextNode) {
            loadNode(opt.nextNode, true);
        }
    }

    // 7. End of Node / Feedback Handling
    video.addEventListener('ended', () => {
        if (!isNodeBased) return;

        if (activeDecisionData && activeDecisionData.isIncorrect) {
            handleFailure();
            activeDecisionData = null; 
            return;
        }

        if (!currentNode.decisions || currentNode.decisions.length === 0) {
            console.log("Scenario Complete. Redirecting to Quiz.");
            window.location.href = `/quiz/${SCENARIO_DATA.id}`;
        }
    });

    function handleFailure() {
        lives--;
        updateLivesUI();

        if (lives > 0) {
            feedbackOverlay.classList.remove('d-none');
            feedbackOverlay.classList.add('d-flex');
        } else {
            alert("CRITICAL FAILURE: 3 Strikes. Simulation Failed.");
            window.location.href = `/quiz/${SCENARIO_DATA.id}`;
        }
    }

    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            feedbackOverlay.classList.add('d-none');
            feedbackOverlay.classList.remove('d-flex');
            
            if (previousNodeId) {
                loadNode(previousNodeId, true);
            } else {
                loadNode(SCENARIO_DATA.startNode, true);
            }
        });
    }

    function updateLivesUI() {
        if (lives < 3 && lifePoints[2]) lifePoints[2].classList.add('life-lost');
        if (lives < 2 && lifePoints[1]) lifePoints[1].classList.add('life-lost');
        if (lives < 1 && lifePoints[0]) lifePoints[0].classList.add('life-lost');
    }

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    fullscreenBtn.addEventListener('click', () => {
        if (video.requestFullscreen) video.requestFullscreen();
    });

    /**
     * Helper to convert Google Drive links to local PROXY links.
     */
    function processGDriveLinks(data) {
        if (!data || !data.nodes) return;

        data.nodes.forEach(node => {
            if (node.videoUrl && node.videoUrl.includes('drive.google.com')) {
                const match = node.videoUrl.match(/\/d\/([a-zA-Z0-9_-]+)/);
                if (match && match[1]) {
                    const originalUrl = node.videoUrl;
                    // UPDATED: Point to local Flask proxy instead of GDrive directly
                    // Adjust prefix if your blueprint has a url_prefix (e.g., /student/proxy/...)
                    node.videoUrl = `/proxy/${match[1]}`;
                    console.log(`[GDrive Proxy] Converted: ${originalUrl} -> ${node.videoUrl}`);
                }
            }
        });
    }
});
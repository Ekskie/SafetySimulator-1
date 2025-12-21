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

    // 2. Data from Template
    if (typeof SCENARIO_DATA === 'undefined') {
        console.error("SCENARIO_DATA not found.");
        return;
    }

    // --- NODE SYSTEM SETUP (Graph Based) ---
    const isNodeBased = SCENARIO_DATA.nodes && SCENARIO_DATA.nodes.length > 0;
    let currentNode = null;
    let nodesMap = {};
    
    if (isNodeBased) {
        // Build a map for O(1) lookups
        SCENARIO_DATA.nodes.forEach(n => nodesMap[n.id] = n);
    }

    let isDecisionActive = false;
    let hasPausedForCurrentNode = false;

    // 3. Initialize
    if (isNodeBased && SCENARIO_DATA.startNode) {
        // Pre-load the first node but don't play yet
        loadNode(SCENARIO_DATA.startNode, false);
    }

    video.addEventListener('canplay', () => {
        loadingOverlay.classList.add('d-none');
    });

    startBtn.addEventListener('click', () => {
        startOverlay.classList.add('d-none');
        video.play().catch(e => console.log("Play failed:", e));
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

    // 5. Node Loading Logic
    function loadNode(nodeId, autoPlay = true) {
        const node = nodesMap[nodeId];
        if (!node) {
            console.error("Node not found:", nodeId);
            return;
        }

        console.log("Loading Node:", nodeId);
        currentNode = node;
        hasPausedForCurrentNode = false; // Reset pause trigger

        // Update Video Source
        // Note: JSON provides absolute path like "/static/videos/..."
        video.src = node.videoUrl;
        
        if (autoPlay) {
            video.play();
            updatePlayIcon();
        }
    }

    // 6. Progress & Decision Checking
    video.addEventListener('timeupdate', () => {
        // Update UI
        if (video.duration) {
            const percent = (video.currentTime / video.duration) * 100;
            progressBar.style.width = `${percent}%`;
            timerDisplay.textContent = formatTime(video.currentTime);
        }

        // --- BRANCHING LOGIC ---
        if (isNodeBased && currentNode && currentNode.pauseAt) {
            // Check if we reached the pause point (with small buffer)
            if (video.currentTime >= currentNode.pauseAt && !isDecisionActive && !hasPausedForCurrentNode) {
                triggerDecision(currentNode.decisions);
            }
        } 
        // Fallback for non-node based (Legacy linear)
        else if (!isNodeBased) {
            // (Legacy code would go here if needed)
        }
    });

    function triggerDecision(decisions) {
        if (!decisions || decisions.length === 0) return;

        console.log("Triggering Decision Point");
        
        video.pause();
        isDecisionActive = true;
        hasPausedForCurrentNode = true; // Prevent re-triggering for this node
        updatePlayIcon();

        // Setup Overlay
        decisionPrompt.textContent = "Select Protocol"; // Or generic text
        decisionChoices.innerHTML = '';

        decisions.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'btn choice-btn w-100';
            btn.innerHTML = `<i class="bi bi-caret-right-fill me-2"></i> ${opt.label}`;
            
            btn.addEventListener('click', () => {
                // Hide Overlay
                decisionOverlay.classList.remove('d-flex');
                decisionOverlay.classList.add('d-none');
                isDecisionActive = false;
                
                // Navigate to Next Node
                if (opt.nextNode) {
                    loadNode(opt.nextNode, true);
                } else {
                    console.log("No next node defined for this choice.");
                }
            });
            decisionChoices.appendChild(btn);
        });

        // Show Overlay
        decisionOverlay.classList.remove('d-none');
        decisionOverlay.classList.add('d-flex');
    }

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    // 7. End of Node Handling
    video.addEventListener('ended', () => {
        if (isNodeBased) {
            // If the video ends and there were no decisions to make,
            // it means we reached a leaf node (conclusion).
            // Redirect to Quiz.
            if (!currentNode.decisions || currentNode.decisions.length === 0) {
                console.log("Scenario Complete. Redirecting to Quiz.");
                window.location.href = `/quiz/${SCENARIO_DATA.id}`;
            }
        } else {
            // Legacy Linear Fallback
            window.location.href = `/quiz/${SCENARIO_DATA.id}`;
        }
    });

    // Fullscreen
    fullscreenBtn.addEventListener('click', () => {
        if (video.requestFullscreen) video.requestFullscreen();
    });
});
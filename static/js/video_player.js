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
    
    // Feedback Overlays
    const feedbackOverlay = document.getElementById('feedback-overlay');
    const retryBtn = document.getElementById('retry-btn');
    const lifePoints = document.querySelectorAll('.life-point');

    // 2. Data Validation
    if (typeof SCENARIO_DATA === 'undefined') {
        console.error("SCENARIO_DATA not found.");
        return;
    }

    // --- GAME STATE ---
    let lives = 3;
    let currentNode = null;
    let previousNodeId = null; 
    let nodesMap = {};
    let isDecisionActive = false;
    let hasPausedForCurrentNode = false;
    let isVideoReady = false; // New flag to prevent stale time checks
    let isFailureSequence = false; // New flag to track if we are watching a failure consequence

    // --- NODE SYSTEM SETUP ---
    const isNodeBased = SCENARIO_DATA.nodes && SCENARIO_DATA.nodes.length > 0;
    
    if (isNodeBased) {
        SCENARIO_DATA.nodes.forEach(n => nodesMap[n.id] = n);
    }

    // 3. Initialize First Node
    if (isNodeBased && SCENARIO_DATA.startNode) {
        // Prepare the node, loading happens on click to satisfy browser autoplay policies
        currentNode = nodesMap[SCENARIO_DATA.startNode];
    }

    // 4. Start Button Logic
    startBtn.addEventListener('click', () => {
        startOverlay.classList.add('d-none');
        if (currentNode) {
            loadNode(currentNode.id, true);
        }
    });

    // 5. Node Loading Logic
    function loadNode(nodeId, autoPlay = true) {
        const node = nodesMap[nodeId];
        if (!node) {
            console.error("Node not found:", nodeId);
            return;
        }

        // Save history for retry
        if (currentNode && currentNode.id !== nodeId) {
            previousNodeId = currentNode.id;
        }
        currentNode = node;
        hasPausedForCurrentNode = false; 
        isVideoReady = false; // Reset ready flag to prevent stale triggers

        // Use Direct URL (Supabase storage links are direct)
        const directUrl = node.videoUrl;
        console.log(`Loading Video: ${directUrl}`);
        
        video.src = directUrl;
        video.load();

        if (autoPlay) {
            const playPromise = video.play();
            if (playPromise !== undefined) {
                playPromise.then(() => updatePlayIcon())
                .catch(e => console.log("Autoplay waiting for interaction...", e));
            }
        }
    }

    // Listener to confirm video is ready and time is fresh
    video.addEventListener('loadedmetadata', () => {
        isVideoReady = true;
    });

    // 6. Sync Logic (The core reason Video > Iframe)
    video.addEventListener('timeupdate', () => {
        // Stop if video isn't fully loaded yet (prevents previous video time from triggering new node logic)
        if (!isVideoReady) return;

        // Update UI
        if (video.duration) {
            const percent = (video.currentTime / video.duration) * 100;
            progressBar.style.width = `${percent}%`;
            timerDisplay.textContent = formatTime(video.currentTime);
        }

        // Check for Decisions
        if (currentNode && (currentNode.pauseAt !== undefined && currentNode.pauseAt !== null)) {
            // Ensure we compare numbers
            const pauseAtTime = parseFloat(currentNode.pauseAt);
            
            // Using a small buffer (0.5s) to ensure we catch the moment
            if (video.currentTime >= pauseAtTime && !isDecisionActive && !hasPausedForCurrentNode && !isFailureSequence) {
                triggerDecision(currentNode.decisions);
            }
        }
    });

    // --- Fallback for End of Video ---
    video.addEventListener('ended', () => {
        if (!isVideoReady) return;

        // If this was a failure consequence video, show the feedback overlay now
        if (isFailureSequence) {
            isFailureSequence = false;
            showFeedbackOverlay();
            return;
        }

        if (!isDecisionActive && !hasPausedForCurrentNode) {
            // If the node has decisions, show them now
            if (currentNode && currentNode.decisions && currentNode.decisions.length > 0) {
                console.log("Video ended. Triggering fallback decision.");
                triggerDecision(currentNode.decisions);
            } 
            // If NO decisions, then the scenario is effectively complete
            else if (currentNode) {
                console.log("Video ended. No decisions. Moving to quiz/next.");
                window.location.href = `/quiz/${SCENARIO_DATA.id}`;
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
        
        if (opt.isIncorrect) {
            // 1. Deduct Life immediately
            lives--;
            updateLivesUI();

            // 2. Check for Critical Failure (Game Over)
            if (lives <= 0) {
                 alert("CRITICAL FAILURE: 3 Strikes. Simulation Failed.");
                 window.location.href = `/quiz/${SCENARIO_DATA.id}`;
                 return;
            }

            // 3. Handle Consequence
            if (opt.nextNode) {
                // Play consequence video first, then show feedback (via 'ended' event)
                isFailureSequence = true;
                loadNode(opt.nextNode, true);
            } else {
                // No video? Show feedback immediately
                showFeedbackOverlay();
            }

        } else if (opt.nextNode) {
            // Correct choice with next node
            loadNode(opt.nextNode, true);
        } else {
            // End of scenario (Success)
            window.location.href = `/quiz/${SCENARIO_DATA.id}`;
        }
    }

    // 7. Controls & Helpers
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

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    fullscreenBtn.addEventListener('click', () => {
        if (video.requestFullscreen) video.requestFullscreen();
    });

    // 8. Error Handling
    video.addEventListener('error', (e) => {
        console.error("Video Error:", video.error);
        if (video.error && video.error.code === 4) {
             alert("Video loading failed. Please check your internet connection or verify the Supabase storage link permissions.");
        }
    });

    // 9. Failure Logic Helpers
    function showFeedbackOverlay() {
        feedbackOverlay.classList.remove('d-none');
        feedbackOverlay.classList.add('d-flex');
    }

    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            feedbackOverlay.classList.add('d-none');
            feedbackOverlay.classList.remove('d-flex');
            
            // RESET TO BEGINNING (Start of Scenario)
            if (SCENARIO_DATA.startNode) {
                loadNode(SCENARIO_DATA.startNode, true);
            }
        });
    }

    function updateLivesUI() {
        if (lives < 3 && lifePoints[2]) lifePoints[2].classList.add('life-lost');
        if (lives < 2 && lifePoints[1]) lifePoints[1].classList.add('life-lost');
        if (lives < 1 && lifePoints[0]) lifePoints[0].classList.add('life-lost');
    }
});
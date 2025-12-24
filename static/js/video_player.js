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
    
    // Feedback Overlays
    const feedbackOverlay = document.getElementById('feedback-overlay');
    const retryBtn = document.getElementById('retry-btn');
    const lifePoints = document.querySelectorAll('.life-point');

    // 2. Data from Template
    if (typeof SCENARIO_DATA === 'undefined') {
        console.error("SCENARIO_DATA not found.");
        return;
    }

    // --- GAME STATE ---
    let lives = 3;
    let currentNode = null;
    let previousNodeId = null; // To handle looping back
    let nodesMap = {};
    let isDecisionActive = false;
    let hasPausedForCurrentNode = false;
    let activeDecisionData = null; // Store choice data for feedback logic
    
    // --- NODE SYSTEM SETUP (Graph Based) ---
    const isNodeBased = SCENARIO_DATA.nodes && SCENARIO_DATA.nodes.length > 0;
    
    if (isNodeBased) {
        // Build a map for O(1) lookups
        SCENARIO_DATA.nodes.forEach(n => nodesMap[n.id] = n);
    }

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
        
        // Store previous node only if it was a "setup" node (one with decisions)
        // This allows us to loop back to the QUESTION, not just the previous video snippet
        if (currentNode && currentNode.decisions && currentNode.decisions.length > 0) {
            previousNodeId = currentNode.id; 
        }

        currentNode = node;
        hasPausedForCurrentNode = false; // Reset pause trigger

        // Update Video Source
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
    });

    function triggerDecision(decisions) {
        if (!decisions || decisions.length === 0) return;

        console.log("Triggering Decision Point");
        
        video.pause();
        isDecisionActive = true;
        hasPausedForCurrentNode = true;
        updatePlayIcon();

        // Setup Overlay
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

        // Show Overlay
        decisionOverlay.classList.remove('d-none');
        decisionOverlay.classList.add('d-flex');
    }

    function handleChoice(opt) {
        // Hide Decision Overlay
        decisionOverlay.classList.remove('d-flex');
        decisionOverlay.classList.add('d-none');
        isDecisionActive = false;
        
        // Store choice to check correctness after video plays (or immediately if needed)
        // Note: For immediate feedback loops, we process flags here.
        activeDecisionData = opt;

        if (opt.nextNode) {
            loadNode(opt.nextNode, true);
        } else {
            console.log("No next node defined for this choice.");
        }
    }

    // 7. End of Node / Feedback Handling
    video.addEventListener('ended', () => {
        if (!isNodeBased) return;

        // Check if the node we just finished was a "Wrong Answer Consequence"
        if (activeDecisionData && activeDecisionData.isIncorrect) {
            handleFailure();
            activeDecisionData = null; // Reset
            return;
        }

        // Standard Navigation (Success path or Neutral path)
        if (!currentNode.decisions || currentNode.decisions.length === 0) {
            // Leaf node = End of Scenario
            console.log("Scenario Complete. Redirecting to Quiz.");
            window.location.href = `/quiz/${SCENARIO_DATA.id}`;
        } else {
            // This node just flows into another decision? 
            // Usually nodes with decisions pause. If it played to end without pausing, 
            // it might mean 'pauseAt' was missing or > duration.
            // Do nothing, just wait.
        }
    });

    function handleFailure() {
        lives--;
        updateLivesUI();

        if (lives > 0) {
            // Show Feedback Overlay
            feedbackOverlay.classList.remove('d-none');
            feedbackOverlay.classList.add('d-flex');
        } else {
            // Game Over Logic
            alert("CRITICAL FAILURE: 3 Strikes. Simulation Failed.");
            window.location.href = `/quiz/${SCENARIO_DATA.id}`; // Or a game over page
        }
    }

    // Retry Button Logic
    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            feedbackOverlay.classList.add('d-none');
            feedbackOverlay.classList.remove('d-flex');
            
            // Loop back to the previous Decision Node (Context Scene)
            if (previousNodeId) {
                console.log("Retrying node:", previousNodeId);
                loadNode(previousNodeId, true);
            } else {
                // Fallback to start if tracking lost
                loadNode(SCENARIO_DATA.startNode, true);
            }
        });
    }

    function updateLivesUI() {
        // Update hearts from right to left
        // lives = 2 -> index 2 (3rd heart) becomes lost
        // lives = 1 -> index 1 (2nd heart) becomes lost
        
        // If lives=2, we have lost 1 heart. The heart at index 2 (last one) should dim.
        if (lives < 3) lifePoints[2].classList.add('life-lost');
        if (lives < 2) lifePoints[1].classList.add('life-lost');
        if (lives < 1) lifePoints[0].classList.add('life-lost');
    }

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    // Fullscreen
    fullscreenBtn.addEventListener('click', () => {
        if (video.requestFullscreen) video.requestFullscreen();
    });
});
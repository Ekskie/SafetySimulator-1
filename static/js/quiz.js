document.addEventListener('DOMContentLoaded', () => {
    // 1. Data Validation
    // Support both direct array (legacy) and nested object structure (PC1scenario.json)
    const questionsData = QUIZ_DATA.questions || QUIZ_DATA;

    if (!questionsData || questionsData.length === 0) {
        document.getElementById('question-text').textContent = "No assessment data available for this mission.";
        return;
    }

    // 2. DOM Elements
    const questionText = document.getElementById('question-text');
    const optionsContainer = document.getElementById('options-container');
    const currentNumEl = document.getElementById('current-question-num');
    const totalNumEl = document.getElementById('total-questions');
    const progressBar = document.getElementById('quiz-progress');
    
    const questionSection = document.getElementById('question-section');
    const resultsSection = document.getElementById('results-section');
    const finalScoreEl = document.getElementById('final-score');
    const resultMessage = document.getElementById('result-message');
    const resultIcon = document.getElementById('result-icon');

    // 3. State
    let currentQuestionIndex = 0;
    let score = 0;
    const totalQuestions = questionsData.length;

    // Initialize UI
    totalNumEl.textContent = totalQuestions;
    loadQuestion(currentQuestionIndex);

    // 4. Load Question Function
    function loadQuestion(index) {
        const questionData = questionsData[index];
        
        // Update Text - Handling property name difference (JSON uses 'text')
        questionText.textContent = questionData.text || questionData.question;
        currentNumEl.textContent = index + 1;
        
        // Update Progress
        const progress = ((index) / totalQuestions) * 100;
        progressBar.style.width = `${progress}%`;

        // Generate Options
        optionsContainer.innerHTML = '';
        
        questionData.options.forEach((opt, i) => {
            const btn = document.createElement('div');
            btn.className = 'quiz-option rounded'; 
            btn.innerHTML = `<span class="badge bg-secondary me-2">${String.fromCharCode(65 + i)}</span> ${opt}`;
            
            // Pass the index 'i' and the correctOption (which is an index in your JSON)
            btn.addEventListener('click', () => handleAnswer(i, questionData.correctOption, btn));
            optionsContainer.appendChild(btn);
        });
    }

    // 5. Handle Answer
    function handleAnswer(selectedIndex, correctIndex, btnElement) {
        // Prevent multiple clicks
        if (optionsContainer.classList.contains('locked')) return;
        optionsContainer.classList.add('locked');

        // Check Correctness (Index Comparison)
        const isCorrect = selectedIndex === correctIndex;
        
        if (isCorrect) {
            score++;
            btnElement.classList.add('correct');
            btnElement.querySelector('.badge').classList.replace('bg-secondary', 'bg-success');
        } else {
            btnElement.classList.add('incorrect');
            btnElement.querySelector('.badge').classList.replace('bg-secondary', 'bg-danger');
            
            // Highlight the correct one automatically
            const allOptions = optionsContainer.children;
            if (allOptions[correctIndex]) {
                const correctBtn = allOptions[correctIndex];
                correctBtn.classList.add('correct');
                correctBtn.querySelector('.badge').classList.replace('bg-secondary', 'bg-success');
            }
        }

        // Wait then Next
        setTimeout(() => {
            currentQuestionIndex++;
            optionsContainer.classList.remove('locked');
            
            if (currentQuestionIndex < totalQuestions) {
                loadQuestion(currentQuestionIndex);
            } else {
                showResults();
            }
        }, 1500);
    }

    // 6. Show Results
        function showResults() {
        questionSection.classList.add('d-none');
        resultsSection.classList.remove('d-none');
        progressBar.style.width = '100%';

        const percentage = Math.round((score / totalQuestions) * 100);
        finalScoreEl.textContent = `${percentage}%`;

        // --- NEW: Save to Database via API ---
        saveProgressToDB(SCENARIO_ID, percentage);

        // Dynamic Feedback
        if (percentage >= 80) {
            resultMessage.textContent = "Excellent work. You have demonstrated high proficiency.";
            resultIcon.className = "bi bi-shield-check display-1 text-success mb-3 d-block";
            finalScoreEl.style.color = "var(--safezard-green)";
        } else if (percentage >= 50) {
            resultMessage.textContent = "Mission accomplished, but safety protocols need review.";
            resultIcon.className = "bi bi-exclamation-circle display-1 text-warning mb-3 d-block";
            finalScoreEl.style.color = "var(--safezard-caution-yellow)";
        } else {
            resultMessage.textContent = "Critical failure in safety adherence. Retraining recommended.";
            resultIcon.className = "bi bi-x-octagon display-1 text-danger mb-3 d-block";
            finalScoreEl.style.color = "var(--safezard-danger)";
        }
    }

    // 7. Save Data Helper
     async function saveProgressToDB(id, percentage) {
        try {
            // We need the title, often available in template variable SCENARIO_TITLE or we just send ID
            // Assuming SCENARIO_DATA is available globally from the template like in player.html
            // If not, we pass the ID as the title for now
            
            const response = await fetch('/api/save_progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // CSRF token might be needed if you have CSRF protection enabled in Flask
                },
                body: JSON.stringify({
                    scenario_id: id,
                    scenario_title: id, // Or pass actual title from template
                    score: percentage
                })
            });
            
            if (!response.ok) {
                console.error("Failed to save progress to database");
            }
            
            // OPTIONAL: Keep LocalStorage as a backup or for offline capabilities
            saveProgressLocal(id, percentage);
            
        } catch (error) {
            console.error("Network error saving progress:", error);
        }
    }

    // Keep legacy local storage as backup
    function saveProgressLocal(id, percentage) {
        const progressKey = 'safezard_progress';
        let progress = JSON.parse(localStorage.getItem(progressKey) || '{}');
        progress[id] = {
            completed: true,
            percentComplete: 100,
            timestamp: new Date().toISOString()
        };
        localStorage.setItem(progressKey, JSON.stringify(progress));
    }
}   );
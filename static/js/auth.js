document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const toggleBtn = document.getElementById('toggle-auth-btn');
    const toggleText = document.getElementById('toggle-text');
    const alertBox = document.getElementById('auth-alert');
    const alertMsg = document.getElementById('auth-alert-msg');
    const loadingOverlay = document.getElementById('auth-loading');

    let isLoginView = true;

    // Toggle between Login and Register
    toggleBtn.addEventListener('click', () => {
        isLoginView = !isLoginView;
        alertBox.classList.add('d-none'); // Clear errors

        if (isLoginView) {
            loginForm.classList.remove('d-none');
            registerForm.classList.add('d-none');
            toggleText.textContent = "New personnel?";
            toggleBtn.textContent = "Register New Account";
            toggleBtn.classList.remove('text-info');
            toggleBtn.classList.add('text-success');
        } else {
            loginForm.classList.add('d-none');
            registerForm.classList.remove('d-none');
            toggleText.textContent = "Already authorized?";
            toggleBtn.textContent = "Access Existing Account";
            toggleBtn.classList.remove('text-success');
            toggleBtn.classList.add('text-info');
        }
    });

    // Handle Login Submit
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        setLoading(true);

        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (data.success) {
                window.location.href = '/scenario_select'; 
            } else {
                showError(data.message);
                setLoading(false);
            }
        } catch (error) {
            showError("System connection error.");
            setLoading(false);
        }
    });

    // Handle Register Submit
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;
        const confirm = document.getElementById('reg-confirm').value;

        if (password !== confirm) {
            showError("Passwords do not match.");
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (data.success) {
                // STOPPED AUTOMATIC REDIRECT
                setLoading(false);
                
                // Switch back to login view so they can see where to log in
                if (!isLoginView) {
                    toggleBtn.click();
                }
                
                // Show success message (using success type green color)
                showError(data.message, 'success');
                
                // Clear the register form
                registerForm.reset();
            } else {
                showError(data.message);
                setLoading(false);
            }
        } catch (error) {
            showError("System connection error.");
            setLoading(false);
        }
    });

    // Helpers
    function setLoading(isLoading) {
        if (isLoading) loadingOverlay.classList.remove('d-none');
        else loadingOverlay.classList.add('d-none');
    }

    function showError(msg, type = 'danger') {
        alertMsg.textContent = msg;
        alertBox.classList.remove('d-none', 'alert-danger', 'alert-success');
        alertBox.classList.add(`alert-${type}`);
    }
});
document.addEventListener("DOMContentLoaded", () => {
    // Theme toggle
    const themeToggle = document.getElementById("themeToggle");
    const html = document.documentElement;

    // Initialize theme from localStorage
    const savedTheme = localStorage.getItem("theme") || "light";
    html.setAttribute("data-theme", savedTheme);

    // Theme toggle handler
    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const currentTheme = html.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            html.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
        });
    }

    // Elements
    const authSection = document.getElementById("authSection");
    const userSection = document.getElementById("userSection");
    const lectureSection = document.getElementById("lectureSection");
    const studyPackSection = document.getElementById("studyPackSection");
    const resultSection = document.getElementById("resultSection");
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const lectureForm = document.getElementById("lectureForm");
    const uploadForm = document.getElementById("uploadForm");
    const authMessage = document.getElementById("authMessage");
    const messageDiv = document.getElementById("message");
    const uploadMessage = document.getElementById("uploadMessage");
    const generateMessage = document.getElementById("generateMessage");
    const currentUserSpan = document.getElementById("currentUser");
    const authTitle = document.getElementById("authTitle");
    const switchToRegister = document.getElementById("switchToRegister");
    const switchToLogin = document.getElementById("switchToLogin");
    const authSwitchText = document.getElementById("authSwitchText");
    const switchToLoginText = document.getElementById("switchToLoginText");
    const logoutBtn = document.getElementById("logoutBtn");

    // Header buttons
    const headerLoginBtn = document.getElementById("headerLoginBtn");
    const headerRegisterBtn = document.getElementById("headerRegisterBtn");
    const headerLogoutBtn = document.getElementById("headerLogoutBtn");

    // Study pack elements
    const lectureSelect = document.getElementById("lectureSelect");
    const generateBtn = document.getElementById("generateBtn");
    const newGenerateBtn = document.getElementById("newGenerateBtn");
    const resultTitle = document.getElementById("resultTitle");
    const resultMeta = document.getElementById("resultMeta");
    const resultContent = document.getElementById("resultContent");

    // Buttons
    const loginBtn = document.getElementById("loginBtn");
    const registerBtn = document.getElementById("registerBtn");
    const saveBtn = document.getElementById("saveBtn");
    const uploadBtn = document.getElementById("uploadBtn");

    // State
    let selectedLectureId = null;
    let selectedTaskType = null;

    // Header button handlers
    if (headerLoginBtn) {
        headerLoginBtn.addEventListener("click", () => showLogin());
    }
    if (headerRegisterBtn) {
        headerRegisterBtn.addEventListener("click", () => showRegister());
    }
    if (headerLogoutBtn) {
        headerLogoutBtn.addEventListener("click", async () => {
            try {
                await fetch("/api/logout", { method: "POST" });
                checkAuth();
            } catch (error) {
                showMessage("Logout failed.", "error");
            }
        });
    }

    // Check auth status on load
    checkAuth();

    // Switch between login/register
    switchToRegister.addEventListener("click", () => showRegister());
    switchToLogin.addEventListener("click", () => showLogin());

    // Login form submit
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("loginUsername").value.trim();
        const password = document.getElementById("loginPassword").value;

        if (!username || !password) {
            showAuthMessage("Please fill in both fields.", "error");
            return;
        }

        loginBtn.disabled = true;
        loginBtn.textContent = "Logging in...";

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();

            if (response.ok) {
                showAuthMessage(data.message, "success");
                loginForm.reset();
                setTimeout(() => checkAuth(), 500);
            } else {
                showAuthMessage(data.error || "Login failed.", "error");
            }
        } catch (error) {
            showAuthMessage("Network error. Please try again.", "error");
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = "Login";
        }
    });

    // Register form submit
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("registerUsername").value.trim();
        const email = document.getElementById("registerEmail").value.trim();
        const password = document.getElementById("registerPassword").value;

        if (!username || !email || !password) {
            showAuthMessage("Please fill in all fields.", "error");
            return;
        }
        if (password.length < 6) {
            showAuthMessage("Password must be at least 6 characters.", "error");
            return;
        }

        registerBtn.disabled = true;
        registerBtn.textContent = "Registering...";

        try {
            const response = await fetch("/api/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password })
            });
            const data = await response.json();

            if (response.ok) {
                showAuthMessage(data.message, "success");
                registerForm.reset();
                setTimeout(() => checkAuth(), 500);
            } else {
                showAuthMessage(data.error || "Registration failed.", "error");
            }
        } catch (error) {
            showAuthMessage("Network error. Please try again.", "error");
        } finally {
            registerBtn.disabled = false;
            registerBtn.textContent = "Register";
        }
    });

    // Logout
    logoutBtn.addEventListener("click", async () => {
        try {
            await fetch("/api/logout", { method: "POST" });
            checkAuth();
        } catch (error) {
            showMessage("Logout failed.", "error");
        }
    });

    // Lecture form submit (manual entry)
    lectureForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const title = document.getElementById("title").value.trim();
        const content = document.getElementById("content").value.trim();

        if (!title || !content) {
            showMessage("Please fill in both title and content.", "error");
            return;
        }

        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        try {
            const response = await fetch("/api/lectures", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, content })
            });

            const data = await response.json();

            if (response.ok) {
                showMessage(data.message, "success");
                lectureForm.reset();
                // Refresh lecture list
                loadLectures();
            } else {
                showMessage(data.error || "Failed to save lecture.", "error");
            }
        } catch (error) {
            showMessage("Network error. Please try again.", "error");
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = "Save Lecture";
        }
    });

    // Upload form submit
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const fileInput = document.getElementById("lectureFile");
        const file = fileInput.files[0];
        const title = document.getElementById("uploadTitle").value.trim();

        if (!file) {
            showUploadMessage("Please select a file.", "error");
            return;
        }

        const allowedTypes = [".pdf", ".docx"];
        const fileExt = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
        if (!allowedTypes.includes(fileExt)) {
            showUploadMessage("Only PDF and DOCX files are allowed.", "error");
            return;
        }

        uploadBtn.disabled = true;
        uploadBtn.textContent = "Uploading & Extracting...";

        const formData = new FormData();
        formData.append("file", file);
        if (title) {
            formData.append("title", title);
        }

        try {
            const response = await fetch("/api/lectures/upload", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                showUploadMessage("Lecture uploaded and saved successfully (ID: " + data.lecture_id + "). No further action needed.", "success");
                uploadForm.reset();
                // Refresh lecture list
                loadLectures();
            } else {
                showUploadMessage(data.error || "Upload failed.", "error");
            }
        } catch (error) {
            showUploadMessage("Network error. Please try again.", "error");
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = "Upload & Extract Text";
        }
    });

    // Lecture selection change
    lectureSelect.addEventListener("change", () => {
        selectedLectureId = lectureSelect.value ? parseInt(lectureSelect.value, 10) : null;
        updateGenerateButton();
    });

    // Task type selection change
    document.querySelectorAll('input[name="taskType"]').forEach(radio => {
        radio.addEventListener("change", () => {
            selectedTaskType = radio.value;
            updateGenerateButton();
        });
    });

    // Generate button click
    generateBtn.addEventListener("click", async () => {
        if (!selectedLectureId || !selectedTaskType) return;

        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="loading-spinner"></span><span class="btn-text">Generating...</span>';
        generateMessage.className = "message hidden";

        try {
            const taskDescriptions = {
                summary: "generate a summary",
                notes: "create study notes",
                questions: "generate practice questions",
                mcqs: "create multiple choice questions"
            };

            const response = await fetch("/api/study-pack/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    task: taskDescriptions[selectedTaskType],
                    lecture_id: selectedLectureId
                })
            });

            const data = await response.json();

            if (response.ok) {
                showGenerateMessage("Study pack generated successfully!", "success");
                displayResult(data);
            } else {
                showGenerateMessage(data.error || "Generation failed.", "error");
            }
        } catch (error) {
            showGenerateMessage("Network error. Please try again.", "error");
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<span class="btn-text">Generate Study Pack</span>';
        }
    });

    // New generate button
    newGenerateBtn.addEventListener("click", () => {
        resultSection.classList.add("hidden");
        studyPackSection.classList.remove("hidden");
        // Reset selections
        lectureSelect.value = "";
        selectedLectureId = null;
        document.querySelectorAll('input[name="taskType"]').forEach(radio => {
            radio.checked = false;
        });
        selectedTaskType = null;
        updateGenerateButton();
    });

    // Check authentication status
    async function checkAuth() {
        try {
            const response = await fetch("/api/me");
            const data = await response.json();

            if (data.user) {
                showAuthenticatedUI(data.user);
            } else {
                showUnauthenticatedUI();
            }
        } catch (error) {
            showUnauthenticatedUI();
        }
    }

    function showAuthenticatedUI(user) {
        authSection.classList.add("hidden");
        userSection.classList.add("hidden");  // Hide the account card in main content
        lectureSection.classList.remove("hidden");
        studyPackSection.classList.remove("hidden");
        
        // Show user menu in header, hide auth buttons
        document.getElementById("headerAuthButtons").classList.add("hidden");
        document.getElementById("headerUserMenu").classList.remove("hidden");
        document.querySelector("#headerUserName span").textContent = user.username;
        
        loadLectures();
    }

    function showUnauthenticatedUI() {
        authSection.classList.remove("hidden");
        userSection.classList.add("hidden");
        lectureSection.classList.add("hidden");
        studyPackSection.classList.add("hidden");
        resultSection.classList.add("hidden");
        
        // Show auth buttons in header, hide user menu
        document.getElementById("headerAuthButtons").classList.remove("hidden");
        document.getElementById("headerUserMenu").classList.add("hidden");
        
        showLogin();
    }

    function showLogin() {
        loginForm.classList.remove("hidden");
        registerForm.classList.add("hidden");
        authTitle.textContent = "Login";
        authSwitchText.classList.remove("hidden");
        switchToRegister.classList.remove("hidden");
        switchToLoginText.classList.add("hidden");
        switchToLogin.classList.add("hidden");
        authMessage.className = "message hidden";
    }

    function showRegister() {
        loginForm.classList.add("hidden");
        registerForm.classList.remove("hidden");
        authTitle.textContent = "Register";
        authSwitchText.classList.add("hidden");
        switchToRegister.classList.add("hidden");
        switchToLoginText.classList.remove("hidden");
        switchToLogin.classList.remove("hidden");
        authMessage.className = "message hidden";
    }

    async function loadLectures() {
        try {
            const response = await fetch("/api/lectures");
            const data = await response.json();

            if (response.ok && data.lectures) {
                // Clear existing options except the first
                lectureSelect.innerHTML = '<option value="">-- Choose a lecture --</option>';

                data.lectures.forEach(lecture => {
                    const option = document.createElement("option");
                    option.value = lecture.id;
                    option.textContent = lecture.title;
                    lectureSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error("Failed to load lectures:", error);
        }
    }

    function updateGenerateButton() {
        const hasSelection = selectedLectureId && selectedTaskType;
        generateBtn.disabled = !hasSelection;
    }

    function displayResult(data) {
        studyPackSection.classList.add("hidden");
        resultSection.classList.remove("hidden");

        resultTitle.textContent = data.lecture_title;

        // Build metadata badges
        const metaParts = [];
        metaParts.push(`<span class="result-meta-item">${data.task_type.toUpperCase()}</span>`);
        metaParts.push(`<span class="result-meta-item">${data.provider} (${data.model})</span>`);
        metaParts.push(`<span class="result-meta-item">${data.chunks_used} chunks</span>`);
        if (data.fallback_used) {
            metaParts.push(`<span class="result-meta-item" style="background:#fff3cd;color:#856404;">fallback used</span>`);
        }
        resultMeta.innerHTML = metaParts.join('');

        resultContent.innerHTML = marked.parse(data.content);
    }

    function showAuthMessage(text, type) {
        authMessage.textContent = text;
        authMessage.className = "message " + type;
    }

    function showMessage(text, type) {
        messageDiv.textContent = text;
        messageDiv.className = "message " + type;
    }

    function showUploadMessage(text, type) {
        uploadMessage.textContent = text;
        uploadMessage.className = "message " + type;
    }

    function showGenerateMessage(text, type) {
        generateMessage.textContent = text;
        generateMessage.className = "message " + type;
    }
});
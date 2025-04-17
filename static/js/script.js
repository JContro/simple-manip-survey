document.addEventListener("DOMContentLoaded", function () {
  // Tab switching functionality
  const loginTab = document.getElementById("login-tab");
  const registerTab = document.getElementById("register-tab");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  loginTab.addEventListener("click", function () {
    loginTab.classList.add("active");
    registerTab.classList.remove("active");
    loginForm.classList.add("active");
    registerForm.classList.remove("active");
  });

  registerTab.addEventListener("click", function () {
    registerTab.classList.add("active");
    loginTab.classList.remove("active");
    registerForm.classList.add("active");
    loginForm.classList.remove("active");
  });

  // Form validation
  const loginFormElement = document.getElementById("login");
  const registerFormElement = document.getElementById("register");

  // Login form validation
  loginFormElement.addEventListener("submit", function (e) {
    e.preventDefault();

    // Reset error messages
    clearErrors("login");

    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    let isValid = true;

    // Email validation
    if (!email) {
      showError("login-email", "Email is required");
      isValid = false;
    } else if (!isValidEmail(email)) {
      showError("login-email", "Please enter a valid email address");
      isValid = false;
    }

    // Password validation
    if (!password) {
      showError("login-password", "Password is required");
      isValid = false;
    }

    if (isValid) {
      // Simulate login process
      simulateLoginProcess(email, password);
    }
  });

  // Registration form validation
  registerFormElement.addEventListener("submit", function (e) {
    e.preventDefault();

    // Reset error messages
    clearErrors("register");

    const name = document.getElementById("register-name").value.trim();
    const email = document.getElementById("register-email").value.trim();
    const password = document.getElementById("register-password").value;
    const confirmPassword = document.getElementById(
      "register-confirm-password"
    ).value;
    let isValid = true;

    // Name validation
    if (!name) {
      showError("register-name", "Name is required");
      isValid = false;
    }

    // Email validation
    if (!email) {
      showError("register-email", "Email is required");
      isValid = false;
    } else if (!isValidEmail(email)) {
      showError("register-email", "Please enter a valid email address");
      isValid = false;
    }

    // Password validation
    if (!password) {
      showError("register-password", "Password is required");
      isValid = false;
    } else if (password.length < 8) {
      showError(
        "register-password",
        "Password must be at least 8 characters long"
      );
      isValid = false;
    }

    // Confirm password validation
    if (!confirmPassword) {
      showError("register-confirm-password", "Please confirm your password");
      isValid = false;
    } else if (password !== confirmPassword) {
      showError("register-confirm-password", "Passwords do not match");
      isValid = false;
    }

    if (isValid) {
      // Simulate registration process
      simulateRegistrationProcess(name, email, password);
    }
  });

  // Start survey button
  const startSurveyBtn = document.getElementById("start-survey-btn");
  startSurveyBtn.addEventListener("click", function () {
    // Check if user is logged in (for demo purposes, we'll just show a message)
    const isLoggedIn = localStorage.getItem("isLoggedIn") === "true";

    if (isLoggedIn) {
      // Redirect to survey page (would be implemented in a real app)
      window.location.href = "#survey-page"; // Placeholder for demo
      showMessage("login", "Redirecting to survey...", "success");
    } else {
      // Show message to login first
      showMessage("login", "Please login to start the survey", "error");
      // Scroll to login form
      loginForm.scrollIntoView({ behavior: "smooth" });
    }
  });

  // Remember me functionality
  const rememberMeCheckbox = document.getElementById("remember-me");

  // Check if there are saved credentials
  if (localStorage.getItem("rememberedEmail")) {
    document.getElementById("login-email").value =
      localStorage.getItem("rememberedEmail");
    rememberMeCheckbox.checked = true;
  }

  // Helper functions
  function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  function showError(fieldId, message) {
    const errorElement = document.getElementById(`${fieldId}-error`);
    errorElement.textContent = message;
  }

  function clearErrors(formPrefix) {
    const errorElements = document.querySelectorAll(
      `#${formPrefix}-form .error-message`
    );
    errorElements.forEach((element) => {
      element.textContent = "";
    });

    // Clear form message
    const messageElement = document.getElementById(`${formPrefix}-message`);
    messageElement.textContent = "";
    messageElement.className = "form-message";
  }

  function showMessage(formPrefix, message, type) {
    const messageElement = document.getElementById(`${formPrefix}-message`);
    messageElement.textContent = message;
    messageElement.className = `form-message ${type}`;
  }

  function simulateLoginProcess(email, password) {
    // This is a simulation - in a real app, you would make an API call
    showMessage("login", "Logging in...", "success");

    // Simulate API delay
    setTimeout(() => {
      // For demo purposes, any login attempt succeeds
      localStorage.setItem("isLoggedIn", "true");

      // Handle remember me
      if (rememberMeCheckbox.checked) {
        localStorage.setItem("rememberedEmail", email);
      } else {
        localStorage.removeItem("rememberedEmail");
      }

      showMessage("login", "Login successful!", "success");

      // Redirect to survey after successful login (would be implemented in a real app)
      setTimeout(() => {
        window.location.href = "#survey-page"; // Placeholder for demo
      }, 1000);
    }, 1500);
  }

  function simulateRegistrationProcess(name, email, password) {
    // This is a simulation - in a real app, you would make an API call
    showMessage("register", "Creating your account...", "success");

    // Simulate API delay
    setTimeout(() => {
      // For demo purposes, any registration attempt succeeds
      showMessage(
        "register",
        "Registration successful! You can now login.",
        "success"
      );

      // Clear form
      document.getElementById("register-name").value = "";
      document.getElementById("register-email").value = "";
      document.getElementById("register-password").value = "";
      document.getElementById("register-confirm-password").value = "";

      // Switch to login tab after successful registration
      setTimeout(() => {
        loginTab.click();
      }, 1500);
    }, 1500);
  }
});

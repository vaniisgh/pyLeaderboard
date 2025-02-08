// Constants
const CONFIG = {
  API_BASE:
    window.location.hostname === "localhost"
      ? "http://localhost:8000"
      : window.location.origin,
};

// Show error/success messages
function showAlert(message, type = "danger") {
  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
  document.querySelector("#alerts").appendChild(alertDiv);
  setTimeout(() => alertDiv.remove(), 5000);
}

// Login handler
async function login(event) {
  event.preventDefault();
  const formData = new FormData(event.target);

  try {
    const response = await fetch(`${CONFIG.API_BASE}/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        username: formData.get("username"),
        password: formData.get("password"),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Login failed");
    }

    // Store auth token and redirect
    localStorage.setItem("authToken", data.access_token);
    window.location.href = "/game-dashboard/";
  } catch (error) {
    showAlert(error.message);
  }
}

// Register handler
async function register(event) {
  event.preventDefault();
  const formData = new FormData(event.target);

  try {
    const response = await fetch(`${CONFIG.API_BASE}/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: formData.get("username"),
        email: formData.get("email"),
        password: formData.get("password"),
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Registration failed");
    }

    showAlert("Registration successful! Please login.", "success");
    // Switch to login tab
    document.querySelector('a[href="#login"]').click();
  } catch (error) {
    showAlert(error.message);
  }
}

// Check authentication status on page load
document.addEventListener("DOMContentLoaded", () => {
  const authToken = localStorage.getItem("authToken");
  if (authToken && window.location.pathname === "/") {
    window.location.href = "/game-dashboard/";
  }
});

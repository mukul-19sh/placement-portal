class AuthManager {
  constructor() {
    this.token = localStorage.getItem("auth_token");
    this.userRole = localStorage.getItem("user_role");
    this.userEmail = localStorage.getItem("user_email");
  }

  setAuth(token, role, email) {
    this.token = token;
    this.userRole = role;
    this.userEmail = email;
    localStorage.setItem("auth_token", token);
    localStorage.setItem("user_role", role);
    localStorage.setItem("user_email", email);
  }

  clearAuth() {
    this.token = null;
    this.userRole = null;
    this.userEmail = null;
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_role");
    localStorage.removeItem("user_email");
  }

  isAuthenticated() {
    return !!this.token;
  }

  getRole() {
    return this.userRole;
  }

  getEmail() {
    return this.userEmail;
  }

  async signUp(email, password, role) {
    try {
      const data = await api.register(email, password, role);
      return { success: true, message: data.message || "Registration successful" };
    } catch (error) {
      return { success: false, message: error.message };
    }
  }

  async signIn(email, password, role = null) {
    try {
      const data = await api.login(email, password, role);
      const payload = JSON.parse(atob(data.access_token.split(".")[1]));
      this.setAuth(data.access_token, payload.role, email);
      return { success: true, role: payload.role };
    } catch (error) {
      return { success: false, message: error.message };
    }
  }

  logout() {
    this.clearAuth();
    window.location.href = "index.html";
  }
}

const auth = new AuthManager();

// Route protection
const PROTECTED_ROUTES = {
  "admin-dashboard.html": ["admin"],
  "company-dashboard.html": ["company"],
  "student-dashboard.html": ["student"],
};

function checkRouteProtection() {
  const page = window.location.pathname.split("/").pop();
  if (PROTECTED_ROUTES[page]) {
    if (!auth.isAuthenticated()) {
      window.location.href = "index.html";
      return false;
    }
    if (!PROTECTED_ROUTES[page].includes(auth.getRole())) {
      redirectToDashboard(auth.getRole());
      return false;
    }
  }
  return true;
}

function redirectToDashboard(role) {
  const map = {
    admin: "admin-dashboard.html",
    company: "company-dashboard.html",
    student: "student-dashboard.html",
  };
  window.location.href = map[role] || "index.html";
}

document.addEventListener("DOMContentLoaded", () => {
  checkRouteProtection();

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) logoutBtn.addEventListener("click", () => auth.logout());

  const emailEl = document.getElementById("user-email");
  if (emailEl && auth.getEmail()) emailEl.textContent = auth.getEmail();
});

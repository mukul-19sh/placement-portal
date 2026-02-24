// Fix 4: Single config constant -- change this when deploying
const API_BASE = "https://placement-portal-backend-mukul.onrender.com";

const api = {
  register: (email, password, role) =>
    fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, role }),
    }).then(handleResponse),

  login: (email, password, role) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const url = role
      ? `${API_BASE}/auth/login?role=${encodeURIComponent(role)}`
      : `${API_BASE}/auth/login`;
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    }).then(handleResponse);
  },

  getStudents: () => authFetch("/students/"),
  addStudent: (data) =>
    authFetch("/students/", { method: "POST", body: JSON.stringify([data]) }),

  getJobs: () => authFetch("/jobs/"),
  getMyJobs: () => authFetch("/company/my-jobs"),
  addJob: (data) =>
    authFetch("/jobs/", { method: "POST", body: JSON.stringify(data) }),

  adminDashboard: () => authFetch("/admin/dashboard"),
  companyDashboard: () => authFetch("/company/dashboard"),
  studentDashboard: () => authFetch("/student/dashboard"),

  shortlist: (jobId) => authFetch(`/admin/shortlist/${jobId}`),
  companyShortlist: (jobId) => authFetch(`/company/shortlist/${jobId}`),
};

// Fix 3: Token expiry shows alert before redirect
function authFetch(path, options = {}) {
  const token = localStorage.getItem("auth_token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  return fetch(`${API_BASE}${path}`, { ...options, headers }).then((res) => {
    if (res.status === 401) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_role");
      localStorage.removeItem("user_email");
      alert("Session expired. Please login again.");
      window.location.href = "sign-in.html";
      throw new Error("Session expired. Please login again.");
    }
    return handleResponse(res);
  });
}

async function handleResponse(res) {
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
  return data;
}

// Fix 5: Reusable form validation helpers
function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePassword(pw) {
  return pw.length >= 6;
}

function validateCGPA(val) {
  const n = parseFloat(val);
  return !isNaN(n) && n >= 0 && n <= 10;
}

function validateNotEmpty(val) {
  return val.trim().length > 0;
}

function showFormError(formEl, message) {
  let errEl = formEl.querySelector(".form-error");
  if (!errEl) {
    errEl = document.createElement("p");
    errEl.className = "form-error";
    errEl.style.cssText = "color:#dc3545;background:#f8d7da;padding:10px;border-radius:8px;text-align:center;margin-top:10px;";
    formEl.appendChild(errEl);
  }
  errEl.textContent = message;
  errEl.style.display = "block";
  setTimeout(() => { errEl.style.display = "none"; }, 4000);
}

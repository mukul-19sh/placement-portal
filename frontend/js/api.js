// Fix 4: Single config constant -- change this when deploying
// Temporarily pointing to local backend for testing the fix. Change back to Render for production!
// const API_BASE = "https://placement-portal-backend-mukul.onrender.com";
const API_BASE = "http://localhost:8000";
// Console log for debugging
console.log('API_BASE:', API_BASE);
console.log('Protocol:', window.location.protocol);
console.log('Hostname:', window.location.hostname);

// Render free tier can sleep; ping it once on page load
async function wakeServer() {
  try {
    await fetch(`${API_BASE}/`, { method: "GET" });
  } catch (e) {
    console.log("Server not responding:", e.message);
  }
}

const api = {
  register: (email, password, role) =>
    fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, role }),
    }).then(handleResponse).catch(handleNetworkError),

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
    }).then(handleResponse).catch(handleNetworkError);
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
  adminAnalytics: () => authFetch("/admin/analytics"),

  // Admin Notifications
  getAdminNotifications: () => authFetch("/admin/notifications"),
  markAdminNotificationRead: (id) => authFetch(`/admin/notifications/${id}/read`, { method: "POST" }),
  markAllAdminNotificationsRead: () => authFetch("/admin/notifications/mark-all-read", { method: "POST" }),

  shortlist: (jobId) => authFetch(`/admin/shortlist/${jobId}`),
  companyShortlist: (jobId) => authFetch(`/company/shortlist/${jobId}`),

  // Company profile endpoints
  getCompanyProfile: () => authFetch("/company/profile"),
  createOrUpdateCompanyProfile: (data) => authFetch("/company/profile", {
    method: "POST",
    body: JSON.stringify(data)
  }),

  // Student profile endpoints
  getStudentProfile: () => authFetch("/student/profile"),
  createOrUpdateProfile: (data) => authFetch("/student/profile", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  uploadResume: (file) => {
    const token = localStorage.getItem("auth_token");
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/student/upload-resume`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    }).then(handleResponse);
  },

  // Matched jobs and applications
  getMatchedJobs: () => authFetch("/student/matched-jobs"),
  applyForJob: (jobId) => authFetch(`/student/apply/${jobId}`, { method: "POST" }),
  getMyApplications: () => authFetch("/student/my-applications"),

  // AI Resume Review
  aiResumeReview: () => authFetch("/student/ai-resume-review", { method: "POST" }),

  // Notifications
  getNotifications: () => authFetch("/student/notifications"),
  markNotificationRead: (id) => authFetch(`/student/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () => authFetch("/student/notifications/mark-all-read", { method: "POST" }),

  // Resume Chatbot
  chatWithBot: (question) => authFetch("/chatbot/chat", {
    method: "POST",
    body: JSON.stringify({ question, has_resume: false })
  }),
  chatWithBotAndResume: (question, file) => {
    const token = localStorage.getItem("auth_token");
    const form = new FormData();
    form.append("file", file);
    form.append("chat_request", JSON.stringify({ question, has_resume: true }));

    return fetch(`${API_BASE}/chatbot/chat-with-resume`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    }).then(handleResponse);
  },
  getResumeSuggestions: () => authFetch("/chatbot/suggestions"),
  getSkillsAnalysis: () => authFetch("/chatbot/skills-analysis"),
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

function handleNetworkError(error) {
  if (error.message === 'Failed to fetch') {
    throw new Error('Cannot connect to server at ' + API_BASE + '. Make sure backend is running (python run.py in backend folder). Check browser console (F12) for details.');
  }
  throw error;
}

api.getFileUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  if (!url.startsWith('/uploads')) {
    url = '/uploads' + (url.startsWith('/') ? '' : '/') + url;
  }
  return API_BASE + url;
}; // Helper to resolve local/cloud file URLs

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

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`${btn.dataset.tab}-tab`).classList.add("active");
      
      // Load content for specific tabs
      if (btn.dataset.tab === "matched-jobs") {
        loadMatchedJobs();
      } else if (btn.dataset.tab === "my-applications") {
        loadApplications();
      } else if (btn.dataset.tab === "resume-chatbot") {
        initializeChatbot();
      }
    });
  });

  // Notification system
  const notificationBtn = document.getElementById("notification-btn");
  const notificationDropdown = document.getElementById("notification-dropdown");
  
  if (notificationBtn && notificationDropdown) {
    notificationBtn.addEventListener("click", () => {
      notificationDropdown.classList.toggle("show");
      if (notificationDropdown.classList.contains("show")) {
        loadNotifications();
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".notification-container")) {
        notificationDropdown.classList.remove("show");
      }
    });

    // Mark all as read
    document.getElementById("mark-all-read").addEventListener("click", markAllNotificationsRead);
  }

  document.getElementById("profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("profile-name").value;
    const skills = document.getElementById("profile-skills").value;
    const cgpa = document.getElementById("profile-cgpa").value;

    if (!validateNotEmpty(name)) { showFormError(e.target, "Name is required."); return; }
    if (!validateNotEmpty(skills)) { showFormError(e.target, "At least one skill is required."); return; }
    if (!validateCGPA(cgpa)) { showFormError(e.target, "CGPA must be between 0 and 10."); return; }

    const data = {
      full_name: name,
      skills: skills.split(",").map((s) => s.trim()).join(", "),
      cgpa: parseFloat(cgpa),
    };
    const msg = document.getElementById("profile-message");
    try {
      const res = await api.createOrUpdateProfile(data);
      msg.textContent = res.message;
      msg.className = "success-message";
      msg.style.display = "block";
      localStorage.setItem("student_cgpa", data.cgpa);
      localStorage.setItem("student_skills", data.skills);
      if (res.profile && res.profile.id) {
        localStorage.setItem("student_profile_id", res.profile.id);
      }
      loadStats();
      loadProfilePreview({ name: data.full_name, skills: data.skills, cgpa: data.cgpa });
      updateProfileCompletion({ profile_completion: calculateProfileCompletion(res.profile) });
    } catch (err) {
      msg.textContent = "Error: " + err.message;
      msg.className = "error-message";
      msg.style.display = "block";
    }
  });

  const uploadBtn = document.getElementById("upload-resume-btn");
  const fileInput = document.getElementById("resume-file");
  const resumeMsg = document.getElementById("resume-message");
  if (uploadBtn && fileInput && resumeMsg) {
    uploadBtn.addEventListener("click", async () => {
      resumeMsg.textContent = "";
      resumeMsg.className = "";
      resumeMsg.style.display = "none";

      const file = fileInput.files[0];
      if (!file) {
        resumeMsg.textContent = "Please choose a PDF file first.";
        resumeMsg.className = "error-message";
        resumeMsg.style.display = "block";
        return;
      }
      if (file.type !== "application/pdf") {
        resumeMsg.textContent = "Only PDF files are allowed.";
        resumeMsg.className = "error-message";
        resumeMsg.style.display = "block";
        return;
      }

      try {
        const res = await api.uploadResume(file);
        resumeMsg.textContent = "Resume uploaded successfully!";
        resumeMsg.className = "success-message";
        resumeMsg.style.display = "block";
        if (res.resume_url) {
          localStorage.setItem("student_resume_url", res.resume_url);
        }
      } catch (err) {
        resumeMsg.textContent = "Error: " + err.message;
        resumeMsg.className = "error-message";
        resumeMsg.style.display = "block";
      }
    });
  }

  document.getElementById("refresh-jobs").addEventListener("click", loadJobs);

  loadStats();
  loadJobs();
  loadProfile();
  setInterval(loadNotifications, 30000); // Load notifications every 30 seconds
});

function calculateProfileCompletion(profile) {
  if (!profile) return 0;
  
  let completion = 0;
  const totalFields = 4; // name, skills, cgpa, resume
  
  if (profile.name && profile.name.trim()) completion += 1;
  if (profile.skills && profile.skills.trim()) completion += 1;
  if (profile.cgpa && profile.cgpa > 0) completion += 1;
  if (profile.resume_url && profile.resume_url.trim()) completion += 1;
  
  return Math.round((completion / totalFields) * 100);
}

function updateProfileCompletion(profileData) {
  const completionEl = document.getElementById("profile-completion");
  if (!completionEl || !profileData.profile_completion) return;
  
  const percentage = profileData.profile_completion;
  const status = profileData.completion_status;
  
  completionEl.innerHTML = `
    <div class="completion-percentage">${percentage}%</div>
    <div class="completion-status">${status}</div>
  `;
}

// Chatbot functionality
let currentResumeFile = null;

function initializeChatbot() {
  const sendBtn = document.getElementById("send-chatbot-btn");
  const questionInput = document.getElementById("chatbot-question");
  const analyzeBtn = document.getElementById("analyze-resume-btn");
  const resumeInput = document.getElementById("chatbot-resume");
  
  if (sendBtn && questionInput) {
    sendBtn.addEventListener("click", sendChatMessage);
    questionInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        sendChatMessage();
      }
    });
  }
  
  if (analyzeBtn && resumeInput) {
    analyzeBtn.addEventListener("click", analyzeResumeForChatbot);
    resumeInput.addEventListener("change", (e) => {
      currentResumeFile = e.target.files[0];
    });
  }
  
  // Quick question buttons
  document.querySelectorAll(".quick-question-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const question = btn.dataset.question;
      document.getElementById("chatbot-question").value = question;
      sendChatMessage();
    });
  });
}

async function sendChatMessage() {
  const questionInput = document.getElementById("chatbot-question");
  const question = questionInput.value.trim();
  
  if (!question) return;
  
  // Add user message to chat
  addChatMessage(question, "user");
  questionInput.value = "";
  
  try {
    const response = currentResumeFile 
      ? await api.chatWithBotAndResume(question, currentResumeFile)
      : await api.chatWithBot(question);
    
    // Add bot response to chat
    addChatMessage(response.answer, "bot");
    
    // Show analysis if available
    if (response.analysis) {
      showAnalysisInChat(response.analysis);
    }
    
  } catch (err) {
    addChatMessage("Sorry, I encountered an error. Please try again.", "bot");
  }
}

async function analyzeResumeForChatbot() {
  const resumeInput = document.getElementById("chatbot-resume");
  const file = resumeInput.files[0];
  
  if (!file) {
    alert("Please select a resume file first.");
    return;
  }
  
  if (file.type !== "application/pdf") {
    alert("Only PDF files are supported.");
    return;
  }
  
  currentResumeFile = file;
  addChatMessage("Resume uploaded! You can now ask me specific questions about your resume.", "bot");
  
  // Get initial analysis
  try {
    const response = await api.chatWithBotAndResume("Analyze my resume", file);
    addChatMessage(response.answer, "bot");
    
    if (response.analysis) {
      showAnalysisInChat(response.analysis);
    }
  } catch (err) {
    addChatMessage("Failed to analyze resume. Please try again.", "bot");
  }
}

function addChatMessage(message, sender) {
  const messagesContainer = document.getElementById("chatbot-messages");
  const messageDiv = document.createElement("div");
  messageDiv.className = sender === "user" ? "user-message" : "bot-message";
  messageDiv.textContent = message;
  
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showAnalysisInChat(analysis) {
  const messagesContainer = document.getElementById("chatbot-messages");
  
  // Skills analysis
  if (analysis.skills_found && Object.keys(analysis.skills_found).length > 0) {
    const skillsDiv = document.createElement("div");
    skillsDiv.className = "chatbot-analysis";
    skillsDiv.innerHTML = `
      <h5>🔍 Skills Found</h5>
      ${Object.entries(analysis.skills_found).map(([category, skills]) => `
        <div class="skill-category">
          <strong>${category.replace('_', ' ').title()}:</strong>
          <div class="skills-list">${skills.join(", ")}</div>
        </div>
      `).join('')}
    `;
    messagesContainer.appendChild(skillsDiv);
  }
  
  // Quality scores
  if (analysis.quality_scores) {
    const qualityDiv = document.createElement("div");
    qualityDiv.className = "chatbot-analysis";
    qualityDiv.innerHTML = `
      <h5>📊 Resume Quality Scores</h5>
      <div>Overall Score: ${analysis.quality_scores.overall_score}/10</div>
      <div>Action Verbs: ${analysis.quality_scores.action_score}/10</div>
      <div>Quantifiable Results: ${analysis.quality_scores.quant_score}/10</div>
      <div>Structure: ${analysis.quality_scores.structure_score}/10</div>
    `;
    messagesContainer.appendChild(qualityDiv);
  }
  
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function loadProfile() {
  try {
    const profile = await api.getStudentProfile();
    if (profile && profile.profile_completion !== undefined) {
      updateProfileCompletion(profile);
      
      // Fill form with existing data
      if (profile.full_name) {
        document.getElementById("profile-name").value = profile.full_name;
      }
      if (profile.skills) {
        document.getElementById("profile-skills").value = profile.skills;
      }
      if (profile.cgpa) {
        document.getElementById("profile-cgpa").value = profile.cgpa;
      }
      
      loadProfilePreview(profile);
    }
  } catch (err) {
    console.error("Failed to load profile:", err);
  }
}

async function loadMatchedJobs() {
  const c = document.getElementById("matched-jobs-list");
  c.innerHTML = '<p class="loading">Loading matched jobs...</p>';
  try {
    const response = await api.getMatchedJobs();
    const jobs = response.matched_jobs || [];
    
    if (!jobs.length) { 
      c.innerHTML = '<p class="info">No jobs match your profile above 70%. Try updating your profile with more skills.</p>'; 
      return; 
    }

    c.innerHTML = jobs.map((job) => {
      const matchClass = job.match_percentage >= 85 ? 'high' : job.match_percentage >= 75 ? 'medium' : 'low';
      return `<div class="list-item">
        <div class="list-item-header">
          <strong>${job.title}</strong>
          <span class="match-badge ${matchClass}">${job.match_percentage}% Match</span>
        </div>
        <div class="list-item-body">
          <strong>Requirements:</strong> ${job.requirements}<br>
          <strong>Min CGPA:</strong> ${job.min_cgpa}<br>
          <strong>Your Skills Match:</strong> ${job.matched_skills.join(", ") || "None"}
        </div>
        <div class="list-item-footer">
          <button class="btn-primary btn-sm" onclick="applyForJob(${job.id})">Apply Now</button>
          <span class="badge ${job.cgpa_eligible ? 'badge-success' : 'badge-danger'}">
            ${job.cgpa_eligible ? 'CGPA Eligible' : 'CGPA Not Eligible'}
          </span>
        </div>
      </div>`;
    }).join("");
  } catch (e) { 
    c.innerHTML = `<p class="error">Error: ${e.message}</p>`; 
  }
}

async function applyForJob(jobId) {
  try {
    const result = await api.applyForJob(jobId);
    alert(`Application submitted successfully! Match: ${result.match_percentage}%`);
    loadApplications(); // Refresh applications list
  } catch (err) {
    alert("Error applying for job: " + err.message);
  }
}

async function loadApplications() {
  const c = document.getElementById("applications-list");
  c.innerHTML = '<p class="loading">Loading applications...</p>';
  try {
    const response = await api.getMyApplications();
    const applications = response.applications || [];
    
    if (!applications.length) { 
      c.innerHTML = '<p class="info">No job applications yet. Apply for jobs that match 70% or higher.</p>'; 
      return; 
    }

    c.innerHTML = applications.map((app) => {
      const statusClass = app.status === 'accepted' ? 'badge-success' : 
                         app.status === 'rejected' ? 'badge-danger' : 'badge-warning';
      return `<div class="list-item">
        <div class="list-item-header">
          <strong>${app.job_title}</strong>
          <span class="badge ${statusClass}">${app.status}</span>
        </div>
        <div class="list-item-body">
          <strong>Applied:</strong> ${new Date(app.applied_at).toLocaleDateString()}<br>
          <strong>Match Percentage:</strong> ${app.match_percentage}%
        </div>
      </div>`;
    }).join("");
  } catch (e) { 
    c.innerHTML = `<p class="error">Error: ${e.message}</p>`; 
  }
}

async function startAIReview() {
  const resultsEl = document.getElementById("ai-review-results");
  const btn = document.getElementById("start-ai-review");
  
  btn.disabled = true;
  btn.textContent = "Analyzing...";
  resultsEl.innerHTML = '<p class="loading">AI is analyzing your resume...</p>';
  
  try {
    const results = await api.aiResumeReview();
    
    const scoreClass = results.overall_score >= 8 ? 'excellent' : 
                      results.overall_score >= 6 ? 'good' : 
                      results.overall_score >= 4 ? 'fair' : 'poor';
    
    resultsEl.innerHTML = `
      <div class="ai-score ${scoreClass}">${results.overall_score}/10</div>
      
      <div class="ai-section">
        <h5>🎯 Strengths</h5>
        <ul>
          ${results.strengths.map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>
      
      <div class="ai-section">
        <h5>📈 Areas for Improvement</h5>
        <ul>
          ${results.improvements.map(i => `<li>${i}</li>`).join('')}
        </ul>
      </div>
      
      <div class="ai-section">
        <h5>🛠️ Formatting Tips</h5>
        <ul>
          ${results.formatting_tips.map(tip => `<li>${tip}</li>`).join('')}
        </ul>
      </div>
      
      <div class="ai-section">
        <h5>📋 Next Steps</h5>
        <ul>
          ${results.next_steps.map(step => `<li>${step}</li>`).join('')}
        </ul>
      </div>
    `;
  } catch (err) {
    resultsEl.innerHTML = `<p class="error">Error: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Start AI Review";
  }
}

async function loadNotifications() {
  try {
    const notifications = await api.getNotifications();
    const notificationsList = document.getElementById("notifications-list");
    const notificationCount = document.getElementById("notification-count");
    
    const unreadNotifications = notifications.filter(n => !n.is_read);
    notificationCount.textContent = unreadNotifications.length;
    notificationCount.style.display = unreadNotifications.length > 0 ? 'inline' : 'none';
    
    if (!notifications.length) {
      notificationsList.innerHTML = '<p class="no-notifications">No new notifications</p>';
      return;
    }
    
    notificationsList.innerHTML = notifications.map(n => `
      <div class="notification-item ${!n.is_read ? 'unread' : ''}" onclick="markNotificationRead(${n.id})">
        <div>${n.message}</div>
        <div class="notification-time">${new Date(n.created_at).toLocaleString()}</div>
      </div>
    `).join('');
  } catch (err) {
    console.error("Failed to load notifications:", err);
  }
}

async function markNotificationRead(notificationId) {
  try {
    await api.markNotificationRead(notificationId);
    loadNotifications();
  } catch (err) {
    console.error("Failed to mark notification as read:", err);
  }
}

async function markAllNotificationsRead() {
  try {
    await api.markAllNotificationsRead();
    loadNotifications();
  } catch (err) {
    console.error("Failed to mark all notifications as read:", err);
  }
}

function loadProfilePreview(data) {
  const el = document.getElementById("profile-preview");
  if (!el) return;
  const skills = data.skills.split(",").map((s) => s.trim()).filter(Boolean);
  el.innerHTML = `
    <div class="profile-card">
      <h3>${data.name}</h3>
      <div class="profile-detail">CGPA: ${data.cgpa}</div>
      <div class="profile-skills">${skills.map((s) => `<span class="skill-tag">${s}</span>`).join("")}</div>
    </div>
  `;
}

async function loadStats() {
  const el = document.getElementById("student-stats");
  if (!el) return;
  try {
    const d = await api.studentDashboard();
    const s = d.stats || {};
    el.innerHTML = `
      <div class="stat-card"><span class="stat-value">${s.available_jobs ?? 0}</span><span class="stat-label">Available Jobs</span></div>
    `;
  } catch (e) { el.innerHTML = ""; }
}

async function loadJobs() {
  const c = document.getElementById("jobs-list");
  c.innerHTML = '<p class="loading">Loading jobs...</p>';
  try {
    const jobs = await api.getJobs();
    if (!jobs.length) { c.innerHTML = '<p class="info">No jobs available at the moment.</p>'; return; }

    const myCgpa = parseFloat(localStorage.getItem("student_cgpa") || "0");
    const mySkills = (localStorage.getItem("student_skills") || "")
      .toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);

    c.innerHTML = jobs.map((j) => {
      let eligibility = "";
      if (myCgpa > 0) {
        const meetsGpa = myCgpa >= j.min_cgpa;
        const reqSkills = (j.requirements || "").toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);
        const matched = reqSkills.filter((s) => mySkills.includes(s));
        const matchPct = reqSkills.length ? Math.round((matched.length / reqSkills.length) * 100) : 0;

        if (meetsGpa && matchPct >= 50) {
          eligibility = `<span class="badge badge-success">Eligible (${matchPct}% skill match)</span>`;
        } else if (meetsGpa) {
          eligibility = `<span class="badge badge-warning">CGPA OK, ${matchPct}% skill match</span>`;
        } else {
          eligibility = `<span class="badge badge-danger" style="background:#dc3545">CGPA below ${j.min_cgpa}</span>`;
        }
      }

      return `<div class="list-item">
        <div class="list-item-header"><strong>${j.title}</strong><span class="badge">Min CGPA: ${j.min_cgpa}</span></div>
        <div class="list-item-body">Requirements: ${j.requirements || "N/A"}</div>
        ${eligibility ? `<div class="list-item-footer">${eligibility}</div>` : ""}
      </div>`;
    }).join("");
  } catch (e) { c.innerHTML = `<p class="error">Error: ${e.message}</p>`; }
}

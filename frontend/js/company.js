document.addEventListener("DOMContentLoaded", () => {
  // Tab switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`${btn.dataset.tab}-tab`).classList.add("active");
      if (btn.dataset.tab === "applicants") loadJobsForApplicants();
    });
  });

  loadCompanyProfile();
  loadStats();
  loadMyJobs();
  loadJobsForShortlist();

  // Company profile save
  document.getElementById("company-profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
      company_name: document.getElementById("profile-company-name").value,
      manager_name: document.getElementById("profile-manager-name").value,
      designation: document.getElementById("profile-designation").value,
    };
    const msg = document.getElementById("company-profile-message");
    try {
      await api.createOrUpdateCompanyProfile(data);
      msg.textContent = "Profile saved successfully!";
      msg.style.color = "green";
      setTimeout(() => { msg.textContent = ""; }, 3000);
      loadStats();
    } catch (err) {
      msg.textContent = "Error: " + err.message;
      msg.style.color = "red";
    }
  });

  // Post job
  document.getElementById("post-job-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("job-title").value;
    const skills = document.getElementById("job-skills").value;
    const cgpa = document.getElementById("job-min-cgpa").value;
    const topN = document.getElementById("job-top-n").value;
    if (!validateNotEmpty(title)) { showFormError(e.target, "Job title is required."); return; }
    if (!validateNotEmpty(skills)) { showFormError(e.target, "At least one skill is required."); return; }
    if (!validateCGPA(cgpa)) { showFormError(e.target, "CGPA must be between 0 and 10."); return; }
    try {
      await api.addJob({
        title,
        requirements: skills.split(",").map((s) => s.trim()).join(", "),
        min_cgpa: parseFloat(cgpa),
        top_n: parseInt(topN) || 10,
      });
      alert("Job posted successfully!");
      e.target.reset();
      loadMyJobs();
      loadStats();
      loadJobsForShortlist();
      loadJobsForApplicants();
    } catch (err) {
      showFormError(e.target, err.message);
    }
  });

  // Shortlist form
  document.getElementById("shortlist-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const jobId = document.getElementById("shortlist-job-select").value;
    if (!jobId) { showFormError(e.target, "Please select a job first."); return; }
    try {
      const data = await api.companyShortlist(jobId);
      renderShortlist(data);
    } catch (err) {
      document.getElementById("shortlist-results").innerHTML = `<p class="error">Error: ${err.message}</p>`;
    }
  });

  // Load applicants button
  document.getElementById("load-applicants-btn").addEventListener("click", async () => {
    const jobId = document.getElementById("applicant-job-select").value;
    if (!jobId) { alert("Please select a job first."); return; }
    loadApplicants(jobId);
  });

  document.getElementById("refresh-jobs").addEventListener("click", loadMyJobs);
});

// ─── Stats ───────────────────────────────────────────────────────────────────
async function loadStats() {
  const el = document.getElementById("company-stats");
  if (!el) return;
  try {
    const d = await api.companyDashboard();
    const s = d.stats || {};
    el.innerHTML = `
      <div class="stat-card"><span class="stat-value">${s.my_jobs ?? 0}</span><span class="stat-label">My Jobs</span></div>
      <div class="stat-card"><span class="stat-value">${s.total_jobs_posted ?? 0}</span><span class="stat-label">Total Jobs</span></div>
    `;
  } catch (e) { el.innerHTML = ""; }
}

// ─── My Jobs ─────────────────────────────────────────────────────────────────
async function loadMyJobs() {
  const c = document.getElementById("jobs-list");
  c.innerHTML = '<p class="loading">Loading your jobs...</p>';
  try {
    const jobs = await api.getMyJobs();
    if (!jobs.length) { c.innerHTML = '<p class="info">You haven\'t posted any jobs yet.</p>'; return; }
    c.innerHTML = jobs.map((j) => `
      <div class="list-item">
        <div class="list-item-header"><strong>${j.title}</strong><span class="badge">Min CGPA: ${j.min_cgpa}</span></div>
        <div class="list-item-body">Requirements: ${j.requirements || "N/A"}</div>
        <div class="list-item-footer">
          <button class="btn-primary btn-sm" onclick="viewApplicantsForJob(${j.id}, '${j.title.replace(/'/g, "\\'")}')">View Applicants</button>
        </div>
      </div>`).join("");
  } catch (e) { c.innerHTML = `<p class="error">Error: ${e.message}</p>`; }
}

function viewApplicantsForJob(jobId, jobTitle) {
  // Switch to applicants tab and load
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
  document.querySelector("[data-tab='applicants']").classList.add("active");
  document.getElementById("applicants-tab").classList.add("active");
  loadJobsForApplicants(() => {
    document.getElementById("applicant-job-select").value = jobId;
    loadApplicants(jobId);
  });
}

// ─── Applicants ───────────────────────────────────────────────────────────────
async function loadJobsForApplicants(cb) {
  const sel = document.getElementById("applicant-job-select");
  if (!sel) return;
  try {
    const jobs = await api.getMyJobs();
    sel.innerHTML = '<option value="">— Select a job to view applicants —</option>' +
      jobs.map((j) => `<option value="${j.id}">${j.title}</option>`).join("");
    if (cb) cb();
  } catch (e) { sel.innerHTML = '<option value="">Error loading jobs</option>'; }
}

const STATUS_LABELS = {
  applied: "📋 Applied",
  under_review: "🔍 Under Review",
  shortlisted: "⭐ Shortlisted",
  interview: "📅 Interview Scheduled",
  rejected: "❌ Rejected",
  offer: "🎉 Offer Sent",
};

async function loadApplicants(jobId) {
  const c = document.getElementById("applicants-list");
  c.innerHTML = '<p class="loading">Loading applicants...</p>';
  try {
    const data = await api.getJobApplicants(jobId);
    if (!data.applicants || !data.applicants.length) {
      c.innerHTML = '<p class="info">No applicants yet for this job.</p>';
      return;
    }
    c.innerHTML = `<h4 style="margin-bottom:12px;">${data.job_title} — ${data.total_applicants} Applicant(s)</h4>` +
      data.applicants.map((a) => {
        const statusClass = `status-${a.status}`;
        const statusLabel = STATUS_LABELS[a.status] || a.status;
        const interviewHtml = a.interview ? `
          <div style="background:#f3e5f5;padding:8px 12px;border-radius:8px;margin-top:8px;font-size:13px;">
            📅 <strong>Interview:</strong> ${a.interview.date} at ${a.interview.time} — ${a.interview.mode}
            ${a.interview.link ? `| <a href="${a.interview.link}" target="_blank">Join</a>` : ""}
          </div>` : "";
        const offerHtml = a.offer ? `
          <div style="background:#e8f5e9;padding:8px 12px;border-radius:8px;margin-top:8px;font-size:13px;">
            🎉 <strong>Offer Sent:</strong> ${a.offer.position} — CTC: ${a.offer.ctc}
            <span class="status-badge" style="margin-left:6px;">${a.offer.status}</span>
          </div>` : "";
        return `
          <div class="applicant-card">
            <div class="applicant-header">
              <div>
                <strong>${a.student_name}</strong>
                <span style="color:#666;font-size:13px;margin-left:8px;">${a.student_email}</span>
              </div>
              <span class="status-badge ${statusClass}">${statusLabel}</span>
            </div>
            <div style="font-size:13px;color:#444;margin-bottom:6px;">
              CGPA: <strong>${a.student_cgpa}</strong> &nbsp;|&nbsp;
              Match: <strong>${a.match_percentage}%</strong> &nbsp;|&nbsp;
              Skills: ${a.student_skills || "N/A"}
              ${a.resume_url ? ` &nbsp;|&nbsp; <a href="${api.getFileUrl(a.resume_url)}" target="_blank">📄 Resume</a>` : ""}
            </div>
            ${interviewHtml}
            ${offerHtml}
            <div class="action-btns">
              <button class="btn-xs btn-review" onclick="updateStatus(${a.application_id}, 'under_review', ${jobId})">🔍 Under Review</button>
              <button class="btn-xs btn-shortlist" onclick="updateStatus(${a.application_id}, 'shortlisted', ${jobId})">⭐ Shortlist</button>
              <button class="btn-xs btn-interview" onclick="openInterviewModal(${a.application_id})">📅 Schedule Interview</button>
              <button class="btn-xs btn-offer" onclick="openOfferModal(${a.application_id})">🎉 Send Offer</button>
              <button class="btn-xs btn-reject" onclick="updateStatus(${a.application_id}, 'rejected', ${jobId})">❌ Reject</button>
            </div>
          </div>`;
      }).join("");
  } catch (e) { c.innerHTML = `<p class="error">Error: ${e.message}</p>`; }
}

async function updateStatus(appId, status, jobId) {
  try {
    await api.updateApplicationStatus(appId, status);
    loadApplicants(jobId);
  } catch (e) { alert("Error: " + e.message); }
}

// ─── Interview Modal ──────────────────────────────────────────────────────────
function openInterviewModal(appId) {
  document.getElementById("interview-app-id").value = appId;
  // Default to tomorrow
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById("interview-date").value = tomorrow.toISOString().split("T")[0];
  document.getElementById("interview-time").value = "10:00";
  document.getElementById("interview-link").value = "";
  document.getElementById("interview-notes").value = "";
  document.getElementById("interview-modal").classList.add("open");
}

async function submitInterview() {
  const appId = document.getElementById("interview-app-id").value;
  const data = {
    interview_date: document.getElementById("interview-date").value,
    interview_time: document.getElementById("interview-time").value,
    mode: document.getElementById("interview-mode").value,
    link: document.getElementById("interview-link").value || null,
    notes: document.getElementById("interview-notes").value || null,
  };
  if (!data.interview_date || !data.interview_time) { alert("Date and time are required."); return; }
  try {
    await api.scheduleInterview(appId, data);
    closeModal("interview-modal");
    alert("Interview scheduled successfully! The student has been notified.");
    const jobId = document.getElementById("applicant-job-select").value;
    if (jobId) loadApplicants(jobId);
  } catch (e) { alert("Error: " + e.message); }
}

// ─── Offer Modal ──────────────────────────────────────────────────────────────
function openOfferModal(appId) {
  document.getElementById("offer-app-id").value = appId;
  document.getElementById("offer-position").value = "";
  document.getElementById("offer-ctc").value = "";
  document.getElementById("offer-modal").classList.add("open");
}

async function submitOffer() {
  const appId = document.getElementById("offer-app-id").value;
  const position = document.getElementById("offer-position").value.trim();
  const ctc = document.getElementById("offer-ctc").value.trim();
  if (!position || !ctc) { alert("Position and CTC are required."); return; }
  try {
    await api.sendOffer(appId, { position, ctc });
    closeModal("offer-modal");
    alert("Offer sent! The student has been notified via dashboard and email.");
    const jobId = document.getElementById("applicant-job-select").value;
    if (jobId) loadApplicants(jobId);
  } catch (e) { alert("Error: " + e.message); }
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}
// Close modal on backdrop click
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("open");
  }
});

// ─── Shortlist Tool ───────────────────────────────────────────────────────────
async function loadJobsForShortlist() {
  const sel = document.getElementById("shortlist-job-select");
  if (!sel) return;
  try {
    const jobs = await api.getMyJobs();
    sel.innerHTML = '<option value="">Select one of your jobs</option>' +
      jobs.map((j) => `<option value="${j.id}">${j.title}</option>`).join("");
  } catch (e) { sel.innerHTML = '<option value="">Error loading</option>'; }
}

function renderShortlist(data) {
  const c = document.getElementById("shortlist-results");
  if (!data.results || !data.results.length) { c.innerHTML = '<p class="info">No matching candidates.</p>'; return; }
  c.innerHTML = `<h4>Shortlist for: ${data.job}</h4>` + data.results.map((r, i) => `
    <div class="list-item">
      <div class="list-item-header"><strong>#${i + 1}. ${r.name}</strong><span class="badge badge-success">Score: ${Number(r.score || 0).toFixed(2)}</span></div>
      <div class="list-item-body">
        CGPA: ${r.cgpa} | Skills: ${r.skills || "N/A"}
        ${r.resume_url ? ` | <a href="${api.getFileUrl(r.resume_url)}" target="_blank" rel="noopener noreferrer">View Resume</a>` : ""}
      </div>
    </div>`).join("");
}

// ─── Company Profile ──────────────────────────────────────────────────────────
async function loadCompanyProfile() {
  try {
    const profile = await api.getCompanyProfile();
    if (profile) {
      document.getElementById("profile-company-name").value = profile.company_name || "";
      document.getElementById("profile-manager-name").value = profile.manager_name || "";
      document.getElementById("profile-designation").value = profile.designation || "";
    }
  } catch (err) { console.log("No profile found or error loading profile."); }
}

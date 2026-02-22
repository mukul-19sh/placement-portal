document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`${btn.dataset.tab}-tab`).classList.add("active");
    });
  });

  document.getElementById("post-job-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("job-title").value;
    const skills = document.getElementById("job-skills").value;
    const cgpa = document.getElementById("job-min-cgpa").value;
    const topN = document.getElementById("job-top-n").value;

    if (!validateNotEmpty(title)) { showFormError(e.target, "Job title is required."); return; }
    if (!validateNotEmpty(skills)) { showFormError(e.target, "At least one skill is required."); return; }
    if (!validateCGPA(cgpa)) { showFormError(e.target, "CGPA must be between 0 and 10."); return; }

    const data = {
      title,
      requirements: skills.split(",").map((s) => s.trim()).join(", "),
      min_cgpa: parseFloat(cgpa),
      top_n: parseInt(topN) || 10,
    };
    try {
      await api.addJob(data);
      alert("Job posted successfully!");
      e.target.reset();
      loadMyJobs();
      loadStats();
      loadJobsForShortlist();
    } catch (err) {
      showFormError(e.target, err.message);
    }
  });

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

  document.getElementById("refresh-jobs").addEventListener("click", loadMyJobs);

  loadStats();
  loadMyJobs();
  loadJobsForShortlist();
});

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
      </div>`).join("");
  } catch (e) { c.innerHTML = `<p class="error">Error: ${e.message}</p>`; }
}

async function loadJobsForShortlist() {
  const sel = document.getElementById("shortlist-job-select");
  if (!sel) return;
  try {
    const jobs = await api.getMyJobs();
    sel.innerHTML = '<option value="">Select one of your jobs</option>' + jobs.map((j) => `<option value="${j.id}">${j.title}</option>`).join("");
  } catch (e) { sel.innerHTML = '<option value="">Error loading</option>'; }
}

function renderShortlist(data) {
  const c = document.getElementById("shortlist-results");
  if (!data.results || !data.results.length) { c.innerHTML = '<p class="info">No matching candidates.</p>'; return; }
  c.innerHTML = `<h4>Shortlist for: ${data.job}</h4>` + data.results.map((r, i) => `
    <div class="list-item">
      <div class="list-item-header"><strong>#${i + 1}. ${r.name}</strong><span class="badge badge-success">Score: ${Number(r.score || 0).toFixed(2)}</span></div>
      <div class="list-item-body">CGPA: ${r.cgpa} | Skills: ${r.skills || "N/A"}</div>
    </div>`).join("");
}

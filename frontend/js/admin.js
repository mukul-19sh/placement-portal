document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`${btn.dataset.tab}-tab`).classList.add("active");
    });
  });

  document.getElementById("add-student-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("student-name").value;
    const skills = document.getElementById("student-skills").value;
    const cgpa = document.getElementById("student-cgpa").value;

    if (!validateNotEmpty(name)) { showFormError(e.target, "Student name is required."); return; }
    if (!validateNotEmpty(skills)) { showFormError(e.target, "At least one skill is required."); return; }
    if (!validateCGPA(cgpa)) { showFormError(e.target, "CGPA must be between 0 and 10."); return; }

    const data = {
      name,
      skills: skills.split(",").map((s) => s.trim()).join(", "),
      cgpa: parseFloat(cgpa),
    };
    try {
      await api.addStudent(data);
      alert("Student added successfully!");
      e.target.reset();
      loadStudents();
      loadStats();
    } catch (err) {
      showFormError(e.target, err.message);
    }
  });

  document.getElementById("add-job-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("job-title").value;
    const skills = document.getElementById("job-skills").value;
    const cgpa = document.getElementById("job-min-cgpa").value;

    if (!validateNotEmpty(title)) { showFormError(e.target, "Job title is required."); return; }
    if (!validateNotEmpty(skills)) { showFormError(e.target, "At least one skill is required."); return; }
    if (!validateCGPA(cgpa)) { showFormError(e.target, "CGPA must be between 0 and 10."); return; }

    const data = {
      title,
      requirements: skills.split(",").map((s) => s.trim()).join(", "),
      min_cgpa: parseFloat(cgpa),
      top_n: parseInt(document.getElementById("job-top-n").value) || 10,
    };
    try {
      await api.addJob(data);
      alert("Job added successfully!");
      e.target.reset();
      loadJobs();
      loadJobsForShortlist();
      loadStats();
    } catch (err) {
      showFormError(e.target, err.message);
    }
  });

  document.getElementById("shortlist-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const jobId = document.getElementById("shortlist-job-select").value;
    if (!jobId) { showFormError(e.target, "Please select a job first."); return; }
    try {
      const data = await api.shortlist(jobId);
      renderShortlist(data);
    } catch (err) {
      document.getElementById("shortlist-results").innerHTML = `<p class="error">Error: ${err.message}</p>`;
    }
  });

  document.getElementById("refresh-students").addEventListener("click", loadStudents);
  document.getElementById("refresh-jobs").addEventListener("click", loadJobs);

  loadStats();
  loadStudents();
  loadJobs();
  loadJobsForShortlist();
});

async function loadStats() {
  const el = document.getElementById("admin-stats");
  if (!el) return;
  try {
    const d = await api.adminDashboard();
    const s = d.stats || {};
    el.innerHTML = `
      <div class="stat-card"><span class="stat-value">${s.total_students ?? 0}</span><span class="stat-label">Students</span></div>
      <div class="stat-card"><span class="stat-value">${s.total_jobs ?? 0}</span><span class="stat-label">Jobs</span></div>
    `;
  } catch (e) { el.innerHTML = ""; }
}

async function loadStudents() {
  const c = document.getElementById("students-list");
  c.innerHTML = '<p class="loading">Loading students...</p>';
  try {
    const students = await api.getStudents();
    if (!students.length) { c.innerHTML = '<p class="info">No students found.</p>'; return; }
    c.innerHTML = students.map((s) => `
      <div class="list-item">
        <div class="list-item-header"><strong>${s.name}</strong><span class="badge">CGPA: ${s.cgpa}</span></div>
        <div class="list-item-body">Skills: ${s.skills || "N/A"}</div>
      </div>`).join("");
  } catch (e) { c.innerHTML = `<p class="error">Error: ${e.message}</p>`; }
}

async function loadJobs() {
  const c = document.getElementById("jobs-list");
  c.innerHTML = '<p class="loading">Loading jobs...</p>';
  try {
    const jobs = await api.getJobs();
    if (!jobs.length) { c.innerHTML = '<p class="info">No jobs found.</p>'; return; }
    c.innerHTML = jobs.map((j) => `
      <div class="list-item">
        <div class="list-item-header"><strong>${j.title}</strong><span class="badge">Min CGPA: ${j.min_cgpa}</span></div>
        <div class="list-item-body">Requirements: ${j.requirements || "N/A"}</div>
        ${j.created_by ? `<div class="list-item-footer"><small>Posted by: ${j.created_by}</small></div>` : ""}
      </div>`).join("");
  } catch (e) { c.innerHTML = `<p class="error">Error: ${e.message}</p>`; }
}

async function loadJobsForShortlist() {
  const sel = document.getElementById("shortlist-job-select");
  try {
    const jobs = await api.getJobs();
    sel.innerHTML = '<option value="">Select a job</option>' + jobs.map((j) => `<option value="${j.id}">${j.title}</option>`).join("");
  } catch (e) { sel.innerHTML = '<option value="">Error loading jobs</option>'; }
}

function renderShortlist(data) {
  const c = document.getElementById("shortlist-results");
  if (!data.results || !data.results.length) { c.innerHTML = '<p class="info">No matching students found.</p>'; return; }
  c.innerHTML = `<h4>Shortlist for: ${data.job}</h4>` + data.results.map((r, i) => `
    <div class="list-item">
      <div class="list-item-header"><strong>#${i + 1}. ${r.name}</strong><span class="badge badge-success">Score: ${Number(r.score || 0).toFixed(2)}</span></div>
      <div class="list-item-body">CGPA: ${r.cgpa} | Skills: ${r.skills || "N/A"}</div>
    </div>`).join("");
}

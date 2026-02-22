document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`${btn.dataset.tab}-tab`).classList.add("active");
    });
  });

  document.getElementById("profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("profile-name").value;
    const skills = document.getElementById("profile-skills").value;
    const cgpa = document.getElementById("profile-cgpa").value;

    if (!validateNotEmpty(name)) { showFormError(e.target, "Name is required."); return; }
    if (!validateNotEmpty(skills)) { showFormError(e.target, "At least one skill is required."); return; }
    if (!validateCGPA(cgpa)) { showFormError(e.target, "CGPA must be between 0 and 10."); return; }

    const data = {
      name,
      skills: skills.split(",").map((s) => s.trim()).join(", "),
      cgpa: parseFloat(cgpa),
    };
    const msg = document.getElementById("profile-message");
    try {
      await api.addStudent(data);
      msg.textContent = "Profile saved successfully!";
      msg.className = "success-message";
      msg.style.display = "block";
      localStorage.setItem("student_cgpa", data.cgpa);
      localStorage.setItem("student_skills", data.skills);
      loadStats();
      loadProfilePreview(data);
    } catch (err) {
      msg.textContent = "Error: " + err.message;
      msg.className = "error-message";
      msg.style.display = "block";
    }
  });

  document.getElementById("refresh-jobs").addEventListener("click", loadJobs);

  loadStats();
  loadJobs();
});

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

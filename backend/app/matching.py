def score_student_for_job(student, job):
    student_skills = set([s.strip().lower() for s in student.skills.split(",")])
    job_reqs = [r.strip().lower() for r in job.requirements.split(",")]

    matched = student_skills.intersection(job_reqs)
    missing = set(job_reqs) - student_skills

    skill_score = len(matched) * 15   # heavier weight
    cgpa_score = student.cgpa * 2     # scaled

    total_score = skill_score + cgpa_score

    return {
        "score": total_score,
        "matched_skills": list(matched),
        "missing_skills": list(missing)
    }

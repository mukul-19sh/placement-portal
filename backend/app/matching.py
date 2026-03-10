def score_student_for_job(student, job):
    student_skills = set([s.strip().lower() for s in student.skills.split(",")])
    job_reqs = [r.strip().lower() for r in job.requirements.split(",")]

    matched = student_skills.intersection(job_reqs)
    missing = set(job_reqs) - student_skills

    # Calculate percentage match
    total_requirements = len(job_reqs)
    skill_match_percentage = (len(matched) / total_requirements * 100) if total_requirements > 0 else 0
    
    # CGPA eligibility check
    cgpa_eligible = student.cgpa >= job.min_cgpa
    
    skill_score = len(matched) * 15   # heavier weight
    cgpa_score = student.cgpa * 2     # scaled

    total_score = skill_score + cgpa_score

    return {
        "score": total_score,
        "matched_skills": list(matched),
        "missing_skills": list(missing),
        "skill_match_percentage": round(skill_match_percentage, 1),
        "cgpa_eligible": cgpa_eligible,
        "overall_match_percentage": calculate_overall_match(skill_match_percentage, cgpa_eligible)
    }


def calculate_overall_match(skill_percentage, cgpa_eligible):
    """Calculate overall match percentage considering skills and CGPA."""
    if not cgpa_eligible:
        return min(skill_percentage - 20, 50)  # Penalty for CGPA ineligibility
    return skill_percentage


def is_job_match(student, job, threshold=70):
    """Check if student matches job requirements above threshold."""
    scoring = score_student_for_job(student, job)
    return scoring["overall_match_percentage"] >= threshold

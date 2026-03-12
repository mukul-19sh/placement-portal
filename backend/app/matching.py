import re

def normalize_skill(skill):
    return re.sub(r'[^a-z0-9]', '', skill.lower())

def score_student_for_job(student, job):
    student_skills_raw = [s.strip().lower() for s in student.skills.split(",") if s.strip()]
    job_reqs_raw = [r.strip().lower() for r in job.requirements.split(",") if r.strip()]

    matched = []
    missing = []
    
    student_skills_norm = [normalize_skill(s) for s in student_skills_raw]
    
    for req in job_reqs_raw:
        req_norm = normalize_skill(req)
        is_match = False
        for student_norm in student_skills_norm:
            if req_norm == student_norm or req_norm in student_norm or student_norm in req_norm:
                is_match = True
                break
        if is_match:
            matched.append(req)
        else:
            missing.append(req)

    # Calculate percentage match
    total_requirements = len(job_reqs_raw)
    skill_match_percentage = (len(matched) / total_requirements * 100) if total_requirements > 0 else 100
    
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

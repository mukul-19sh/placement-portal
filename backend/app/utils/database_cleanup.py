"""
Database cleanup utilities for removing old/duplicate data.
"""
from sqlalchemy.orm import Session
from ..models import Student, StudentUser, CompanyUser, AdminUser, EmailVerificationToken
from typing import List, Dict


def cleanup_duplicate_students(db: Session) -> Dict[str, int]:
    """
    Remove duplicate student profiles, keeping only the most recent one per email.
    Returns cleanup statistics.
    """
    # Find all students grouped by email
    students_by_email = db.query(Student).all()
    email_groups = {}
    
    for student in students_by_email:
        if student.owner_email not in email_groups:
            email_groups[student.owner_email] = []
        email_groups[student.owner_email].append(student)
    
    removed_count = 0
    kept_count = 0
    
    for email, students in email_groups.items():
        if len(students) > 1:
            # Sort by ID (assuming higher ID = more recent)
            students.sort(key=lambda x: x.id if x.id else 0, reverse=True)
            
            # Keep the first (most recent), delete the rest
            for student in students[1:]:
                db.delete(student)
                removed_count += 1
            
            kept_count += 1
        else:
            kept_count += 1
    
    db.commit()
    
    return {
        "removed_profiles": removed_count,
        "kept_profiles": kept_count,
        "total_processed": len(students_by_email)
    }


def cleanup_unverified_users(db: Session, days_old: int = 30) -> Dict[str, int]:
    """
    Remove unverified users older than specified days.
    Returns cleanup statistics.
    """
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Get unverified users with old tokens
    old_tokens = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.expires_at < cutoff_date,
        EmailVerificationToken.used == False
    ).all()
    
    removed_users = 0
    removed_tokens = 0
    
    for token in old_tokens:
        # Find and remove the associated user
        email = token.email
        role = token.role
        
        if role == "student":
            user = db.query(StudentUser).filter(StudentUser.email == email).first()
        elif role == "company":
            user = db.query(CompanyUser).filter(CompanyUser.email == email).first()
        elif role == "admin":
            user = db.query(AdminUser).filter(AdminUser.email == email).first()
        else:
            user = None
        
        if user:
            db.delete(user)
            removed_users += 1
        
        db.delete(token)
        removed_tokens += 1
    
    db.commit()
    
    return {
        "removed_users": removed_users,
        "removed_tokens": removed_tokens,
        "cutoff_days": days_old
    }


def cleanup_orphaned_profiles(db: Session) -> int:
    """
    Remove student profiles that don't have corresponding user accounts.
    Returns number of removed profiles.
    """
    # Get all student emails that have user accounts
    student_users = db.query(StudentUser.email).all()
    valid_emails = {email[0] for email in student_users}
    
    # Find orphaned student profiles
    orphaned_profiles = db.query(Student).filter(
        Student.owner_email.notin_(valid_emails)
    ).all()
    
    removed_count = len(orphaned_profiles)
    
    for profile in orphaned_profiles:
        db.delete(profile)
    
    db.commit()
    
    return removed_count


def get_database_stats(db: Session) -> Dict[str, int]:
    """
    Get current database statistics.
    """
    return {
        "students": db.query(Student).count(),
        "student_users": db.query(StudentUser).count(),
        "company_users": db.query(CompanyUser).count(),
        "admin_users": db.query(AdminUser).count(),
        "email_tokens": db.query(EmailVerificationToken).count(),
        "used_tokens": db.query(EmailVerificationToken).filter(EmailVerificationToken.used == True).count(),
        "unused_tokens": db.query(EmailVerificationToken).filter(EmailVerificationToken.used == False).count()
    }


def run_full_cleanup(db: Session) -> Dict[str, any]:
    """
    Run complete database cleanup and return comprehensive report.
    """
    # Get initial stats
    initial_stats = get_database_stats(db)
    
    # Run cleanup operations
    duplicate_cleanup = cleanup_duplicate_students(db)
    unverified_cleanup = cleanup_unverified_users(db, days_old=30)
    orphaned_cleanup = cleanup_orphaned_profiles(db)
    
    # Get final stats
    final_stats = get_database_stats(db)
    
    return {
        "initial_stats": initial_stats,
        "final_stats": final_stats,
        "cleanup_results": {
            "duplicate_profiles": duplicate_cleanup,
            "unverified_users": unverified_cleanup,
            "orphaned_profiles": orphaned_cleanup
        },
        "summary": {
            "total_removed": (
                duplicate_cleanup["removed_profiles"] +
                unverified_cleanup["removed_users"] +
                orphaned_cleanup
            ),
            "net_change": {
                "students": final_stats["students"] - initial_stats["students"],
                "student_users": final_stats["student_users"] - initial_stats["student_users"],
                "email_tokens": final_stats["email_tokens"] - initial_stats["email_tokens"]
            }
        }
    }

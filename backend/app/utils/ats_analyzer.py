import re
import json
from typing import Dict, List, Tuple, Set
from collections import Counter
import PyPDF2
from io import BytesIO


class ATSAnalyzer:
    """Advanced ATS (Applicant Tracking System) Resume Analyzer."""
    
    # Technical skills categories
    TECH_SKILLS = {
        'programming_languages': [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust'
        ],
        'web_technologies': [
            'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'spring', 'laravel', 'rails'
        ],
        'databases': [
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle', 'sqlite'
        ],
        'cloud_devops': [
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'terraform', 'ansible'
        ],
        'tools_frameworks': [
            'git', 'github', 'jira', 'slack', 'vscode', 'intellij', 'eclipse', 'webpack', 'babel'
        ]
    }
    
    # Action verbs for resume analysis
    ACTION_VERBS = [
        'developed', 'implemented', 'designed', 'created', 'built', 'led', 'managed', 'optimized',
        'improved', 'increased', 'reduced', 'achieved', 'launched', 'deployed', 'maintained',
        'collaborated', 'coordinated', 'analyzed', 'tested', 'debugged', 'refactored'
    ]
    
    # Quantitative indicators
    QUANTITATIVE_INDICATORS = [
        '%', 'percent', 'increase', 'decrease', 'growth', 'revenue', 'cost', 'time',
        'users', 'customers', 'clients', 'projects', 'team', 'employees', 'budget'
    ]
    
    def __init__(self):
        self.all_skills = [skill for category in self.TECH_SKILLS.values() for skill in category]
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content."""
        try:
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.lower()
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract and categorize skills from resume text."""
        found_skills = {}
        
        for category, skills in self.TECH_SKILLS.items():
            category_skills = []
            for skill in skills:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, text, re.IGNORECASE):
                    category_skills.append(skill)
            
            if category_skills:
                found_skills[category] = category_skills
        
        return found_skills
    
    def calculate_skill_score(self, resume_skills: Dict[str, List[str]], job_requirements: str) -> float:
        """Calculate skill match score against job requirements."""
        job_skills = [skill.strip().lower() for skill in job_requirements.split(',')]
        all_resume_skills = [skill for skills in resume_skills.values() for skill in skills]
        
        if not job_skills:
            return 5.0  # Neutral score if no requirements
        
        matched_skills = set(all_resume_skills) & set(job_skills)
        match_percentage = len(matched_skills) / len(job_skills)
        
        # Scale to 0-10
        return min(10.0, match_percentage * 10)
    
    def analyze_experience_quality(self, text: str) -> Dict[str, any]:
        """Analyze the quality of experience descriptions."""
        # Count action verbs
        action_verbs_found = []
        for verb in self.ACTION_VERBS:
            if re.search(r'\b' + verb + r'\b', text, re.IGNORECASE):
                action_verbs_found.append(verb)
        
        # Check for quantitative metrics
        quantitative_score = 0
        for indicator in self.QUANTITATIVE_INDICATORS:
            if indicator in text:
                quantitative_score += 1
        
        # Check for bullet points and structure
        bullet_points = len(re.findall(r'[•·-]\s', text))
        
        # Calculate experience quality score
        action_verb_score = min(5.0, len(action_verbs_found) / len(self.ACTION_VERBS) * 5)
        quant_score = min(3.0, quantitative_score / len(self.QUANTITATIVE_INDICATORS) * 3)
        structure_score = min(2.0, bullet_points / 5 * 2)
        
        total_score = action_verb_score + quant_score + structure_score
        
        return {
            'score': round(total_score, 1),
            'action_verbs_found': action_verbs_found,
            'quantitative_indicators': quantitative_score,
            'bullet_points': bullet_points,
            'suggestions': self._get_experience_suggestions(action_verb_score, quant_score, structure_score)
        }
    
    def _get_experience_suggestions(self, action_score: float, quant_score: float, struct_score: float) -> List[str]:
        """Get suggestions for improving experience descriptions."""
        suggestions = []
        
        if action_score < 3.0:
            suggestions.append("Use more action verbs to start bullet points (e.g., 'Developed', 'Implemented', 'Led')")
        
        if quant_score < 2.0:
            suggestions.append("Add quantitative metrics to show impact (e.g., 'increased efficiency by 30%', 'managed team of 5')")
        
        if struct_score < 1.5:
            suggestions.append("Use bullet points to structure your experience descriptions")
        
        return suggestions
    
    def generate_missing_keywords(self, resume_skills: Dict[str, List[str]], job_requirements: str) -> List[str]:
        """Generate list of missing keywords from job requirements."""
        job_skills = [skill.strip().lower() for skill in job_requirements.split(',')]
        all_resume_skills = [skill for skills in resume_skills.values() for skill in skills]
        
        missing_skills = set(job_skills) - set(all_resume_skills)
        return sorted(list(missing_skills))
    
    def generate_resume_suggestions(self, resume_skills: Dict[str, List[str]], experience_analysis: Dict, job_requirements: str = "") -> List[str]:
        """Generate comprehensive resume improvement suggestions."""
        suggestions = []
        
        # Skill-based suggestions
        total_skills = sum(len(skills) for skills in resume_skills.values())
        if total_skills < 5:
            suggestions.append("Add more relevant technical skills to your resume")
        
        if 'programming_languages' not in resume_skills or len(resume_skills.get('programming_languages', [])) < 2:
            suggestions.append("Include more programming languages to show technical versatility")
        
        if 'cloud_devops' not in resume_skills:
            suggestions.append("Consider adding cloud or DevOps skills (AWS, Docker, etc.) as they are in high demand")
        
        # Experience-based suggestions
        suggestions.extend(experience_analysis.get('suggestions', []))
        
        # Job-specific suggestions
        if job_requirements:
            missing_keywords = self.generate_missing_keywords(resume_skills, job_requirements)
            if missing_keywords:
                suggestions.append(f"Add these keywords from job description: {', '.join(missing_keywords[:5])}")
        
        # General suggestions
        suggestions.extend([
            "Ensure your resume is properly formatted with clear sections",
            "Keep your resume concise (1-2 pages maximum)",
            "Proofread carefully for typos and grammatical errors",
            "Include a professional summary at the top"
        ])
        
        return suggestions[:8]  # Return top 8 suggestions
    
    def generate_rewritten_bullets(self, text: str, target_skills: List[str]) -> List[str]:
        """Generate improved bullet point suggestions."""
        # This is a simplified version - in production, you'd use more sophisticated NLP
        rewritten_bullets = []
        
        # Find existing bullet points
        bullet_points = re.findall(r'[•·-]\s*([^\n]+)', text)
        
        for i, bullet in enumerate(bullet_points[:3]):  # Limit to 3 examples
            # Simple enhancement logic
            if not any(verb in bullet.lower() for verb in self.ACTION_VERBS[:5]):
                rewritten = f"Developed {bullet.strip()}"
            elif not any(indicator in bullet.lower() for indicator in ['%', 'number', 'team', 'project']):
                rewritten = f"{bullet.strip()} resulting in improved efficiency"
            else:
                rewritten = bullet.strip()
            
            rewritten_bullets.append(f"Example {i+1}: {rewritten}")
        
        return rewritten_bullets
    
    def analyze_resume(self, pdf_content: bytes, job_requirements: str = "") -> Dict:
        """Perform complete ATS analysis of resume."""
        # Extract text
        text = self.extract_text_from_pdf(pdf_content)
        
        # Extract skills
        skills = self.extract_skills(text)
        
        # Calculate scores
        skill_score = self.calculate_skill_score(skills, job_requirements) if job_requirements else 5.0
        experience_analysis = self.analyze_experience_quality(text)
        
        # Generate recommendations
        missing_keywords = self.generate_missing_keywords(skills, job_requirements) if job_requirements else []
        suggestions = self.generate_resume_suggestions(skills, experience_analysis, job_requirements)
        rewritten_bullets = self.generate_rewritten_bullets(text, list(skills.keys()))
        
        # Calculate overall ATS score
        overall_score = (skill_score * 0.4) + (experience_analysis['score'] * 0.6)
        
        return {
            'ats_score': round(overall_score, 1),
            'skill_score': round(skill_score, 1),
            'experience_score': experience_analysis['score'],
            'skills_found': skills,
            'missing_keywords': missing_keywords,
            'suggestions': suggestions,
            'rewritten_bullets': rewritten_bullets,
            'skill_breakdown': {
                category: len(skills_list) for category, skills_list in skills.items()
            },
            'experience_analysis': experience_analysis
        }


# Global ATS analyzer instance
ats_analyzer = ATSAnalyzer()

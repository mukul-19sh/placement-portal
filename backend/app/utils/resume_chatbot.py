import re
import json
from typing import Dict, List, Tuple
from collections import Counter
import PyPDF2
from io import BytesIO


class ResumeReviewChatbot:
    """AI-powered chatbot for resume review and profile improvement."""
    
    # Common technical skills categories
    TECH_SKILLS = {
        'programming_languages': [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust',
            'html', 'css', 'sql', 'r', 'matlab', 'scala', 'perl', 'dart', 'objective-c'
        ],
        'web_technologies': [
            'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'spring', 'laravel', 'rails',
            'next.js', 'nuxt', 'gatsby', 'webpack', 'babel', 'tailwind', 'bootstrap', 'jquery'
        ],
        'databases': [
            'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle', 'sqlite', 'cassandra',
            'dynamodb', 'firebase', 'supabase', 'neo4j', 'influxdb'
        ],
        'cloud_devops': [
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'terraform', 'ansible',
            'ci/cd', 'microservices', 'serverless', 'lambda', 'ec2', 's3', 'cloudformation'
        ],
        'tools_frameworks': [
            'git', 'github', 'gitlab', 'jira', 'slack', 'vscode', 'intellij', 'eclipse',
            'postman', 'swagger', 'api', 'rest', 'graphql', 'grpc', 'kafka', 'rabbitmq'
        ]
    }
    
    # Action verbs for resume analysis
    ACTION_VERBS = [
        'developed', 'implemented', 'designed', 'created', 'built', 'led', 'managed', 'optimized',
        'improved', 'increased', 'reduced', 'achieved', 'launched', 'deployed', 'maintained',
        'collaborated', 'coordinated', 'analyzed', 'tested', 'debugged', 'refactored',
        'architected', 'engineered', 'spearheaded', 'mentored', 'trained', 'documented'
    ]
    
    # Common resume issues
    COMMON_ISSUES = [
        "missing quantifiable achievements",
        "weak action verbs",
        "poor formatting",
        "missing keywords",
        "inconsistent tense",
        "too generic",
        "missing technical details",
        "no clear structure"
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
    
    def analyze_resume_quality(self, text: str) -> Dict[str, any]:
        """Analyze quality of resume content."""
        # Count action verbs
        action_verbs_found = []
        for verb in self.ACTION_VERBS:
            if re.search(r'\b' + verb + r'\b', text, re.IGNORECASE):
                action_verbs_found.append(verb)
        
        # Check for quantitative metrics
        quantitative_indicators = ['%', 'percent', 'increase', 'decrease', 'growth', 'revenue', 
                              'cost', 'time', 'users', 'customers', 'clients', 'projects', 
                              'team', 'employees', 'budget', 'saved', 'reduced']
        
        quant_count = sum(1 for indicator in quantitative_indicators if indicator in text)
        
        # Check structure and formatting
        bullet_points = len(re.findall(r'[•·-]\s', text))
        sections = len(re.findall(r'\n\s*(?:experience|education|skills|projects|summary)', text, re.IGNORECASE))
        
        # Calculate quality scores
        action_score = min(10, len(action_verbs_found) / len(self.ACTION_VERBS) * 10)
        quant_score = min(10, quant_count / len(quantitative_indicators) * 10)
        structure_score = min(10, (bullet_points / 5 + sections / 4) * 5)
        
        overall_score = (action_score + quant_score + structure_score) / 3
        
        return {
            'overall_score': round(overall_score, 1),
            'action_score': round(action_score, 1),
            'quant_score': round(quant_score, 1),
            'structure_score': round(structure_score, 1),
            'action_verbs_found': action_verbs_found,
            'quantitative_indicators': quant_count,
            'bullet_points': bullet_points,
            'sections': sections
        }
    
    def generate_improvement_suggestions(self, skills: Dict[str, List[str]], quality: Dict, text: str) -> List[str]:
        """Generate personalized improvement suggestions."""
        suggestions = []
        
        # Skill-based suggestions
        total_skills = sum(len(skills_list) for skills_list in skills.values())
        if total_skills < 5:
            suggestions.append("💡 Add more specific technical skills to increase your visibility")
        
        if 'programming_languages' not in skills or len(skills.get('programming_languages', [])) < 2:
            suggestions.append("💡 Include multiple programming languages to show versatility")
        
        if 'cloud_devops' not in skills:
            suggestions.append("☁️ Add cloud/DevOps skills (AWS, Docker, etc.) - they're in high demand")
        
        # Quality-based suggestions
        if quality['action_score'] < 5:
            suggestions.append("🎯 Start bullet points with strong action verbs (Developed, Led, Implemented)")
        
        if quality['quant_score'] < 5:
            suggestions.append("📊 Add quantifiable achievements (e.g., 'increased efficiency by 30%')")
        
        if quality['structure_score'] < 5:
            suggestions.append("📝 Use clear sections and bullet points for better readability")
        
        # Content-based suggestions
        if len(text) < 500:
            suggestions.append("📄 Your resume seems too short - add more detail about your experience")
        
        if 'summary' not in text.lower():
            suggestions.append("👤 Add a professional summary at the top of your resume")
        
        return suggestions
    
    def answer_profile_question(self, question: str, profile_data: Dict = None, resume_text: str = None) -> str:
        """Answer questions about profile improvement."""
        question_lower = question.lower()
        
        # Skills-related questions
        if any(word in question_lower for word in ['skill', 'skills', 'technical']):
            if resume_text:
                skills = self.extract_skills(resume_text)
                total_skills = sum(len(skills_list) for skills_list in skills.values())
                
                if total_skills == 0:
                    return "I don't see any technical skills in your resume. Consider adding programming languages, frameworks, or tools you're proficient with."
                
                response = f"I found {total_skills} technical skills in your resume:\n\n"
                for category, skills_list in skills.items():
                    if skills_list:
                        response += f"🔹 {category.replace('_', ' ').title()}: {', '.join(skills_list)}\n"
                
                if total_skills < 8:
                    response += f"\n💡 Consider adding more skills, especially in these areas: {', '.join(self.TECH_SKILLS['cloud_devops'][:3])}, {', '.join(self.TECH_SKILLS['tools_frameworks'][:3])}"
                
                return response
            else:
                return "Please upload your resume first so I can analyze your skills."
        
        # Improvement-related questions
        if any(word in question_lower for word in ['improve', 'better', 'weakness', 'missing']):
            if resume_text:
                quality = self.analyze_resume_quality(resume_text)
                skills = self.extract_skills(resume_text)
                suggestions = self.generate_improvement_suggestions(skills, quality, resume_text)
                
                response = f"Here are the main areas for improvement:\n\n"
                response += f"📊 Overall Resume Score: {quality['overall_score']}/10\n\n"
                
                if quality['action_score'] < 6:
                    response += f"🎯 Action Verbs: {quality['action_score']}/10 - Use stronger action words\n"
                
                if quality['quant_score'] < 6:
                    response += f"📈 Quantifiable Results: {quality['quant_score']}/10 - Add metrics and numbers\n"
                
                if quality['structure_score'] < 6:
                    response += f"📝 Structure: {quality['structure_score']}/10 - Improve formatting\n"
                
                response += "\nTop 3 Recommendations:\n"
                for i, suggestion in enumerate(suggestions[:3], 1):
                    response += f"{i}. {suggestion}\n"
                
                return response
            else:
                return "Upload your resume and I'll provide specific improvement recommendations."
        
        # Profile-related questions
        if any(word in question_lower for word in ['profile', 'linkedin', 'complete']):
            if profile_data:
                completion = profile_data.get('profile_completion', 0)
                response = f"Your profile is {completion}% complete.\n\n"
                
                if not profile_data.get('full_name'):
                    response += "❌ Missing: Full name\n"
                if not profile_data.get('skills'):
                    response += "❌ Missing: Skills\n"
                if not profile_data.get('cgpa'):
                    response += "❌ Missing: CGPA\n"
                if not profile_data.get('resume_url'):
                    response += "❌ Missing: Resume\n"
                
                response += "\n💡 A complete profile gets 3x more views from recruiters!"
                
                return response
            else:
                return "Make sure to fill out all sections: name, skills, CGPA, and upload your resume."
        
        # Job-related questions
        if any(word in question_lower for word in ['job', 'career', 'interview']):
            return "For job applications, focus on:\n\n• Tailoring your resume to each job description\n• Highlighting relevant skills and experience\n• Using keywords from the job posting\n• Quantifying your achievements\n\nWould you like me to review your resume for a specific job type?"
        
        # Default response
        return "I can help you with:\n\n• Resume analysis and improvement suggestions\n• Skills identification and recommendations\n• Profile completion tips\n• Job application advice\n\nUpload your resume and ask me anything about making it better!"
    
    def chat_with_resume(self, question: str, pdf_content: bytes = None, profile_data: Dict = None) -> Dict:
        """Main chat interface for resume review."""
        response = {
            "question": question,
            "answer": "",
            "has_resume": bool(pdf_content),
            "analysis": None
        }
        
        # Analyze resume if provided
        if pdf_content:
            try:
                resume_text = self.extract_text_from_pdf(pdf_content)
                skills = self.extract_skills(resume_text)
                quality = self.analyze_resume_quality(resume_text)
                
                response["analysis"] = {
                    "skills_found": skills,
                    "quality_scores": quality,
                    "total_skills": sum(len(skills_list) for skills_list in skills.values())
                }
                
                # Answer the question with resume context
                response["answer"] = self.answer_profile_question(question, profile_data, resume_text)
                
            except Exception as e:
                response["answer"] = f"Sorry, I couldn't analyze your resume: {str(e)}"
        else:
            # Answer without resume context
            response["answer"] = self.answer_profile_question(question, profile_data)
        
        return response


# Global chatbot instance
resume_chatbot = ResumeReviewChatbot()

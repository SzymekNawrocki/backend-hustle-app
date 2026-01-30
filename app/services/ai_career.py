import random

def analyze_job_description(text: str):
    """
    MOCKED AI analysis of a job description.
    Returns a random match score and 5 technological keywords.
    """
    tech_pool = ["Python", "FastAPI", "Docker", "AWS", "SQLAlchemy", "PostgreSQL", "React", "TypeScript", "Kubernetes", "Redis"]
    
    match_score = random.randint(50, 100)
    ai_keywords = random.sample(tech_pool, 5)
    
    return {
        "match_score": match_score,
        "ai_keywords": ai_keywords
    }

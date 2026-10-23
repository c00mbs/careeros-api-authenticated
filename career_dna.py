"""Build a category score profile from a user's saved skills."""

from modules.models import User


def build_career_dna(user: User) -> dict[str, int]:
    dna = {
        "technical": 0,
        "leadership": 0,
        "operations": 0,
        "communication": 0,
        "analytical": 0,
    }
    for skill in user.skills:
        name = skill.skill_name.lower()
        if name in {"python", "sql", "excel", "power bi"}:
            dna["analytical"] += 5
        if name in {"python", "sql", "pandas", "machine learning"}:
            dna["technical"] += 5
        if name in {"leadership", "coaching", "training"}:
            dna["leadership"] += 5
        if name in {"inventory", "logistics", "operations"}:
            dna["operations"] += 5
        if name in {"communication", "presentation"}:
            dna["communication"] += 5
    return {category: min(score, 100) for category, score in dna.items()}

from __future__ import annotations
import re
from pathlib import PurePosixPath
from typing import Any

# Rules are intentionally explainable. Keywords are evidence, not proof.
LEARNING_TERMS = {
 "programming": ["tutorial", "course", "lesson", "lecture", "learn", "learning", "beginner", "advanced", "bootcamp", "coding", "programming", "code along", "hands-on", "lab exercise", "lab sheet", "workshop"],
 "java": ["java", "spring boot", "jvm"], "python": ["python", "django", "flask", "pandas tutorial"],
 "javascript": ["javascript", "typescript", "node.js", "react course", "next.js course"],
 "web_development": ["html", "css", "web development", "frontend", "front-end", "backend", "back-end", "full stack", "fullstack"],
 "mobile_development": ["android development", "kotlin", "swiftui", "ios development", "jetpack compose", "flutter course"],
 "software_engineering": ["software engineering", "design patterns", "formal methods", "b method", "uml", "requirements engineering", "software architecture"],
 "computer_science": ["algorithm", "data structures", "operating systems", "computer science", "compiler", "automata theory"],
 "database": ["database", "sql", "mysql", "postgresql", "mongodb", "normalization"],
 "cybersecurity": ["cybersecurity", "ethical hacking", "penetration testing", "pentesting", "network security", "kali linux", "ctf", "capture the flag"],
 "networking": ["networking", "cisco", "ccna", "tcp/ip", "wireshark", "routing and switching"],
 "mathematics": ["mathematics", "discrete math", "calculus", "linear algebra", "statistics", "boolean algebra"],
 "ai_data_science": ["machine learning", "deep learning", "artificial intelligence", "data science", "neural network", "tensorflow", "pytorch"],
 "university": ["university", "module notes", "lecture notes", "assignment", "coursework", "exam paper", "past paper", "revision", "semester", "tutorial sheet", "worksheet", "study guide", "textbook", "ebook", "e-book", "syllabus"]
}
NON_LEARNING_TERMS = {
 "entertainment": ["movie", "movies", "film", "series", "season", "episode", "anime", "cartoon", "concert", "music video", "1080p", "2160p", "bluray", "blu-ray", "web-dl", "hdtv"],
 "personal": ["family photos", "personal photos", "backup", "wedding photos", "passport scan"],
 "business": ["invoice", "payroll", "contract", "quotation", "financial report"]
}
EDU_EXTS = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".epub", ".ipynb", ".py", ".java", ".js", ".ts", ".c", ".cpp", ".kt", ".swift", ".sql"}
MEDIA_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".mp3", ".flac", ".m4v", ".webm"}

def classify(result: dict[str, Any], min_confidence: float = 0.72) -> dict[str, Any]:
    """Classify using available names, source paths and preview. Never claims file-body inspection."""
    name = str(result.get("name") or "")
    sources = result.get("sources") or []
    preview = result.get("preview") or []
    haystack = " ".join([name, *map(str, sources), *map(str, preview)]).lower()
    haystack = re.sub(r"[_./\\-]+", " ", haystack)
    suffix = PurePosixPath(name).suffix.lower()
    positive: list[tuple[str, str]] = []
    negative: list[tuple[str, str]] = []
    for category, terms in LEARNING_TERMS.items():
        for term in terms:
            if re.search(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)", haystack):
                positive.append((category, term))
    for category, terms in NON_LEARNING_TERMS.items():
        for term in terms:
            if re.search(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)", haystack):
                negative.append((category, term))
    # Penalize ambiguous language: a technology name alone is not enough.
    strong_context = any(t in haystack for t in ["course", "tutorial", "lesson", "assignment", "exam", "textbook", "learn", "training", "lab", "worksheet", "revision", "study guide"])
    # Generic labels such as "Lecture 05" alone are ambiguous, not proof of education.
    generic_only = positive and all(term in {"lecture", "lesson", "course", "tutorial", "learning", "learn", "university", "assignment", "exam paper", "revision", "textbook", "ebook", "e-book", "study guide", "worksheet", "workshop"} for _, term in positive)
    matched_categories = list(dict.fromkeys(cat for cat, _ in positive))
    if positive and negative and not strong_context:
        confidence = min(0.88, 0.62 + 0.1 * len(set(term for _, term in negative)))
        return {"is_learning_material": False, "learning_confidence": round(confidence, 2), "primary_category": f"non_learning/{negative[0][0]}", "subcategory": "", "content_type": "media" if suffix in MEDIA_EXTS else ("document_or_code" if suffix in EDU_EXTS else "unknown"), "classification_reason": "non-learning indicators outweigh technology-name match: " + ", ".join(dict.fromkeys(term for _, term in negative)), "review_required": False, "classification_evidence_scope": "available filename, decrypted name if available, source paths and preview metadata only; no file body downloaded or inspected"}
    if positive and generic_only and not strong_context:
        return {"is_learning_material": None, "learning_confidence": 0.35, "primary_category": "uncertain/review_required", "subcategory": "", "content_type": "media" if suffix in MEDIA_EXTS else ("document_or_code" if suffix in EDU_EXTS else "unknown"), "classification_reason": "generic educational label without a clear subject or enough context", "review_required": True, "classification_evidence_scope": "available filename, decrypted name if available, source paths and preview metadata only; no file body downloaded or inspected"}
    if positive:
        confidence = min(0.98, 0.48 + 0.11 * len(set(term for _, term in positive)) + (0.18 if strong_context else 0))
        if negative:
            confidence -= 0.24
        confidence = max(0.0, min(0.98, confidence))
        is_learning: bool | None = confidence >= min_confidence
        primary = matched_categories[0] if matched_categories else "other"
        category = f"learning/{primary}" if is_learning is True else ("uncertain/review_required" if confidence >= 0.35 else "non_learning/other")
        reason = "learning indicators: " + ", ".join(dict.fromkeys(term for _, term in positive))
        if negative: reason += "; conflicting non-learning indicators: " + ", ".join(dict.fromkeys(term for _, term in negative))
        review = is_learning is not True
    elif negative:
        confidence = min(0.95, 0.58 + 0.12 * len(set(term for _, term in negative)))
        is_learning = False
        category = f"non_learning/{negative[0][0]}"
        reason = "non-learning indicators: " + ", ".join(dict.fromkeys(term for _, term in negative))
        review = False
    else:
        confidence = 0.2 if not name else 0.35
        is_learning = None
        category = "uncertain/review_required"
        reason = "insufficient descriptive metadata; filename/body content not confirmed"
        review = True
    return {
        "is_learning_material": is_learning,
        "learning_confidence": round(confidence, 2),
        "primary_category": category,
        "subcategory": matched_categories[0] if matched_categories and is_learning is True else "",
        "content_type": "media" if suffix in MEDIA_EXTS else ("document_or_code" if suffix in EDU_EXTS else "unknown"),
        "classification_reason": reason,
        "review_required": review,
        "classification_evidence_scope": "available filename, decrypted name if available, source paths and preview metadata only; no file body downloaded or inspected"
    }

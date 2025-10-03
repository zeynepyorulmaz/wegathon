"""
Trip requirements parser and validator.
Extracts trip details from user prompt and identifies missing required information.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from app.models.conversation import RequiredField
from app.core.logging import logger


def parse_trip_prompt(prompt: str, language: str = "en") -> Tuple[Dict[str, Any], List[RequiredField]]:
    """
    Parse a trip prompt and extract known information.
    Returns (extracted_data, missing_required_fields)
    """
    extracted = {}
    missing = []
    
    # Define questions in multiple languages
    questions = {
        "en": {
            "origin": "Where are you traveling from?",
            "destination": "Where would you like to go?",
            "start_date": "When would you like to start your trip? (format: DD.MM.YYYY or YYYY-MM-DD)",
            "end_date": "When would you like to return? (format: DD.MM.YYYY or YYYY-MM-DD)",
            "duration": "How many days/nights do you want to travel?",
            "adults": "How many adults will be traveling?",
        },
        "tr": {
            "origin": "Nereden seyahat edeceksiniz?",
            "destination": "Nereye gitmek istersiniz?",
            "start_date": "Seyahatinize ne zaman başlamak istersiniz? (format: GG.AA.YYYY)",
            "end_date": "Ne zaman dönmek istersiniz? (format: GG.AA.YYYY)",
            "duration": "Kaç gün/gece seyahat etmek istersiniz?",
            "adults": "Kaç yetişkin seyahat edecek?",
        }
    }
    
    lang_questions = questions.get(language, questions["en"])
    
    # Extract origin
    origin_patterns = [
        r"from\s+([A-Za-zğüşıöçĞÜŞİÖÇ\s]+?)(?:\s+to|\s*,)",
        r"starting\s+(?:from\s+)?([A-Za-zğüşıöçĞÜŞİÖÇ\s]+?)(?:\s+to|\s*,)",
        r"([A-Za-zğüşıöçĞÜŞİÖÇ]+)'dan",
        r"([A-Za-zğüşıöçĞÜŞİÖÇ]+)'den",
    ]
    for pattern in origin_patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            extracted["origin"] = match.group(1).strip()
            break
    
    # Extract destination
    dest_patterns = [
        r"to\s+([A-Za-zğüşıöçĞÜŞİÖÇ\s]+?)(?:\s+on|\s*,|\s+for|\s*$)",
        r"visit\s+([A-Za-zğüşıöçĞÜŞİÖÇ\s]+?)(?:\s+on|\s*,|\s+for|\s*$)",
        r"([A-Za-zğüşıöçĞÜŞİÖÇ]+)'ya",
        r"([A-Za-zğüşıöçĞÜŞİÖÇ]+)'ye",
    ]
    for pattern in dest_patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            extracted["destination"] = match.group(1).strip()
            break
    
    # Extract dates
    # Format: DD.MM.YYYY or YYYY-MM-DD
    date_pattern = r"\b(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{4}-\d{2}-\d{2})\b"
    dates = re.findall(date_pattern, prompt)
    if len(dates) >= 1:
        extracted["start_date"] = dates[0]
    if len(dates) >= 2:
        extracted["end_date"] = dates[1]
    
    # Extract duration
    duration_patterns = [
        r"(\d+)\s*(?:day|days|gün)",
        r"(\d+)\s*(?:night|nights|gece)",
    ]
    for pattern in duration_patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            extracted["duration"] = int(match.group(1))
            break
    
    # Extract number of travelers
    adults_patterns = [
        r"(\d+)\s*(?:adult|adults|yetişkin|kişi)",
        r"(\d+)\s*(?:person|people)",
    ]
    for pattern in adults_patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            extracted["adults"] = int(match.group(1))
            break
    
    # Default adults to 1 if not specified
    if "adults" not in extracted:
        extracted["adults"] = 1
    
    # Determine missing required fields
    if "origin" not in extracted:
        missing.append(RequiredField(
            field="origin",
            question=lang_questions["origin"],
            type="text",
            example="Istanbul" if language == "en" else "İstanbul"
        ))
    
    if "destination" not in extracted:
        missing.append(RequiredField(
            field="destination",
            question=lang_questions["destination"],
            type="text",
            example="Paris" if language == "en" else "Paris"
        ))
    
    # If we have start date but no end date, and no duration, ask for one
    if "start_date" in extracted and "end_date" not in extracted and "duration" not in extracted:
        missing.append(RequiredField(
            field="end_date",
            question=lang_questions["end_date"],
            type="date",
            example="20.11.2025" if language == "en" else "20.11.2025"
        ))
    
    # If no dates at all, ask for start date
    if "start_date" not in extracted:
        missing.append(RequiredField(
            field="start_date",
            question=lang_questions["start_date"],
            type="date",
            example="15.11.2025" if language == "en" else "15.11.2025"
        ))
    
    # If no end date and no duration, ask for duration
    if "start_date" in extracted and "end_date" not in extracted and "duration" not in extracted:
        missing.append(RequiredField(
            field="duration",
            question=lang_questions["duration"],
            type="number",
            example="3" if language == "en" else "3"
        ))
    
    logger.info(f"Parsed prompt - Extracted: {extracted}, Missing: {[f.field for f in missing]}")
    
    return extracted, missing


def validate_and_complete_trip_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate trip data and compute missing fields from available data.
    """
    # If we have start_date and duration but no end_date, compute it
    if "start_date" in data and "duration" in data and "end_date" not in data:
        try:
            start = parse_date(data["start_date"])
            end = start + timedelta(days=int(data["duration"]))
            data["end_date"] = end.strftime("%d.%m.%Y")
        except Exception as e:
            logger.warning(f"Could not compute end_date: {e}")
    
    # If we have both dates but no duration, compute it
    if "start_date" in data and "end_date" in data and "duration" not in data:
        try:
            start = parse_date(data["start_date"])
            end = parse_date(data["end_date"])
            data["duration"] = (end - start).days
        except Exception as e:
            logger.warning(f"Could not compute duration: {e}")
    
    # Ensure adults defaults to 1
    if "adults" not in data:
        data["adults"] = 1
    
    return data


def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats"""
    formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Could not parse date: {date_str}")


def format_trip_prompt(data: Dict[str, Any], language: str = "en") -> str:
    """
    Format collected trip data into a comprehensive prompt for the planner.
    """
    parts = []
    
    if language == "tr":
        if "origin" in data:
            parts.append(f"{data['origin']}'dan")
        if "destination" in data:
            parts.append(f"{data['destination']}'ya")
        if "start_date" in data and "end_date" in data:
            parts.append(f"{data['start_date']} - {data['end_date']} tarihleri arasında")
        elif "start_date" in data:
            parts.append(f"{data['start_date']} tarihinde başlayan")
        if "duration" in data:
            parts.append(f"{data['duration']} günlük")
        if "adults" in data:
            parts.append(f"{data['adults']} kişilik")
        parts.append("seyahat planı")
    else:
        parts.append(f"{data.get('duration', 3)} day trip")
        if "origin" in data:
            parts.append(f"from {data['origin']}")
        if "destination" in data:
            parts.append(f"to {data['destination']}")
        if "start_date" in data and "end_date" in data:
            parts.append(f"{data['start_date']} - {data['end_date']}")
        elif "start_date" in data:
            parts.append(f"starting {data['start_date']}")
        if "adults" in data:
            parts.append(f"{data['adults']} adult(s)")
    
    return " ".join(parts)


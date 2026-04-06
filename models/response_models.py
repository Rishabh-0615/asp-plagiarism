"""Response Models"""
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class AIDetectionResponse:
    """AI Detection Response Model"""
    success: bool
    ai_score: float
    human_score: float
    confidence: float
    label: str
    submission_id: Optional[str] = None
    file_url: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)

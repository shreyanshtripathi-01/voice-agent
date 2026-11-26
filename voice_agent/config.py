"""Configuration for the Fortivex AI voice sales agent.

Everything in this project uses the Python standard library and browser APIs.
No API keys, no paid services, no model downloads.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"
DB_PATH = DATA_DIR / "crm.db"

HOST = "127.0.0.1"
PORT = 8765

LANGUAGES = {
    "en-IN": "English (India)",
    "en-US": "English (US)",
    "hi-IN": "Hindi (हिन्दी)",
    "es-ES": "Spanish (Español)",
}

# BANT = Budget, Authority, Need, Timeline. Each dimension is worth 25 points.
QUALIFICATION_WEIGHTS = {"budget": 25, "authority": 25, "need": 25, "timeline": 25}
GRADE_THRESHOLDS = ((70, "HOT"), (40, "WARM"), (0, "COLD"))

STAGES = (
    "GREETING",
    "DISCOVERY",
    "QUALIFYING",
    "PRESENTING",
    "SCHEDULING",
    "CLOSED",
)

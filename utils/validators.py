"""Input validation helpers (project info + uploaded file checks)."""
from utils.helpers import AUDIENCES, MAX_FILE_MB


def validate_project_inputs(project_name: str, audience: str, description: str = "") -> list[str]:
    """Return a list of human-readable error messages (empty list = all good)."""
    errors = []
    if not project_name or not project_name.strip():
        errors.append("Please enter a project name.")
    elif len(project_name.strip()) > 100:
        errors.append("Project name must be 100 characters or fewer.")
    if audience not in AUDIENCES:
        errors.append("Please choose a valid target audience.")
    if description and len(description) > 1500:
        errors.append("Project description must be 1500 characters or fewer.")
    return errors


def validate_file_basics(filename: str, size_bytes: int) -> list[str]:
    """Cheap checks that do not need to open the PDF."""
    errors = []
    if not filename.lower().endswith(".pdf"):
        errors.append("Only PDF files are supported.")
    if size_bytes == 0:
        errors.append("The file is empty.")
    if size_bytes > MAX_FILE_MB * 1024 * 1024:
        errors.append(f"File is larger than the {MAX_FILE_MB} MB limit.")
    return errors

"""Parse incident_catalog.md into a list of IncidentTemplate objects."""
from __future__ import annotations

import re
from pathlib import Path

from src.models import Category, IncidentTemplate, Severity

_SEVERITY_MAP: dict[str, Severity] = {
    "baja": Severity.LOW,
    "media": Severity.MEDIUM,
    "media a alta": Severity.HIGH,
    "alta": Severity.HIGH,
    "crítica": Severity.CRITICAL,
}

_CATEGORY_MAP: dict[str, Category] = {
    "MEC": Category.MEC,
    "PRO": Category.PRO,
    "CAL": Category.CAL,
    "SEG": Category.SEG,
    "LOG": Category.LOG,
    "OPS": Category.OPS,
}

# Matches lines like: ## MEC-001 – Paro inesperado de clasificadora (grader)
_HEADER_RE = re.compile(
    r"^##\s+(?P<code>[A-Z]{3}-\d{3})\s+[–—-]\s+(?P<name>.+)$"
)
# Matches field lines like: - **Descripción:** La máquina ...
_FIELD_RE = re.compile(
    r"^-\s+\*\*(?P<key>[^*]+?)(?:\s+sugerida)?:\*\*\s*(?P<value>.+)$"
)

_FIELD_KEY_MAP = {
    "Descripción": "description",
    "Impacto": "impact",
    "Severidad": "severity",
    "Severidad sugerida": "severity",
    "Acción inmediata": "immediate_action",
    "Área responsable": "responsible_area",
}


def _parse_severity(raw: str) -> Severity:
    normalized = raw.strip().lower().split("(")[0].strip()
    for key, sev in _SEVERITY_MAP.items():
        if key in normalized:
            return sev
    return Severity.MEDIUM


def parse_catalog(catalog_path: Path | str) -> list[IncidentTemplate]:
    """Read the markdown catalog and return structured templates."""
    text = Path(catalog_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    templates: list[IncidentTemplate] = []
    current: dict | None = None

    for line in lines:
        header_match = _HEADER_RE.match(line.strip())
        if header_match:
            if current:
                templates.append(_build_template(current))
            code = header_match.group("code")
            current = {
                "code": code,
                "category": _CATEGORY_MAP[code.split("-")[0]],
                "name": header_match.group("name").strip(),
            }
            continue

        if current is None:
            continue

        field_match = _FIELD_RE.match(line.strip())
        if field_match:
            key_raw = field_match.group("key").strip()
            value = field_match.group("value").strip()
            field_name = _FIELD_KEY_MAP.get(key_raw)
            if field_name:
                current[field_name] = value

    if current:
        templates.append(_build_template(current))

    return templates


def _build_template(data: dict) -> IncidentTemplate:
    severity_raw = data.pop("severity", "Media")
    return IncidentTemplate(
        severity=_parse_severity(severity_raw),
        **data,
    )


def load_catalog_text(catalog_path: Path | str) -> str:
    """Return raw catalog markdown (for inclusion in LLM prompts)."""
    return Path(catalog_path).read_text(encoding="utf-8")

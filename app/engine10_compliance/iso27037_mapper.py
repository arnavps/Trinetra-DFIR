"""
Maps logged case events onto the four ISO/IEC 27037 phases (Blueprint §5.1):
1. Identification
2. Collection
3. Acquisition
4. Preservation
"""

from typing import List, Dict, Any


def map_case_to_iso27037(audit_log_entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorizes audit log entries into the 4 standard ISO/IEC 27037 digital evidence handling phases.
    """
    mapped_phases: Dict[str, List[Dict[str, Any]]] = {
        "Identification": [],
        "Collection": [],
        "Acquisition": [],
        "Preservation": [],
    }

    for entry in audit_log_entries:
        event_type = entry.get("event_type", "").lower()

        if "case_create" in event_type or "identify" in event_type or "detect" in event_type or "init" in event_type:
            mapped_phases["Identification"].append(entry)
        elif "acquisition" in event_type or "image" in event_type or "raw_read" in event_type or "acqui" in event_type:
            mapped_phases["Acquisition"].append(entry)
        elif "parse" in event_type or "carve" in event_type or "collect" in event_type or "extract" in event_type or "file" in event_type:
            mapped_phases["Collection"].append(entry)
        else:
            # Audit hashing, verification, exports, reports, and normalizations map to Preservation
            mapped_phases["Preservation"].append(entry)

    return mapped_phases


def get_iso27037_narratives(audit_log_entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Generates rich, descriptive narrative summaries for each of the 4 ISO/IEC 27037 phases
    accompanied by explicit timestamped audit entry citations from the current case.
    """
    mapped = map_case_to_iso27037(audit_log_entries)

    descriptions = {
        "Identification": (
            "Evidence identification involves recognizing and cataloging potential digital media sources, "
            "OEM hardware profiles, and case parameters prior to physical seizure or analytical extraction."
        ),
        "Collection": (
            "Collection encompasses the recovery and extraction of evidentiary data, including structured "
            "filesystem parsing, unallocated sector carving, and active channel separation."
        ),
        "Acquisition": (
            "Acquisition defines the creation of a forensic bit-stream duplicate of the digital media under "
            "hardware or software write-blocking, with immediate cryptographic hash computation."
        ),
        "Preservation": (
            "Preservation maintains the integrity and authenticity of digital evidence via continuous "
            "append-only cryptographic hash chaining, audit verification, and tamper analysis."
        ),
    }

    results = {}
    for phase, phase_entries in mapped.items():
        citations = []
        for e in phase_entries:
            ts = e.get("timestamp", "UNKNOWN")
            if isinstance(ts, str) and "T" in ts:
                ts = ts.replace("T", " ")[:19]
            etype = e.get("event_type", "EVENT")
            citations.append(f"[{ts}] {etype}")

        results[phase] = {
            "description": descriptions[phase],
            "count": len(phase_entries),
            "citations": citations,
            "entries": phase_entries,
        }

    return results

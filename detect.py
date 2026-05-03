"""
Thin wrapper around the existing hubspot_detector module.
All detection logic lives in hubspot_detector.py — do not duplicate it here.
"""

from hubspot_detector import DetectionResult, detect_hubspot


def run_detection(domain: str) -> DetectionResult:
    """Run all HubSpot detection methods for *domain* and return the result."""
    return detect_hubspot(company=domain, domain=domain)

"""
CMMC Level 2 and NIST 800-53 compliance checker.

Provides compliance posture assessment based on platform capabilities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class CMMCDomain(str, Enum):
    ACCESS_CONTROL = "AC"
    AWARENESS_TRAINING = "AT"
    AUDIT_ACCOUNTABILITY = "AU"
    CONFIGURATION_MANAGEMENT = "CM"
    IDENTIFICATION_AUTH = "IA"
    INCIDENT_RESPONSE = "IR"
    MAINTENANCE = "MA"
    MEDIA_PROTECTION = "MP"
    PERSONNEL_SECURITY = "PS"
    PHYSICAL_PROTECTION = "PE"
    RISK_ASSESSMENT = "RA"
    SECURITY_ASSESSMENT = "CA"
    SYSTEM_COMMS = "SC"
    SYSTEM_INFO_INTEGRITY = "SI"


DOMAIN_NAMES = {
    CMMCDomain.ACCESS_CONTROL: "Access Control",
    CMMCDomain.AWARENESS_TRAINING: "Awareness & Training",
    CMMCDomain.AUDIT_ACCOUNTABILITY: "Audit & Accountability",
    CMMCDomain.CONFIGURATION_MANAGEMENT: "Configuration Management",
    CMMCDomain.IDENTIFICATION_AUTH: "Identification & Authentication",
    CMMCDomain.INCIDENT_RESPONSE: "Incident Response",
    CMMCDomain.MAINTENANCE: "Maintenance",
    CMMCDomain.MEDIA_PROTECTION: "Media Protection",
    CMMCDomain.PERSONNEL_SECURITY: "Personnel Security",
    CMMCDomain.PHYSICAL_PROTECTION: "Physical Protection",
    CMMCDomain.RISK_ASSESSMENT: "Risk Assessment",
    CMMCDomain.SECURITY_ASSESSMENT: "Security Assessment",
    CMMCDomain.SYSTEM_COMMS: "System & Communications Protection",
    CMMCDomain.SYSTEM_INFO_INTEGRITY: "System & Information Integrity",
}


@dataclass
class CMMCControl:
    domain: CMMCDomain
    control_id: str
    title: str
    description: str
    level: int  # 1 or 2
    is_met: bool = False


# Controls with is_met=True reflect capabilities the platform already implements
_CONTROLS: List[CMMCControl] = [
    # Access Control
    CMMCControl(CMMCDomain.ACCESS_CONTROL, "AC.L1-3.1.1", "Authorized Access Control",
                "Limit system access to authorized users.", 1, True),
    CMMCControl(CMMCDomain.ACCESS_CONTROL, "AC.L1-3.1.2", "Transaction & Function Control",
                "Limit system access to authorized transactions and functions.", 1, True),
    CMMCControl(CMMCDomain.ACCESS_CONTROL, "AC.L2-3.1.3", "CUI Flow Enforcement",
                "Control the flow of CUI in accordance with approved authorizations.", 2, False),
    CMMCControl(CMMCDomain.ACCESS_CONTROL, "AC.L2-3.1.5", "Least Privilege",
                "Employ the principle of least privilege.", 2, True),
    # Awareness & Training
    CMMCControl(CMMCDomain.AWARENESS_TRAINING, "AT.L2-3.2.1", "Role-Based Awareness",
                "Ensure personnel are aware of security risks.", 2, False),
    CMMCControl(CMMCDomain.AWARENESS_TRAINING, "AT.L2-3.2.2", "Training",
                "Ensure personnel are trained to carry out assigned duties.", 2, False),
    # Audit & Accountability
    CMMCControl(CMMCDomain.AUDIT_ACCOUNTABILITY, "AU.L2-3.3.1", "System Auditing",
                "Create and retain audit logs.", 2, True),
    CMMCControl(CMMCDomain.AUDIT_ACCOUNTABILITY, "AU.L2-3.3.2", "User Accountability",
                "Ensure actions can be traced to individual users.", 2, True),
    # Configuration Management
    CMMCControl(CMMCDomain.CONFIGURATION_MANAGEMENT, "CM.L2-3.4.1", "System Baselining",
                "Establish and maintain baseline configurations.", 2, False),
    CMMCControl(CMMCDomain.CONFIGURATION_MANAGEMENT, "CM.L2-3.4.2", "Security Configuration",
                "Establish and enforce security configuration settings.", 2, True),
    # Identification & Authentication
    CMMCControl(CMMCDomain.IDENTIFICATION_AUTH, "IA.L1-3.5.1", "Identification",
                "Identify system users and processes.", 1, True),
    CMMCControl(CMMCDomain.IDENTIFICATION_AUTH, "IA.L1-3.5.2", "Authentication",
                "Authenticate users and processes.", 1, True),
    CMMCControl(CMMCDomain.IDENTIFICATION_AUTH, "IA.L2-3.5.3", "Multifactor Auth",
                "Use multifactor authentication for privileged and network access.", 2, False),
    # Incident Response
    CMMCControl(CMMCDomain.INCIDENT_RESPONSE, "IR.L2-3.6.1", "Incident Handling",
                "Establish operational incident-handling capability.", 2, False),
    CMMCControl(CMMCDomain.INCIDENT_RESPONSE, "IR.L2-3.6.2", "Incident Reporting",
                "Track, document, and report incidents.", 2, True),
    # Maintenance
    CMMCControl(CMMCDomain.MAINTENANCE, "MA.L2-3.7.1", "System Maintenance",
                "Perform maintenance on organizational systems.", 2, False),
    # Media Protection
    CMMCControl(CMMCDomain.MEDIA_PROTECTION, "MP.L1-3.8.3", "Media Disposal",
                "Sanitize or destroy media containing FCI.", 1, False),
    CMMCControl(CMMCDomain.MEDIA_PROTECTION, "MP.L2-3.8.1", "Media Protection",
                "Protect system media containing CUI.", 2, False),
    # Personnel Security
    CMMCControl(CMMCDomain.PERSONNEL_SECURITY, "PS.L2-3.9.1", "Personnel Screening",
                "Screen individuals prior to authorizing access.", 2, False),
    CMMCControl(CMMCDomain.PERSONNEL_SECURITY, "PS.L2-3.9.2", "Personnel Actions",
                "Protect CUI during personnel actions such as terminations.", 2, False),
    # Physical Protection
    CMMCControl(CMMCDomain.PHYSICAL_PROTECTION, "PE.L1-3.10.1", "Physical Access",
                "Limit physical access to organizational systems.", 1, False),
    CMMCControl(CMMCDomain.PHYSICAL_PROTECTION, "PE.L1-3.10.3", "Escort Visitors",
                "Escort visitors and monitor visitor activity.", 1, False),
    # Risk Assessment
    CMMCControl(CMMCDomain.RISK_ASSESSMENT, "RA.L2-3.11.1", "Risk Assessment",
                "Periodically assess risk to operations and assets.", 2, False),
    CMMCControl(CMMCDomain.RISK_ASSESSMENT, "RA.L2-3.11.2", "Vulnerability Scan",
                "Scan for vulnerabilities periodically.", 2, True),
    # Security Assessment
    CMMCControl(CMMCDomain.SECURITY_ASSESSMENT, "CA.L2-3.12.1", "Security Assessments",
                "Periodically assess security controls.", 2, False),
    # System & Communications Protection
    CMMCControl(CMMCDomain.SYSTEM_COMMS, "SC.L1-3.13.1", "Boundary Protection",
                "Monitor and control communications at system boundaries.", 1, True),
    CMMCControl(CMMCDomain.SYSTEM_COMMS, "SC.L2-3.13.8", "CUI in Transit",
                "Implement cryptographic mechanisms to prevent unauthorized CUI disclosure during transmission.", 2, True),
    # System & Information Integrity
    CMMCControl(CMMCDomain.SYSTEM_INFO_INTEGRITY, "SI.L1-3.14.1", "Flaw Remediation",
                "Identify, report, and correct system flaws.", 1, True),
    CMMCControl(CMMCDomain.SYSTEM_INFO_INTEGRITY, "SI.L2-3.14.3", "Security Alerts",
                "Monitor security alerts and advisories.", 2, True),
]


def get_cmmc_controls() -> List[CMMCControl]:
    """Return the full list of tracked CMMC controls."""
    return list(_CONTROLS)


def get_compliance_score() -> dict:
    """Calculate overall and per-domain CMMC compliance scores."""
    controls = get_cmmc_controls()
    total = len(controls)
    met = sum(1 for c in controls if c.is_met)

    domain_map: dict[str, dict] = {}
    for c in controls:
        key = c.domain.value
        if key not in domain_map:
            domain_map[key] = {
                "domain": key,
                "domain_name": DOMAIN_NAMES[c.domain],
                "total_controls": 0,
                "met_controls": 0,
            }
        domain_map[key]["total_controls"] += 1
        if c.is_met:
            domain_map[key]["met_controls"] += 1

    domains = []
    for d in domain_map.values():
        d["percentage"] = round(d["met_controls"] / d["total_controls"] * 100) if d["total_controls"] else 0
        domains.append(d)

    return {
        "total_controls": total,
        "met_controls": met,
        "score_percentage": round(met / total * 100) if total else 0,
        "target_level": 2,
        "domains": sorted(domains, key=lambda x: x["domain"]),
    }


# NIST 800-53 control family overview
_NIST_FAMILIES = [
    {"family_id": "AC", "name": "Access Control", "total_controls": 25, "implemented": 8, "partial": 5, "not_implemented": 12},
    {"family_id": "AT", "name": "Awareness and Training", "total_controls": 6, "implemented": 1, "partial": 2, "not_implemented": 3},
    {"family_id": "AU", "name": "Audit and Accountability", "total_controls": 16, "implemented": 6, "partial": 4, "not_implemented": 6},
    {"family_id": "CA", "name": "Assessment, Authorization, and Monitoring", "total_controls": 9, "implemented": 2, "partial": 3, "not_implemented": 4},
    {"family_id": "CM", "name": "Configuration Management", "total_controls": 14, "implemented": 4, "partial": 3, "not_implemented": 7},
    {"family_id": "CP", "name": "Contingency Planning", "total_controls": 13, "implemented": 3, "partial": 2, "not_implemented": 8},
    {"family_id": "IA", "name": "Identification and Authentication", "total_controls": 13, "implemented": 6, "partial": 3, "not_implemented": 4},
    {"family_id": "IR", "name": "Incident Response", "total_controls": 10, "implemented": 3, "partial": 2, "not_implemented": 5},
    {"family_id": "MA", "name": "Maintenance", "total_controls": 7, "implemented": 1, "partial": 2, "not_implemented": 4},
    {"family_id": "MP", "name": "Media Protection", "total_controls": 8, "implemented": 2, "partial": 1, "not_implemented": 5},
    {"family_id": "PE", "name": "Physical and Environmental Protection", "total_controls": 23, "implemented": 3, "partial": 4, "not_implemented": 16},
    {"family_id": "PL", "name": "Planning", "total_controls": 11, "implemented": 2, "partial": 3, "not_implemented": 6},
    {"family_id": "PM", "name": "Program Management", "total_controls": 16, "implemented": 4, "partial": 3, "not_implemented": 9},
    {"family_id": "PS", "name": "Personnel Security", "total_controls": 9, "implemented": 2, "partial": 2, "not_implemented": 5},
    {"family_id": "RA", "name": "Risk Assessment", "total_controls": 10, "implemented": 3, "partial": 2, "not_implemented": 5},
    {"family_id": "SA", "name": "System and Services Acquisition", "total_controls": 23, "implemented": 5, "partial": 4, "not_implemented": 14},
    {"family_id": "SC", "name": "System and Communications Protection", "total_controls": 51, "implemented": 12, "partial": 8, "not_implemented": 31},
    {"family_id": "SI", "name": "System and Information Integrity", "total_controls": 23, "implemented": 7, "partial": 5, "not_implemented": 11},
    {"family_id": "SR", "name": "Supply Chain Risk Management", "total_controls": 12, "implemented": 2, "partial": 2, "not_implemented": 8},
]


def get_nist_overview() -> dict:
    """Return NIST 800-53 Rev 5 control family overview."""
    total_families = len(_NIST_FAMILIES)
    total_impl = sum(f["implemented"] for f in _NIST_FAMILIES)
    total_all = sum(f["total_controls"] for f in _NIST_FAMILIES)

    return {
        "framework": "NIST 800-53 Rev 5",
        "total_families": total_families,
        "families": _NIST_FAMILIES,
        "overall_coverage": round(total_impl / total_all * 100) if total_all else 0,
    }

"""Prompt templates for Gemini AI Service."""

DEEP_READ_PROMPT = """You are an expert government proposal analyst. Extract ALL compliance requirements from this RFP by systematically analyzing every section.

IMPORTANT: Government RFPs scatter requirements across multiple sections. You MUST analyze ALL of the following if present:

1. **Section C / SOW / PWS**: Technical requirements, deliverables, performance standards, SLAs, acceptance criteria
2. **Section H**: Key personnel, security clearances, OCI provisions, insurance/bonding/licensing
3. **Section L**: Proposal format, page limits, volume structure, submission instructions, certifications
4. **Section M**: Evaluation factors/subfactors, scoring methodology, relative importance
5. **Other sections** (J, F, etc.): CDRLs, data items, delivery schedules, reporting requirements

For EACH requirement provide:
1. Unique ID (e.g., REQ-001)
2. Granular source reference (e.g., "Section L.3.2 - Proposal Format")
3. source_section: one of "Section C", "Section H", "Section L", "Section M", "PWS", "SOW", "Section J", "Section F", "Other"
4. Exact requirement text
5. Importance: MANDATORY, EVALUATED, OPTIONAL, or INFORMATIONAL
6. Category: Technical, Management, Past Performance, Pricing, Administrative, Personnel, Quality, or Security
7. Page reference if available
8. Key terms/keywords

CRITICAL:
- MANDATORY requirements use "shall", "must", "required" language
- Look for evaluation criteria in Section M for scored items
- Include ALL deliverables, certifications, and format requirements
- Do NOT skip Section C/PWS requirements — these are often the most critical

RFP DOCUMENT:
{rfp_text}

Respond with ONLY valid JSON in this format:
{{
    "requirements": [
        {{
            "id": "REQ-001",
            "section": "Section C.3.1 - Software Development",
            "source_section": "Section C",
            "requirement_text": "The contractor shall provide...",
            "importance": "mandatory",
            "category": "Technical",
            "page_reference": 12,
            "keywords": ["contractor", "provide", "deliverable"],
            "confidence": 0.95
        }}
    ],
    "summary": "Brief summary of the RFP scope",
    "total_mandatory": 5,
    "confidence": 0.95
}}"""

GENERATION_PROMPT = """You are an expert government proposal writer. Write a response to address this requirement.

REQUIREMENT:
{requirement_text}

SECTION: {section}
CATEGORY: {category}

INSTRUCTIONS:
1. Write a compelling, compliant response
2. EVERY factual claim MUST cite the source document
3. Use this EXACT citation format: [[Source: filename.pdf, Page XX]]
4. Be specific about experience, metrics, and qualifications
5. Match the required tone: {tone}
6. Target word count: approximately {max_words} words
7. If a WRITING PLAN is included above, follow its guidance on key points, themes, strengths to highlight, and tone preferences

If the Knowledge Base doesn't contain relevant information, state that clearly.

Write the response now:"""

REWRITE_PROMPT = """You are an expert government proposal writer. Rewrite the following proposal content.

CURRENT CONTENT:
{content}

REQUIREMENT BEING ADDRESSED:
{requirement_text}

INSTRUCTIONS:
1. Rewrite in a {tone} tone
2. Maintain all factual claims and citations from the original
3. Use this EXACT citation format: [[Source: filename.pdf, Page XX]]
4. Preserve the meaning but improve clarity, flow, and compliance
{custom_instructions}

Rewrite the content now:"""

EXPAND_PROMPT = """You are an expert government proposal writer. Expand the following proposal content with more detail.

CURRENT CONTENT:
{content}

REQUIREMENT BEING ADDRESSED:
{requirement_text}

INSTRUCTIONS:
1. Expand the content to approximately {target_words} words
2. Add more specific details, metrics, and evidence
3. Maintain the existing tone and style
4. Use this EXACT citation format: [[Source: filename.pdf, Page XX]]
5. Every new factual claim MUST cite the source document
{focus_instructions}

Expand the content now:"""

OUTLINE_PROMPT = """You are an expert government proposal architect. Generate a structured proposal outline from these compliance requirements.

REQUIREMENTS:
{requirements_json}

RFP SUMMARY:
{rfp_summary}

INSTRUCTIONS:
1. Create a standard government proposal structure (Executive Summary, Technical Approach, Management, Past Performance, etc.)
2. Map each requirement to the most appropriate section
3. Nest subsections where logical (e.g., "3.1 Software Development" under "3. Technical Approach")
4. Estimate page count per section based on requirement complexity
5. Include a description for each section explaining what it should cover

Respond with ONLY valid JSON:
{{
    "sections": [
        {{
            "title": "Executive Summary",
            "description": "High-level overview of the offeror's approach",
            "mapped_requirement_ids": [],
            "estimated_pages": 2,
            "children": []
        }},
        {{
            "title": "Technical Approach",
            "description": "Detailed technical solution",
            "mapped_requirement_ids": ["REQ-001"],
            "estimated_pages": 10,
            "children": [
                {{
                    "title": "Software Development Methodology",
                    "description": "Agile approach and SDLC processes",
                    "mapped_requirement_ids": ["REQ-002", "REQ-003"],
                    "estimated_pages": 3,
                    "children": []
                }}
            ]
        }}
    ]
}}"""

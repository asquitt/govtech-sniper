"""
Graphics Generator Unit Tests
===============================
Tests for _placeholder_mermaid, generate_graphic validation, and TEMPLATE_TYPES.
"""

import pytest

from app.services.graphics_generator import (
    TEMPLATE_PROMPTS,
    TEMPLATE_TYPES,
    _placeholder_mermaid,
    generate_graphic,
)

# ---------------------------------------------------------------------------
# TEMPLATE_TYPES / TEMPLATE_PROMPTS
# ---------------------------------------------------------------------------


class TestTemplateConstants:
    def test_all_types_have_prompts(self):
        for t in TEMPLATE_TYPES:
            assert t in TEMPLATE_PROMPTS, f"Missing prompt for template type: {t}"

    def test_expected_types(self):
        expected = {"management_approach", "staffing_plan", "timeline", "org_chart", "process_flow"}
        assert expected == set(TEMPLATE_TYPES)

    def test_prompts_non_empty(self):
        for key, prompt in TEMPLATE_PROMPTS.items():
            assert len(prompt) > 20, f"Prompt for {key} is too short"


# ---------------------------------------------------------------------------
# _placeholder_mermaid
# ---------------------------------------------------------------------------


class TestPlaceholderMermaid:
    def test_timeline_returns_gantt(self):
        result = _placeholder_mermaid("timeline", "Project Timeline")
        assert "gantt" in result
        assert "Project Timeline" in result

    def test_staffing_plan_returns_gantt(self):
        result = _placeholder_mermaid("staffing_plan", None)
        assert "gantt" in result
        assert "Staffing Plan" in result  # title-cased from template_type

    def test_flowchart_types(self):
        for t in ["management_approach", "org_chart", "process_flow"]:
            result = _placeholder_mermaid(t, None)
            assert "flowchart" in result

    def test_custom_title(self):
        result = _placeholder_mermaid("org_chart", "My Org")
        assert "My Org" in result

    def test_no_title_uses_type_name(self):
        result = _placeholder_mermaid("process_flow", None)
        assert "Process Flow" in result


# ---------------------------------------------------------------------------
# generate_graphic
# ---------------------------------------------------------------------------


class TestGenerateGraphic:
    @pytest.mark.asyncio
    async def test_invalid_template_type_raises(self):
        with pytest.raises(ValueError, match="Unknown template type"):
            await generate_graphic(
                content="Some content",
                template_type="nonexistent_type",
                title="Test",
            )

    @pytest.mark.asyncio
    async def test_valid_type_returns_placeholder_without_api_key(self):
        # Without a valid API key, falls back to placeholder
        result = await generate_graphic(
            content="Phase 1 planning, phase 2 execution.",
            template_type="timeline",
            title="Test Timeline",
        )
        assert result["template_type"] == "timeline"
        assert "mermaid_code" in result
        assert len(result["mermaid_code"]) > 0

    @pytest.mark.asyncio
    async def test_title_defaults(self):
        result = await generate_graphic(
            content="Content here",
            template_type="org_chart",
            title=None,
        )
        assert result["title"] == "Generated Graphic"

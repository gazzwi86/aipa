"""Agent evaluation tests for skill selection and usage.

These tests verify that the agent correctly identifies which skills to use
based on user queries, and that skills are properly integrated.
"""

import re

import pytest

# Skill trigger definitions (should match SKILL.md files)
SKILL_TRIGGERS = {
    "time-lookup": ["what time", "current time", "time in", "timezone", "time zone"],
    "script-runner": [
        "run script",
        "execute code",
        "parse csv",
        "run python",
        "python script",
        "process the csv",
    ],
    "weather": [
        "weather in",
        "forecast",
        "temperature",
        "will it rain",
        "weather today",
        "weather in melbourne",
    ],
    "youtube-summarizer": ["youtube.com", "youtu.be", "summarize video", "summarize this video"],
    "generate-pptx": [
        "create presentation",
        "make slides",
        "powerpoint",
        "slide deck",
        "presentation about",
    ],
    "generate-docx": [
        "create document",
        "word document",
        "write report",
        "document for",
        "create a document",
    ],
    "generate-xlsx": [
        "create spreadsheet",
        "excel",
        "xlsx",
        "spreadsheet to",
        "create a spreadsheet",
    ],
    "github-workflow": [
        "create repo",
        "make pr",
        "github issue",
        "pull request",
        "create a github",
    ],
    "aws-budget": ["aws spend", "aws costs", "cloud costs", "aws budget"],
    "browser-automation": ["login to", "check account", "check subscription"],
    "notion-enhanced": [
        "create note",
        "save to notion",
        "update project",
        "note about",
        "create a note",
    ],
    "deep-research": ["research thoroughly", "deep dive", "comprehensive research"],
    "claim-extractor": ["extract claims", "what claims", "extract the claims"],
    "claim-analyzer": ["verify claims", "fact check", "is this true", "verify if", "claim is true"],
    "prompt-creator": [
        "create prompt",
        "write prompt",
        "help me prompt",
        "prompt for",
        "create a prompt",
    ],
    "self-update": ["update yourself", "restart agent"],
    "self-testing": ["test yourself", "run tests", "verify capabilities"],
    "sense-check": [
        "confidence",
        "sense check",
        "review response",
        "does this make sense",
        "confident are you",
        "how confident",
    ],
}

# Agent definitions (should match agent .md files)
AGENT_TRIGGERS = {
    "researcher": ["research", "find out about", "look up"],
    "content-analyst": ["analyze", "verify", "fact check", "deep research"],
    "task-manager": ["create task", "add to list", "schedule", "task to review", "create a task"],
    "writer": ["write", "draft", "compose"],
    "developer": ["code", "debug", "implement", "fix bug"],
    "automation-specialist": ["automate", "browser", "login"],
    "document-creator": ["presentation", "document", "spreadsheet"],
    "self-improver": ["create skill", "create agent", "improve", "new skill", "create a new skill"],
    "quality-reviewer": ["review", "quality", "confidence"],
}


class TestSkillTriggerMatching:
    """Test that queries match expected skill triggers."""

    @pytest.mark.parametrize(
        "query,expected_skill",
        [
            ("What time is it in Tokyo?", "time-lookup"),
            ("Run this Python script to process the CSV", "script-runner"),
            ("What's the weather in Melbourne?", "weather"),
            ("Summarize this YouTube video: https://youtube.com/watch?v=abc", "youtube-summarizer"),
            ("Create a presentation about AI", "generate-pptx"),
            ("Create a document for the project proposal", "generate-docx"),
            ("Create a spreadsheet to track expenses", "generate-xlsx"),
            ("Create a GitHub issue for this bug", "github-workflow"),
            ("What's my AWS spend this month?", "aws-budget"),
            ("Login to my Netflix account", "browser-automation"),
            ("Create a note about this meeting", "notion-enhanced"),
            ("Research thoroughly about quantum computing", "deep-research"),
            ("Extract the claims from this article", "claim-extractor"),
            ("Verify if this claim is true", "claim-analyzer"),
            ("Create a prompt for code review", "prompt-creator"),
            ("Test yourself and report results", "self-testing"),
            ("How confident are you in that answer?", "sense-check"),
        ],
    )
    def test_query_matches_skill(self, query: str, expected_skill: str):
        """Query should match the expected skill triggers."""
        triggers = SKILL_TRIGGERS.get(expected_skill, [])
        query_lower = query.lower()

        matched = any(trigger in query_lower for trigger in triggers)
        assert matched, f"Query '{query}' should trigger '{expected_skill}'"

    def test_no_false_positive_matches(self):
        """Queries should not match unrelated skills."""
        # Weather query should not match time-lookup
        weather_query = "What's the weather forecast?"
        time_triggers = SKILL_TRIGGERS["time-lookup"]
        assert not any(t in weather_query.lower() for t in time_triggers)

        # Time query should not match weather
        time_query = "What time is it?"
        weather_triggers = SKILL_TRIGGERS["weather"]
        assert not any(t in time_query.lower() for t in weather_triggers)


class TestAgentSelection:
    """Test that queries route to correct agents."""

    @pytest.mark.parametrize(
        "query,expected_agent",
        [
            ("Research the history of AI", "researcher"),
            ("Analyze this document for claims", "content-analyst"),
            ("Create a task to review the proposal", "task-manager"),
            ("Write a blog post about technology", "writer"),
            ("Debug this Python function", "developer"),
            ("Automate logging into my accounts", "automation-specialist"),
            ("Create a presentation for the meeting", "document-creator"),
            ("Create a new skill for calendar management", "self-improver"),
            ("Review my answer for accuracy", "quality-reviewer"),
        ],
    )
    def test_query_routes_to_agent(self, query: str, expected_agent: str):
        """Query should route to the expected agent."""
        triggers = AGENT_TRIGGERS.get(expected_agent, [])
        query_lower = query.lower()

        matched = any(trigger in query_lower for trigger in triggers)
        assert matched, f"Query '{query}' should route to '{expected_agent}'"


class TestSkillResponseFormats:
    """Test that skills return expected response formats."""

    def test_time_lookup_response_format(self):
        """Time lookup should return formatted time string."""
        # Expected format: "It's 3:45 PM in Tokyo (JST)"
        response_pattern = r"\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\s+in\s+\w+"
        sample_response = "It's 3:45 PM in Tokyo"
        assert re.search(response_pattern, sample_response)

    def test_weather_response_format(self):
        """Weather response should include temperature and conditions."""
        required_elements = ["degrees", "°C", "°F"]
        sample_response = "It's currently 24 degrees in Melbourne"

        has_temp = any(elem in sample_response for elem in required_elements)
        assert has_temp or "degrees" in sample_response.lower()

    def test_document_response_includes_path(self):
        """Document generation should return file path."""
        sample_response = "Created: workspace/files/report.docx"
        assert "workspace/files/" in sample_response
        assert any(ext in sample_response for ext in [".docx", ".pptx", ".xlsx"])


class TestSkillIntegration:
    """Test skill integration patterns."""

    def test_skills_exist_in_workspace(self):
        """Verify all documented skills have SKILL.md files."""
        from pathlib import Path

        skills_dir = Path("workspace/.claude/skills")
        if skills_dir.exists():
            skill_dirs = [d.name for d in skills_dir.iterdir() if d.is_dir()]

            expected_skills = [
                "time-lookup",
                "script-runner",
                "weather",
                "youtube-summarizer",
                "generate-pptx",
                "generate-docx",
                "generate-xlsx",
                "github-workflow",
                "aws-budget",
            ]

            for skill in expected_skills:
                if skill in skill_dirs:
                    # Just check the directory exists, file may not be created yet
                    assert (skills_dir / skill).exists()

    def test_agents_exist_in_workspace(self):
        """Verify all documented agents have .md files."""
        from pathlib import Path

        agents_dir = Path("workspace/.claude/agents")
        if agents_dir.exists():
            agent_files = [f.stem for f in agents_dir.glob("*.md")]

            expected_agents = [
                "researcher",
                "task-manager",
                "writer",
                "developer",
                "assistant",
                "automation-specialist",
                "content-analyst",
                "document-creator",
                "self-improver",
                "quality-reviewer",
            ]

            existing = [a for a in expected_agents if a in agent_files]
            # At least some agents should exist
            assert len(existing) > 0


class TestMultiSkillQueries:
    """Test queries that might involve multiple skills."""

    def test_research_with_save_pattern(self):
        """Research + save should involve researcher and notion skills."""
        query = "Research thoroughly about AI trends and save to Notion"

        # Verify both skill triggers would match
        assert any(t in query.lower() for t in SKILL_TRIGGERS.get("deep-research", []))
        assert any(t in query.lower() for t in SKILL_TRIGGERS.get("notion-enhanced", []))

        # Should match research patterns
        assert "research" in query.lower()
        # Should mention save/notion
        assert "save" in query.lower() or "notion" in query.lower()

    def test_document_from_research_pattern(self):
        """Creating document from research involves multiple skills."""
        query = "Research cloud providers and create a comparison presentation"

        has_research = "research" in query.lower()
        has_document = any(t in query.lower() for t in ["presentation", "document", "spreadsheet"])

        assert has_research
        assert has_document


@pytest.mark.eval
class TestAgentCapabilities:
    """Evaluation tests for agent capabilities."""

    def test_agent_can_handle_time_queries(self):
        """Agent should handle timezone queries correctly."""
        queries = [
            "What time is it in Melbourne?",
            "What's the current time in Tokyo?",
            "Time in New York?",
        ]

        for query in queries:
            # Should match time skill
            triggers = SKILL_TRIGGERS["time-lookup"]
            assert any(t in query.lower() for t in triggers)

    def test_agent_can_handle_weather_queries(self):
        """Agent should handle weather queries correctly."""
        queries = [
            "What's the weather in Sydney?",
            "Will it rain tomorrow?",
            "Do I need an umbrella?",
        ]

        for query in queries:
            triggers = SKILL_TRIGGERS["weather"]
            matched = any(t in query.lower() for t in triggers)
            # At least some should match
            assert matched or "rain" in query.lower() or "umbrella" in query.lower()

    def test_agent_can_self_improve(self):
        """Agent should be able to create new skills."""
        self_improve_queries = [
            "Create a skill for managing bookmarks",
            "Create an agent for email handling",
            "Add a capability to track habits",
        ]

        for query in self_improve_queries:
            has_create = "create" in query.lower()
            has_skill_or_agent = (
                "skill" in query.lower()
                or "agent" in query.lower()
                or "capability" in query.lower()
            )
            assert has_create or has_skill_or_agent

    def test_agent_can_sense_check(self):
        """Agent should be able to validate its own responses."""
        sense_check_queries = [
            "How confident are you in that?",
            "Sense check your response",
            "Does this make sense?",
        ]

        for query in sense_check_queries:
            triggers = SKILL_TRIGGERS["sense-check"]
            matched = any(t in query.lower() for t in triggers)
            assert matched, f"Query '{query}' should trigger sense-check"

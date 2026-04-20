"""
Phase 1 verification: confirms CrewAI imports and Gemini LLM connection work.

Run with:
    python tests/test_connection.py
"""

import logging
import sys
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Env ───────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
import os

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key or api_key == "your_google_api_key_here":
    logger.error("GOOGLE_API_KEY not set in .env — update it before running this test.")
    sys.exit(1)

# CrewAI reads GEMINI_API_KEY via litellm — mirror the value
os.environ["GEMINI_API_KEY"] = api_key


def test_crewai_import() -> bool:
    """Verify CrewAI can be imported without errors."""
    try:
        from crewai import Agent, Task, Crew, Process, LLM  # noqa: F401
        logger.info("CrewAI import: OK")
        return True
    except ImportError as exc:
        logger.error("CrewAI import failed: %s", exc)
        return False


def test_gemini_connection() -> bool:
    """Send a minimal prompt to Gemini 2.0 Flash via google-genai and verify a response."""
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly: HELLO SEN",
        )
        content: str = response.text.strip()
        logger.info("Gemini response: %r", content)

        if "HELLO SEN" not in content.upper():
            logger.warning("Unexpected response content — check manually.")

        logger.info("Gemini connection: OK")
        return True
    except Exception as exc:
        logger.error("Gemini connection failed: %s", exc)
        return False


def test_crewai_agent_with_gemini() -> bool:
    """Create a minimal CrewAI agent backed by Gemini and run a single task."""
    try:
        from crewai import Agent, Task, Crew, Process, LLM

        llm = LLM(
            model="gemini/gemini-2.5-flash",
            api_key=api_key,
            temperature=0.0,
        )

        hello_agent = Agent(
            role="Test Agent",
            goal="Confirm the SEN pipeline is reachable.",
            backstory="A minimal agent created only to verify the stack works.",
            llm=llm,
            verbose=False,
        )

        hello_task = Task(
            description="Reply with exactly: SEN STACK VERIFIED",
            expected_output="SEN STACK VERIFIED",
            agent=hello_agent,
        )

        crew = Crew(
            agents=[hello_agent],
            tasks=[hello_task],
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()
        logger.info("Crew result: %r", str(result))
        logger.info("CrewAI + Gemini end-to-end: OK")
        return True
    except Exception as exc:
        logger.error("CrewAI + Gemini test failed: %s", exc)
        return False


if __name__ == "__main__":
    results = {
        "crewai_import": test_crewai_import(),
        "gemini_connection": test_gemini_connection(),
        "crewai_agent_e2e": test_crewai_agent_with_gemini(),
    }

    passed = sum(results.values())
    total = len(results)
    logger.info("Phase 1 results: %d/%d passed", passed, total)

    if passed < total:
        failed = [k for k, v in results.items() if not v]
        logger.error("Failed checks: %s", failed)
        sys.exit(1)

    logger.info("Phase 1 COMPLETE — all checks passed.")

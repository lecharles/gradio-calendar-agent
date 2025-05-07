# Other Agent Tryouts — README

This folder contains experimental agents, prototypes, and scripts that are **not part of the main Meeting Rescheduler Agent**. These files are kept for reference, future development, or as examples of using the OpenAI Agents SDK and related tools.

## Purpose
- To separate experimental and non-core agent code from the main meeting rescheduler package.
- To provide a space for trying out new agent ideas, multi-agent orchestration, PDF extraction, and other LLM-powered workflows.
- To serve as a reference for future agent development or integration.

## Contents

Below is a list of the main scripts and what each one does:

### `agent_pdf_extractor_vibe.py`
- **Purpose:** An agent that scrapes a web page for PDF links (e.g., arXiv), downloads and analyzes each PDF for prompt engineering relevance, and outputs structured data (title, summary, year, authors, technique type, etc.).
- **Status:** Functional. Includes robust PDF text extraction and markdown export. Uses OpenAI Agents SDK tools.

### `agent_pdf_extractor_vibe` (short script)
- **Purpose:** A minimal example or test script for extracting structured data from a single PDF using OpenAI.
- **Status:** Example/utility. Not a full agent.

### `structured_data_extract.py`
- **Purpose:** Script for extracting structured event data from a PDF using OpenAI and Pydantic models.
- **Status:** Example/utility. Not a full agent.

### `agent_as_tools.py`
- **Purpose:** Demonstrates how to wrap agent logic as tools for use in multi-agent systems or for direct function testing.
- **Status:** Example/utility. Not a full agent.

### `agent_tools.py`
- **Purpose:** Contains reusable tool functions for agent workflows, such as PDF extraction, text analysis, etc.
- **Status:** Utility module. Used by other agent scripts.

### `multi_agent_system.py`
- **Purpose:** Example of orchestrating multiple agents (e.g., invoice, billing, refund) and agent-to-agent handoff using the OpenAI Agents SDK.
- **Status:** Experimental. Demonstrates multi-agent orchestration.

### `example_agent.py`
- **Purpose:** A simple example agent script for testing or demonstration purposes.
- **Status:** Example/utility. Not a production agent.

## Notes
- These scripts are **not maintained as production code** and may require updates to run with the latest dependencies.
- For the main meeting rescheduler agent, see the `meeting_rescheduler/` directory and the main project README.

---

**For questions or contributions, please contact the project maintainer or see the main project documentation.** 
# Story 13 - Hallucination Detection and Prevention in Subtitle Translation

## Problem Statement
Subtitle translation models (especially MarianMT and similar AI models) sometimes hallucinate or substitute lines with content that is not present in the original. This is most common with:
- Subtitle credits (e.g., "Synced & corrected by ...", website links)
- Translator names (e.g., "Fordította: Krizmo és Sutszi")
- Website URLs (e.g., "www.addic7ed.com")
- Common subtitle metadata (e.g., "HI removed", "Resynced by ...")
- Copyright warnings or disclaimers
- Episode/season info (e.g., "Season 2, Episode 5")

These hallucinations can result in:
- Inaccurate credits (wrong translator names, websites)
- Unintended copyright or legal statements
- Loss of original metadata
- Insertion of irrelevant or misleading information

## Acceptance Criteria
- Identify all common hallucination patterns in subtitle translation output
- Detect lines likely to be hallucinated (credits, URLs, metadata, etc.)
- Provide configurable options for handling these lines:
  - Copy original line as-is (no translation)
  - Replace with a neutral message (e.g., "Subtitle credit removed")
  - Remove line entirely
  - Custom user-defined replacement
- Ensure that normal dialogue and narrative lines are not affected
- Document all known hallucination types and recommended handling strategies

## Technical Requirements
- Implement detection logic for credit lines, URLs, metadata, and common hallucination triggers
- Integrate detection into translation pipeline (pre- or post-processing)
- Add configuration options for user control over handling
- Provide test cases for all known hallucination scenarios
- Ensure compatibility with both MarianMT and Ollama backends

## Example Hallucination Types
- Translator credits: "Fordította: ...", "Translated by ..."
- Website links: "www.addic7ed.com", "www.subscene.com"
- Sync/correction info: "Synced & corrected by ...", "Resynced by ..."
- Copyright warnings: "Do not upload to ...", "For personal use only"
- Episode/season info: "Season 2, Episode 5"

## Workaround Strategies
- Regex-based detection of credit/metadata lines
- Configurable skip/replace/copy logic
- Option to preserve original for specific patterns
- User documentation for best practices

## Next Steps
- Research additional hallucination patterns in subtitle translation
- Implement detection and handling logic
- Add tests and documentation
- Gather user feedback for further refinement

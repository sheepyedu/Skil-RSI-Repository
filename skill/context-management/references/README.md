# Reviewable indexes

CASE_LOCATORS.json contains 502 execution directories including retries, not 502 independent tasks. CONTEXT_EVENT_LOCATORS.json contains 722 machine-collected locator records spanning event types and raw/request-level records, **not 722 independent edits**. Deduplicate accepted counts by run. Indexes retain source, event position/type, not task answers or complete requests.

Extract the repository archives anywhere, mapping group prefixes as follows: claude_native to root grouped/shuffled archives; claude_clm to the Claude CLM archive; codex_native/codex_clm to the corresponding Codex tar archives. Index source paths are relative to the restoration root; some include case/context-events or runs/wire. Recheck inferences in [EVIDENCE](../EVIDENCE.md) using original events and surrounding responses.

These indexes establish locatability, not a substitute for per-case semantic review. See EVIDENCE for coverage limits. They were generated in the four-platform offline review stage, for research auditing only. Do not load or install these research indexes into the skill runtime. Machine identifiers and historical source paths remain unchanged in both language editions for reproducibility.

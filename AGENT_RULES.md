# Agent Rules & Prompt Hygiene

All agent-facing prompts (Segmentation, NarrativeFormatter, Fin Performance, etc.) must follow these rules in addition to the development standards:

1. **Roles First** – Begin every prompt with the agent’s charter (“You are the NarrativeFormatter for Hilary’s ops meeting...”).  
2. **Data Disclosure** – Enumerate exactly what data is being passed (sample counts, tiers, known limitations). If you only pass ten examples, explicitly state “Use these 10 representative samples” and forbid requesting the full dataset.  
3. **Non-Contradiction** – Remove conflicting instructions. Prompts must contain a single directive for tone/audience/length.  
4. **Citations & Grounding** – Remind agents to cite conversation IDs/Intercom URLs and acknowledge gaps instead of inventing evidence.  
5. **Examples** – Include at least one “good” and one “avoid” example for complex outputs (sentiment statements, executive summaries, etc.).  
6. **LLM Operations** – Keep prompts aligned with current timeout/semaphore settings. Do not change multiple operational controls at once; follow the LLM Operational Controls workflow in `DEVELOPMENT_STANDARDS.md`.  
7. **Prompt Audit Log** – Every prompt change must be recorded (before/after summary + reason) either in pull request notes or `PROMPT_CATALOG.md`.

> Run the full Prompt Audit Checklist in `DEVELOPMENT_STANDARDS.md` before merging any prompt change. This policy exists because the TopicSentimentAgent regression (Nov 2025) was caused by missing representative-language in the prompt.




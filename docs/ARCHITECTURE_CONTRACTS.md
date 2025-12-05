# Architecture Contracts

## Data Traceability Contract

- **Every agent output**: `sample_conversations: List[{'id', 'created_at', 'url', 'snippet'}]` (min 2-3 per category)
- **date_range**: `{'min_created_at', 'max_created_at'}` computed from raw `created_at`
- **NarrativeFormatter**: Renders tables w/ dates + `[snippet](url)` in BPO/Fin/Topics/Metrics
- **URL Format**: `https://app.intercom.com/a/apps/{settings.intercom_workspace_id}/conversations/{id}`

**Consumers**: Executive markdown → Gamma slides

**Validation**: `_validate_critical_sections()` checks samples present









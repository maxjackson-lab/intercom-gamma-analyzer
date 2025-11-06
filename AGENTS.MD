# Agent Guidelines

## Code Review Process

After making code changes, you MUST call the `review_code` tool from the Quibbler MCP server with:

- `user_instructions`: The exact instructions the user gave you

- `agent_plan`: **A summary of the specific changes you made** (include which files were modified, what was added/changed, and key implementation details)

- `project_path`: The absolute path to this project (use `pwd` command to get it)

Review Quibbler's feedback and address any issues or concerns raised.

### Example

User asks: "Add logging to the API endpoints"

After implementing, call:

```python
review_code(
    user_instructions="Add logging to the API endpoints",
    agent_plan="""Changes made:
1. Added logger configuration in config/logging.py
2. Updated routes/api.py to log incoming requests and responses
3. Added request_id middleware for tracing
4. Created logs/ directory with .gitignore""",
    project_path="/Users/max.jackson/Intercom Analysis Tool "  # Use pwd command to get this
)
```

### How to Use Quibbler

Quibbler is an MCP server that provides automated code review capabilities. It checks for:
- Quality issues
- Pattern violations
- Hallucinations
- Alignment with user intent

Always invoke Quibbler after completing implementation work to ensure code quality and catch potential issues early.


# Claude Code + Codex CLI Orchestration Workflow

## Setup Complete ✅

**Codex MCP** has been added to your project's `.mcp.json` file.

## How It Works

### Architecture
```
┌─────────────────┐
│  Claude Code    │ ← You interact here (Orchestrator)
│  (Taskmaster)   │
└────────┬────────┘
         │ Delegates tasks via MCP
         ▼
┌─────────────────┐
│  Codex CLI      │ ← Execution Agent
│  (via MCP)      │
└─────────────────┘
```

## Workflow Steps

### 1. Start Your Claude Code Session
```bash
cd C:\claude\Email-Management-Tool
claude
```

### 2. Tell Claude Your Intent
Example prompt:
```
I want you to orchestrate this task using Codex CLI as your execution agent.

Use the codex-subagent MCP to:
1. Create a Python script that [describe task]
2. Test it
3. Report back the results

You should use Codex to do the actual coding work while you coordinate and validate.
```

### 3. Claude Orchestrates, Codex Executes

**Claude will:**
- Break down your request into subtasks
- Use `codex-subagent:execute_task` to delegate work to Codex
- Monitor progress
- Validate results
- Report back to you

**Codex will:**
- Receive tasks from Claude via MCP
- Execute the coding work
- Return results to Claude

## Example Interaction Pattern

### You → Claude:
```
"Create a complete email parser using Codex. 
Have Codex write the code, test it, and fix any issues."
```

### Claude → Codex (via MCP):
```json
{
  "tool": "codex-subagent:execute_task",
  "task": "Create email parser with MIME support",
  "requirements": ["Parse headers", "Extract attachments", "Handle multipart"]
}
```

### Codex → Claude:
```
✅ Task completed
- Created email_parser.py
- Added tests
- All tests passing
```

### Claude → You:
```
Codex has successfully created the email parser. 
Here's what was built: [summary]
Would you like me to have Codex add any additional features?
```

## Available Codex MCP Tools

When Claude calls codex-subagent, it has access to:
- `execute_task` - Delegate coding tasks to Codex
- `get_task_status` - Check on Codex's progress

## Tips for Best Results

### 1. Be Explicit About Orchestration
❌ "Write me a script"
✅ "Use Codex via MCP to write me a script"

### 2. Let Claude Coordinate
Claude should:
- Define requirements
- Validate outputs
- Request fixes/improvements
- Manage the overall workflow

### 3. Let Codex Execute
Codex should:
- Write the actual code
- Run tests
- Debug issues
- Implement features

### 4. Use Taskmaster Features
With taskmaster-ai active, you can:
- Track tasks in a hierarchy
- Monitor progress
- Pause/resume work
- Review completed items

## Example Prompts

### Simple Task
```
"Use Codex to create a quick file organizer script. 
Have it report back when done."
```

### Complex Project
```
"I need you to coordinate with Codex to build a complete 
email management system. Break it down into:
1. Parser module (Codex builds)
2. Storage layer (Codex builds)
3. API interface (Codex builds)

You review each component and request improvements as needed."
```

### Debugging Session
```
"The email parser is failing on attachments. 
Work with Codex to debug and fix this issue."
```

## Monitoring Progress

Claude can check on Codex's work:
```
Claude: "What's the status of the task I gave you?"
↓
Codex: "Currently implementing attachment extraction, 
        80% complete, ETA 2 minutes"
```

## When to Restart

If you need to restart the orchestration:

1. **Keep taskmaster state:** Just continue in current Claude session
2. **Fresh start:** Exit Claude Code and run `claude` again

## File Structure

Your project now has:
```
C:\claude\Email-Management-Tool\
├── .mcp.json                    ← Codex MCP configured here
├── CLAUDE-CODEX-WORKFLOW.md     ← This guide
└── [your project files]
```

## Quick Reference

| What | Who | How |
|------|-----|-----|
| Define requirements | You | Natural language to Claude |
| Coordinate workflow | Claude | Uses taskmaster + codex MCP |
| Execute coding tasks | Codex | Via MCP from Claude |
| Review & iterate | Claude | Validates Codex output |
| Approve/adjust | You | Guide Claude's decisions |

---

**Ready to start!** Tell Claude what you want built, and specify that you want it to use Codex as the execution agent.

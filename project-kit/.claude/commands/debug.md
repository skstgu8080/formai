# Debug Command

Investigate and fix bugs systematically.

## Usage

```
/debug [error-message]
/debug [file-path] [line-number]
/debug --logs             # Analyze recent logs
/debug --trace [function] # Trace function execution
```

## Debug Process

1. **Reproduce**
   - Confirm the issue
   - Identify environment
   - Note error messages

2. **Investigate**
   - Check logs
   - Review recent changes
   - Trace code execution

3. **Isolate**
   - Narrow down to specific code
   - Create minimal reproduction

4. **Fix & Verify**
   - Implement fix
   - Add regression test
   - Verify no side effects

## Output

Provide:
- Root cause analysis
- Proposed fix with explanation
- Regression test
- Prevention recommendations

Reference @.claude/Agents/debugger.md for investigation template.

---
name: code-review
description: Perform code review focusing on quality, security, and best practices
disable-model-invocation: true
allowed-tools: Read, Grep, Glob
---

# Code Review Checklist

When reviewing code, evaluate the following areas:

## 1. Code Quality

- [ ] Code is readable and self-documenting
- [ ] Functions are small and focused (single responsibility)
- [ ] Variable names are descriptive
- [ ] No code duplication (DRY principle)
- [ ] Proper error handling

## 2. Type Safety

### Python
- [ ] Type hints on all function parameters and returns
- [ ] Pydantic models for data validation
- [ ] No implicit `Any` types

### TypeScript
- [ ] No `any` types
- [ ] Interfaces defined for all data structures
- [ ] Proper null/undefined handling

## 3. Security

- [ ] No hardcoded secrets or API keys
- [ ] SQL injection prevention (parameterized queries)
- [ ] Input validation on all user inputs
- [ ] Proper authentication checks
- [ ] No sensitive data in logs

## 4. Performance

- [ ] Async operations for I/O
- [ ] No N+1 query problems
- [ ] Proper database indexing considered
- [ ] Large data sets paginated

## 5. Project-Specific

### LangChain/LangGraph
- [ ] Proper error handling for LLM calls
- [ ] Token limits considered
- [ ] Prompts are clear and well-structured

### FastAPI
- [ ] Proper HTTP status codes
- [ ] Request/response models defined
- [ ] Dependency injection used correctly

### React
- [ ] Components properly memoized if needed
- [ ] useEffect dependencies correct
- [ ] No memory leaks (cleanup functions)

## Review Output Format

Provide feedback in this structure:

```
## Summary
Brief overview of the changes

## Issues Found
1. **[Critical/Major/Minor]** Description
   - File: path/to/file.py:123
   - Suggestion: How to fix

## Positive Notes
What was done well

## Recommendations
Optional improvements
```

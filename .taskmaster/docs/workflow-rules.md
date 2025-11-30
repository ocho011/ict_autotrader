# Workflow Rules for Task Completion

## Critical Rules - MUST Follow

### Rule 1: Test-Driven Development
- Write tests BEFORE marking task as done
- All tests MUST pass (`pytest tests/`)
- Minimum coverage: 80%

### Rule 2: Git Commit Per Subtask
Each subtask completion requires:
```bash
git add .
git commit -m "feat(task-X.Y): [subtask title]

- Implementation details
- Key changes

Refs: Task X.Y"
git push origin main
```

### Rule 3: Documentation Update
Update relevant documentation:
- `docs/architecture.md` - for new components
- `docs/testing.md` - for test strategies
- Code docstrings - for all public functions/classes
- `README.md` - for usage changes

### Rule 4: Completion Checklist
Before marking subtask as done:
- [ ] Code implemented
- [ ] Tests written and passing
- [ ] Docstrings added
- [ ] Git committed and pushed
- [ ] Documentation updated
- [ ] `task-master set-status --id=X.Y --status=done`

## Commit Message Format

```
<type>(task-X.Y): <subject>

<body>

Refs: Task X.Y
```

**Types:**
- `feat` - New feature
- `test` - Add/modify tests
- `docs` - Documentation
- `fix` - Bug fix
- `refactor` - Code refactoring

## DO NOT:
❌ Commit without tests
❌ Mark task done without documentation
❌ Batch multiple subtasks in one commit
❌ Skip docstrings

## Example Workflow

```bash
# 1. Start subtask
task-master set-status --id=1.1 --status=in-progress

# 2. Implement code
# ... coding ...

# 3. Write tests
# ... write tests in tests/ ...

# 4. Run tests
pytest tests/

# 5. Update docs
# ... update docs/architecture.md ...

# 6. Commit & Push
git add .
git commit -m "feat(task-1.1): Create directory structure

- Created src/ with all subdirectories
- Created tests/, docs/, logs/
- Added all __init__.py files

Refs: Task 1.1"
git push origin main

# 7. Mark done
task-master set-status --id=1.1 --status=done
```

---
**Created:** 2025-11-30
**Always follow these rules for every subtask!**

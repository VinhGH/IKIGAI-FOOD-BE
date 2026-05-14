# AGENTS.md

## Tips

Except for the AGENTS.md file, the md files mentioned below are located in the skills/ folder at the same level as AGENTS.md.

## Purpose

This repository uses documentation-first development.

AI agents must follow the project documents as the source of truth. Do not guess architecture, conventions, module behavior, or API contracts from existing code alone.

## Core Documents

### `ARCHITECTURE.md`

Immutable architecture rules.

AI agents MUST read this file before writing any code.

Do not violate this file without explicit human approval.

### `CONVENTIONS.md`

Code generation rules.

AI agents MUST follow this file when generating or modifying code.

This file defines naming, folder structure, DTO style, validation, error handling, testing style, and code organization.

### `MODULE_IAM.md`

IAM module specification.

AI agents MUST read this file before implementing or modifying IAM logic.

This file must be read after:

1. `ARCHITECTURE.md`
2. `CONVENTIONS.md`

### `API_CONTRACT_IAM.md`

Frontend-facing IAM API contract.

This is the single source of truth for IAM API integration.

Backend implementation must match this file exactly unless a task explicitly changes the API contract.

### `TASKS_IAM.md`

IAM task execution plan.

Each task is intended to be handled by one independent agent run.

Tasks are ordered by dependency.

Do not run task N+1 until task N has passed, unless explicitly approved by a human.

## Mandatory Reading Order for IAM Tasks

Before executing any IAM task, read the following files in order:

1. `ARCHITECTURE.md`
2. `CONVENTIONS.md`
3. `MODULE_IAM.md`
4. `TASKS_IAM.md`

If the task touches API routes, request bodies, response shapes, status codes, error formats, or frontend integration, also read:

5. `API_CONTRACT_IAM.md`

## Default IAM Workflow

1. Read the mandatory documents in the required order.
2. Open `TASKS_IAM.md`.
3. Identify the assigned task.
4. Check that all previous dependency tasks have passed.
5. Implement only the assigned task.
6. Do not implement future tasks.
7. Do not change public API contracts unless the task explicitly requires it.
8. Run or update relevant tests if the project has a testing pattern.
9. Report changed files, behavior implemented, tests run, and blockers.

## Token Discipline

Even though mandatory documents must be respected, do not load unrelated files or future task details unnecessarily.

For a single IAM task:

- Read the required project documents.
- Read only the assigned task and its dependency notes from `TASKS_IAM.md`.
- Do not scan unrelated modules unless required by imports, architecture rules, or task dependencies.
- Prefer precise file reads over broad repository scans.

## Implementation Rules

- Follow `ARCHITECTURE.md` as immutable law.
- Follow `CONVENTIONS.md` for all generated or modified code.
- Follow `MODULE_IAM.md` for IAM behavior and boundaries.
- Follow `API_CONTRACT_IAM.md` for public IAM API shape.
- Follow `TASKS_IAM.md` for task order and scope.
- Respect module boundaries.
- Prefer existing project patterns.
- Do not introduce speculative features.
- Do not silently change behavior outside the task scope.
- Do not duplicate shared logic if an existing shared utility or pattern exists.
- Keep each agent run small and reviewable.

## API Contract Rules

When working on IAM APIs:

- `API_CONTRACT_IAM.md` is the source of truth for FE integration.
- Routes, request bodies, response bodies, status codes, and error formats must match the contract.
- If implementation and contract conflict, report the conflict before changing code.
- Do not rename public fields, DTOs, routes, or response shapes unless the assigned task explicitly requires it.
- FE should be able to work from `API_CONTRACT_IAM.md` without reading backend code.

## Task Rules

When working from `TASKS_IAM.md`:

- Each task equals one independent agent run.
- Tasks must be executed in order unless human approval says otherwise.
- Do not start task N+1 if task N has not passed.
- Do not bundle multiple tasks into one run.
- Do not modify future task scope without instruction.
- If blocked, report the blocker clearly.
- If completed, update task status or notes if the repository workflow expects it.

## Shared Code Rules

When creating shared utilities, guards, decorators, pipes, exceptions, helpers, or base classes:

- Confirm the abstraction is truly shared.
- Place it according to `CONVENTIONS.md`.
- Do not leak IAM-specific business logic into generic shared modules.
- Do not place domain rules inside generic helpers.
- Do not create shared code just to satisfy one task unless the architecture requires it.

## Database / Migration Rules

When changing schema, entities, migrations, seeds, repositories, or persistence logic:

- Follow `ARCHITECTURE.md`.
- Follow `MODULE_IAM.md` for IAM persistence rules.
- Keep persistence concerns separate from domain/application logic.
- Do not create migrations unless the assigned task requires schema changes.
- Do not change existing schema behavior casually.

## Testing Rules

When implementing a task:

- Add or update tests when the project already has a testing pattern for that layer.
- Follow testing conventions from `CONVENTIONS.md`.
- Prefer behavior tests over implementation-detail tests.
- Do not skip tests silently for critical IAM behavior.
- If tests cannot be run, report why.

## Security Rules

IAM is security-sensitive.

Never weaken authentication, authorization, password handling, token handling, session handling, permission checks, or audit behavior for convenience.

Never log:

- passwords
- tokens
- refresh tokens
- OTPs
- secrets
- private credentials

Do not introduce temporary bypasses unless the task explicitly asks for a development-only mechanism.

Any development-only bypass must be clearly marked and isolated.

## Conflict Resolution

If documents conflict, priority is:

1. Explicit human instruction in the current conversation
2. `ARCHITECTURE.md`
3. `TASKS_IAM.md`
4. `API_CONTRACT_IAM.md`
5. `MODULE_IAM.md`
6. `CONVENTIONS.md`
7. Existing code patterns

If a conflict affects architecture, security, API shape, task dependency, or data model, stop and report the conflict before changing code.

## Final Response Format

After completing a task, respond with:

- Task completed
- Files changed
- Summary of behavior implemented
- Tests run
- Blockers or follow-up notes

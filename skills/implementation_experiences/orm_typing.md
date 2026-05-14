# ORM Typing Boundary

Use this note when Pylance disagrees with SQLModel / SQLAlchemy expressions.

## Problem pattern

- Runtime ORM code is valid.
- Pylance infers a plain Python type like `list[...]` or `Optional[...]`.
- Helpers such as `selectinload()` or `.where()` produce false-positive type errors.

## What to do

- Fix the narrowest expression that Pylance flags.
- Prefer a typed column or a local cast at the call site.
- Keep the runtime ORM behavior unchanged unless there is a real bug.

## Safe examples

- Cast ORM relationship accessors only at `selectinload()` call sites.
- Use a typed column expression for filters instead of relying on model class attributes.


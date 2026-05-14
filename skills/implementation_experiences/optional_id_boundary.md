# Optional ID Boundary

Use this note when domain objects with optional IDs are written into ORM models.

## Problem pattern

- Domain entities allow `id: Optional[int]` because new objects do not have a database identity yet.
- ORM constructors and foreign-key columns often require concrete `int` values.

## What to do

- Keep optional IDs in the domain layer.
- Convert `Optional[int]` to `int` only when writing to the database.
- If a value must exist for persistence, validate it with a small helper and fail fast.

## Do not

- Change the domain model to force IDs too early.
- Pass `Optional[int]` directly into ORM constructors or column assignments.


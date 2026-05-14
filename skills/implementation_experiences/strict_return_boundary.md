# Strict Return Boundary

Use this note when a repository or service promises a strict return type but the fetch path is optional.

## Problem pattern

- A fetch helper returns `Optional[T]`.
- The public method promises `T`.
- Pylance warns when the optional result is returned directly.

## What to do

- Add a small internal helper like `_require_by_id()`.
- Convert the optional result to the strict return type at the boundary.
- Raise a clear runtime error if the expected row is missing after a successful write.


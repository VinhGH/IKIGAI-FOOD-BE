# IMPLEMENTATION_EXPERIENCES.md

> Index of reusable implementation notes.
> Pick the smallest file that matches the task you are implementing.

---

## Repository Tasks

Read these when implementing repositories, ORM mappings, or DB-boundary code:

- [skills/implementation_experiences/orm_typing.md](C:/Users/edward/Desktop/IKIGAI-FOOD-BE/skills/implementation_experiences/orm_typing.md)
- [skills/implementation_experiences/optional_id_boundary.md](C:/Users/edward/Desktop/IKIGAI-FOOD-BE/skills/implementation_experiences/optional_id_boundary.md)
- [skills/implementation_experiences/strict_return_boundary.md](C:/Users/edward/Desktop/IKIGAI-FOOD-BE/skills/implementation_experiences/strict_return_boundary.md)

---

## Selection Rule

- If the task touches SQLModel attributes, loader options, or SQLAlchemy filters, read `orm_typing.md`.
- If the task writes domain objects into ORM models, read `optional_id_boundary.md`.
- If the task returns a strict type from an optional fetch path, read `strict_return_boundary.md`.


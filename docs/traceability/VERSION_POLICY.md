# Version Policy

## SemVer

This project follows Semantic Versioning:

1. MAJOR: breaking changes in public contracts (sample schema, adapter interfaces)
2. MINOR: backward-compatible features
3. PATCH: backward-compatible fixes

Current version: `0.1.0`

## Iteration Discipline

Each implementation step must include:

1. Requirement mapping update in `REQUIREMENTS.md`
2. Design note update in `DESIGN_NOTES.md` if assumptions change
3. Iteration log update in `docs/iterations/`
4. Changelog entry in `CHANGELOG.md`

## GitHub Safety

1. Never commit `configs/keys.local.json`
2. Use `configs/keys.local.example.json` for shared config template

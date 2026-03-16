# Iteration 0001 - Bootstrap + LOCOMO Sample Demo

## Goal

Create a new project from scratch and validate LOCOMO sample construction feasibility with a minimal demo.

## Scope Included

1. New folder and project skeleton
2. Versioning and traceability documents
3. LOCOMO sample builder demo

## Scope Excluded

1. Full evaluation probe implementations
2. Full attribution engine
3. Real memory-system adapters

## Validation Checklist

- [x] Project created in new path
- [x] Version files added (`VERSION`, `CHANGELOG.md`)
- [x] Requirements and design recorded
- [x] Demo script can parse LOCOMO and produce structured samples

## Validation Notes

1. Syntax check passed:
   - `python -m compileall src scripts`
2. Demo run passed:
   - `python scripts/demo_build_locomo_samples.py --limit 5`
3. NEG construction rule spot-check passed:
   - first NEG sample has `f_key=[]` and `oracle_context=NO_RELEVANT_MEMORY`

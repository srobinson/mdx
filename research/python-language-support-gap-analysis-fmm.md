---
title: Python Language Support Gap Analysis
type: research
tags: [fmm, python, parser, gap-analysis, language-support]
summary: Detailed comparison of Python vs TypeScript parsing support in fmm, identifying 11 concrete gaps across export extraction, import precision, and language-specific features
status: active
source: codebase-analyst
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Executive Summary

fmm's Python parser covers the fundamentals well: top-level functions, classes, `__all__`-based export control, relative/absolute imports, decorators, and public class method extraction. It falls short of TypeScript parity in three categories: (1) import precision features that power `fmm_glossary` Layer 2/3, (2) nested symbol extraction for function bodies, and (3) `parse_file` context awareness. Several Python-specific language features also have no support. The parser is 898 LOC against TypeScript's 2,011 LOC, reflecting roughly 55% feature coverage.

## Project Metadata

- **Parser file**: `src/parser/builtin/python.rs` (898 LOC)
- **Comparison file**: `src/parser/builtin/typescript.rs` (2,011 LOC)
- **Python fixtures**: 3 files, 115 LOC (`fixtures/python/`)
- **TypeScript fixtures**: 3 files, 68 LOC (`fixtures/typescript/`)
- **Private member support**: `src/manifest/private_members.rs` lines 234-266 (top-level), 437-518 (class members)
- **Call-site finder**: `src/manifest/call_site_finder.rs` lines 94-111

## Current Python Capabilities

### What works today

| Feature | Status | Source Location |
|---------|--------|----------------|
| Top-level function extraction | Complete | `python.rs:48-53` (func_query) |
| Top-level class extraction | Complete | `python.rs:54-59` (class_query) |
| Decorated functions and classes | Complete | Both `func_query` and `class_query` handle `decorated_definition` wrappers |
| `__all__` export control (Path A) | Complete | `python.rs:192-242` (extract_dunder_all) |
| Heuristic export discovery (Path B) | Complete | `python.rs:121-158` (extract_exports), filters `_prefix` as private, includes UPPER_CASE and CamelCase assignments |
| `__all__` definition-site resolution | Complete | `python.rs:216` builds definition map, resolves each `__all__` name to its actual source line |
| Module-level constant extraction | Partial | `python.rs:60-63` (assign_query), only includes UPPER_CASE or CamelCase assignments |
| `import X` and `import X as Y` | Complete | `python.rs:70-81` (import_queries), stores original module name |
| `from X import Y` | Complete | `python.rs:82-86` (from_import_query), stores full dotted path |
| Relative imports as dependencies | Complete | `python.rs:87-91`, `python.rs:284-289`, converts dot-notation to path notation |
| Decorator collection | Complete | `python.rs:408-418`, captures both simple (`@foo`) and dotted (`@foo.bar`) decorators into custom_fields |
| Public class method extraction | Complete | `python.rs:297-383` (extract_class_methods), includes `__init__`, excludes other dunders and `_private` |
| Decorated method line ranges | Complete | `python.rs:356-374`, decorator lines included in range |
| Private member extraction (on-demand) | Partial | `private_members.rs:437-518`, extracts `_private` methods but not `_private` properties/attributes |
| Non-exported top-level functions (on-demand) | Partial | `private_members.rs:234-266`, plain `function_definition` only |
| Call-site verification | Basic | `call_site_finder.rs:94-111`, checks `something.METHOD_NAME(...)` pattern |

### Test coverage

- **Unit tests**: 22 tests in `python.rs:483-898`
- **Fixture validation**: 4 tests in `fixture_validation.rs` (lines 21, 72, 116, 142)
- **Edge cases**: 12 Python-specific tests in `edge_cases.rs` (empty file, huge file, syntax errors, private-only, unicode, CRLF, whitespace-only, comments-only, decorated variants)
- **Cross-language validation**: 6 tests with real-world code snippets in `cross_language_validation.rs` (httpx patterns, FastAPI patterns, pandas-style imports)

## TypeScript Parity Gaps

### Gap 1: Named Import Tracking (High Impact)

**TypeScript**: Populates `Metadata.named_imports` (map of source path to list of imported symbol names) and `Metadata.namespace_imports`. This powers Layer 2 glossary precision, where `fmm_glossary` can report exactly which files import a symbol by name.

**Python**: Uses `..Default::default()` on Metadata (line 468), leaving `named_imports` and `namespace_imports` empty. All Python glossary lookups fall back to coarse file-level dependency matching.

**What this breaks**: `fmm_glossary` with `precision: "named"` returns zero results for Python symbols. The `used_by` list for Python exports relies entirely on dependency file matching, producing false positives (any file importing the module appears, even if it imports different symbols).

**Python equivalent**: `from module import Symbol` maps directly to `named_imports["module"] = ["Symbol"]`. `import module` maps to namespace imports.

**Files affected**: `python.rs:462-471`, `src/manifest/glossary_builder.rs`

### Gap 2: Re-export Source Tracking (Medium Impact)

**TypeScript**: Has `reexport_source_query` and `reexport_named_query` that capture `export { X } from './y'` patterns, enabling barrel file resolution.

**Python**: Python's `__init__.py` barrel pattern (`from .module import Symbol`) is already captured as a relative dependency, but the re-exported symbol names are not tracked. fmm cannot determine which names flow through an `__init__.py` without parsing it.

**Files affected**: `python.rs` (no equivalent queries)

### Gap 3: Nested Function/Closure State Extraction (Low Impact)

**TypeScript**: `extract_nested_symbols` (lines 643-747) finds depth-1 nested function declarations and prologue variables inside top-level function bodies. These appear with `kind: "nested-fn"` or `kind: "closure-state"` in exports.

**Python**: No equivalent. Nested functions (`def inner():` inside `def outer():`) and closure variables are invisible.

**Python relevance**: Lower than TypeScript. Python closures and nested functions exist but are less common than TS's factory/closure patterns. However, Python decorators that return inner functions (Flask route handlers, pytest fixtures) would benefit from this.

### Gap 4: function_names Custom Field (Low Impact)

**TypeScript**: Stores `function_names` in `custom_fields` for confirmed function declarations (vs arrow functions assigned to const). This is used by the manifest to build `function_index` for call-site precision in `fmm_glossary`.

**Python**: Not implemented. All Python functions are `function_definition` nodes, so the distinction is less meaningful, but the field is still needed for `function_index` parity.

**Files affected**: `python.rs:446-460` (only populates `decorators`, not `function_names`)

### Gap 5: parse_file Context Awareness (Medium Impact)

**TypeScript**: Overrides `parse_file()` to load `tsconfig.json` path aliases and use them to classify aliased imports as local dependencies. Includes a per-directory cache.

**Python**: No `parse_file()` override. Python has analogous path configuration in `pyproject.toml` (`[tool.mypy]`/`[tool.ruff]` namespace packages), `setup.cfg`, and `sys.path` modifications. The most impactful equivalent would be resolving `pyproject.toml` `[project]` metadata to identify package boundaries.

## Python-Specific Gaps

### Gap 6: Type Hint Extraction (Medium Impact)

Python's type annotation system is rich and structurally significant:

```python
def process(data: list[str]) -> dict[str, int]: ...
age: int = 25
items: Final[list[str]] = []
```

fmm extracts no type information from Python files. For dataclasses and typed module-level assignments, the type annotation is often more informative than the name. TypeScript captures type information implicitly through its export queries (interface, type alias, enum declarations are all typed constructs).

### Gap 7: Dataclass/Attrs/Pydantic Field Extraction (Medium Impact)

```python
@dataclass
class Config:
    host: str = "localhost"
    port: int = 8080
    debug: bool = False
```

fmm correctly exports `Config` as a class and captures the `@dataclass` decorator. It does not extract the field names (`host`, `port`, `debug`) as structural information. For dataclasses, the fields are the API surface. The TS equivalent would be extracting public class properties.

### Gap 8: Protocol/ABC Class Detection (Low Impact)

```python
class Repository(Protocol):
    def get(self, id: str) -> Item: ...
    def save(self, item: Item) -> None: ...
```

Python Protocols (PEP 544) and ABCs define interfaces. fmm has no way to distinguish a Protocol class from a regular class. TypeScript interfaces are explicitly captured as a separate export type.

### Gap 9: `__slots__` Extraction (Low Impact)

```python
class Optimized:
    __slots__ = ('x', 'y', 'z')
```

`__slots__` defines the complete attribute surface of a class. Not extracted.

### Gap 10: Async Function Detection (Low Impact)

```python
async def fetch_data(url: str) -> bytes: ...
```

fmm does not distinguish `async def` from `def`. The tree-sitter grammar uses the same `function_definition` node for both, but async status is available via a child node. TypeScript similarly does not explicitly tag async, so this is parity-neutral.

### Gap 11: Non-Exported Top-Level Function Discovery Misses Decorated Functions

`extract_py_top_level` in `private_members.rs:234-266` only matches `function_definition` directly under the module root. A decorated non-exported function wraps the `function_definition` in a `decorated_definition` node, which this code does not handle. This means `fmm_file_outline(include_private: true)` silently drops decorated private functions.

**Contrast with the main parser**: The main `python.rs` parser correctly handles `decorated_definition` wrappers in its func_query (line 51). The on-demand extraction path is inconsistent.

### Gap 12: Private Class Property Extraction

`collect_py_private_members` in `private_members.rs:478-505` only extracts private methods (`function_definition`). Python class bodies also contain:
- Assignment statements (`self._cache = {}` in `__init__`)
- Annotated assignments (`_internal: int = 0` at class level)

TypeScript's equivalent (`collect_ts_private_members`) handles both `method_definition` and `public_field_definition` nodes. Python private properties are structurally important for understanding class state.

## Priority Recommendations

### P0: Named Import Tracking

**Effort**: Medium (estimated 150-200 LOC)
**Impact**: Unlocks Layer 2 glossary precision for Python codebases. Without this, `fmm_glossary` and `fmm_lookup_export` produce noisy results for Python.

Implementation: Extract `from X import A, B` into `named_imports["X"] = ["A", "B"]` and `import X` into `namespace_imports`. The tree-sitter queries already capture the module names. The missing piece is capturing the imported symbol names from `import_from_statement` children.

### P1: Decorated Function Handling in `extract_py_top_level`

**Effort**: Small (10-20 LOC)
**Impact**: Fixes `fmm_file_outline(include_private: true)` silently dropping decorated private functions. Simple consistency fix.

### P2: function_names Custom Field

**Effort**: Small (20-30 LOC)
**Impact**: Enables `function_index` for Python, improving call-site precision in glossary queries.

### P3: Re-export Name Tracking for `__init__.py`

**Effort**: Medium (100-150 LOC)
**Impact**: Enables barrel file resolution for Python packages. `from .module import X` in `__init__.py` should register X as a re-exported name.

### P4: Dataclass/Typed Class Field Extraction

**Effort**: Medium (100-150 LOC)
**Impact**: Surfaces the API of dataclasses, Pydantic models, and attrs classes. Particularly valuable for ML/data codebases where dataclasses are the primary abstraction.

### P5: Private Class Property Extraction

**Effort**: Small (30-50 LOC)
**Impact**: Completes the `include_private` story for Python classes by adding annotated and assigned attributes alongside methods.

### P6: Type Hint Extraction

**Effort**: Large (200+ LOC)
**Impact**: Would enable type-aware search and richer outlines. Lower priority because fmm's core value is structural navigation, not type analysis.

## Quantitative Summary

| Metric | Python | TypeScript | Gap |
|--------|--------|------------|-----|
| Parser LOC | 898 | 2,011 | 55% smaller |
| Tree-sitter queries | 10 | 12+ | Missing named-import, reexport-named, namespace-import queries |
| Metadata fields populated | 4/6 | 6/6 | Missing `named_imports`, `namespace_imports` |
| Custom fields | 1 (`decorators`) | 2 (`decorators`, `function_names`) | Missing `function_names` |
| `parse_file` override | No | Yes (tsconfig alias resolution) | No path-alias equivalent |
| ExportEntry.kind values | None used | `nested-fn`, `closure-state` | No nested symbol extraction |
| Fixture files | 3 (115 LOC) | 3 (68 LOC) | Python actually has more fixture coverage |
| Unit tests | 22 | ~40+ | Roughly proportional to feature count |
| Edge case tests | 12 | Similar | Good coverage for what exists |
| Cross-language validation | 6 | 6+ | Adequate |

## Key Source Files

| File | Relevance |
|------|-----------|
| `src/parser/builtin/python.rs` | Main Python parser, all export/import/decorator logic |
| `src/parser/builtin/typescript.rs` | TypeScript parser, comparison baseline |
| `src/parser/mod.rs` | `ExportEntry`, `Metadata`, `Parser` trait definitions |
| `src/manifest/private_members.rs:234-518` | On-demand Python private member and non-exported function extraction |
| `src/manifest/call_site_finder.rs:94-111` | Python call-site verification for Layer 3 glossary |
| `src/manifest/glossary_builder.rs` | Glossary builder consuming named_imports (Python has none) |
| `src/manifest/dependency_matcher.rs:129-142` | Python relative import resolution |
| `fixtures/python/` | Three test fixtures covering decorated, heuristic, and `__all__` paths |
| `tests/cross_language_validation.rs:34-420` | Real-world Python code validation tests |
| `tests/edge_cases.rs:33-340` | Python edge case coverage |

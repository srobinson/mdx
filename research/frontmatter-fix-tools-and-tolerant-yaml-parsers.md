---
title: 'Frontmatter fix tools and tolerant YAML parsers: what to plug in vs write'
type: research
tags: [yaml, frontmatter, markdown-matters, mdm-fix, tooling]
summary: 'Survey of CLIs, linters, and parsers that auto-fix or tolerantly parse malformed YAML frontmatter; nothing solves the unquoted-colon class end to end, but eemeli/yaml CST plus a thin heuristic layer is the right plug-in foundation.'
status: active
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

No off-the-shelf tool repairs the unquoted-colon-space (`key: Use when: foo`) frontmatter footgun. Everything either ignores frontmatter (markdownlint), formats only valid YAML (prettier), or validates against a schema after parse succeeds (remark-lint-frontmatter-schema). The right foundation is eemeli/yaml's CST + Document API, which exposes parse errors with offsets, refuses to throw, and supports surgical scalar-quote patches. Build the heuristic layer yourself, but on top of that CST.

## Detailed Findings

### CLIs and linters: none fix the bug class you have

- **markdownlint / markdownlint-cli2 (DavidAnson)**: explicitly ignores YAML/TOML/JSON frontmatter. The `frontMatter` parameter is a regex used only to skip it. 32 of 60 rules support `--fix`, but zero touch frontmatter content.
- **prettier**: formats YAML inside markdown frontmatter only when it parses cleanly. On invalid YAML, prettier errors out -- it is a formatter, not a repairer.
- **remark-frontmatter**: parses the fenced block as a node but does not parse the YAML payload. No fix capability.
- **remark-lint-frontmatter-schema (JulianCataldo)**: validates against a JSON schema with auto-fix suggestions, but only after YAML parse succeeds. Useless for the malformed-input case.
- **obsidian-linter (platers)**: has YAML rules including escape and quote-style enforcement, but the README admits it parses YAML keys via regex, not a real parser, and breaks on edge cases (issue #1245 corrupts timestamps). Cannot recommend as a library.
- **frontmatter-validator (vinicioslc)**: fills missing fields from defaults. Does not repair syntax.
- **rythoris/frontmatter** (Go): extracts only.
- **tidy-markdown (notslang)**: formats valid YAML frontmatter; no repair.
- **Hugo / Jekyll / Docusaurus**: no fix mode. They fail loudly.

There is no "frontmatter doctor" CLI in npm, cargo, or pip. The closest is jsontotable.org's web "YAML Fixer," which is a black-box web tool, not a library.

### Tolerant parsers: eemeli/yaml is the answer

- **eemeli/yaml** (`yaml` on npm): the parser is documented as never throwing -- errors land in `doc.errors` as `{ offset, message }` tokens. CST layer exposes raw tokens with source ranges. Document API has `Scalar` nodes with `type: 'PLAIN' | 'QUOTE_SINGLE' | 'QUOTE_DOUBLE' | 'BLOCK_LITERAL' | 'BLOCK_FOLDED'` -- you can flip a node to `QUOTE_SINGLE` and re-stringify, preserving everything else.
- **js-yaml (nodeca)**: strict by design. Throws on first error. No recovery API. The failsafe schema is a type-coercion knob, not error tolerance.
- **gray-matter**: thin wrapper over js-yaml by default; inherits its strictness. You can pass a custom parser (e.g., eemeli's `yaml`), which is the standard escape hatch.
- **enhanced-yaml** and **YAWN YAML**: AST round-trip libraries that sit on top of eemeli/yaml. Useful precedent but eemeli/yaml core already covers the use case.

### The unquoted-colon-space class

This is the canonical YAML frontmatter footgun -- referenced in dozens of GitHub issues across Hugo, assemble, Astro, and Claude skill loaders. No library auto-quotes; the universal advice is "wrap in quotes." For a programmatic fix you need:

1. Detect the line: regex per line `^(\s*)([A-Za-z_][\w-]*)(\s*:\s+)(.*)$` where the value contains `: ` or starts with `"…"` or unbalanced quotes.
2. Emit a single-quoted scalar (single quotes only need `'` doubled; safer than double).
3. Re-parse to verify.

The eemeli CST gives you exact byte offsets from `doc.errors`, so you can target the bad node rather than re-tokenize from scratch.

### AST-level surgical edits

- **eemeli/yaml Document API**: `doc.get(key, true)` returns the `Scalar` node; mutate `.value` and `.type = 'QUOTE_SINGLE'`, then `String(doc)`. Comments and unrelated formatting survive. Caveat: issue #349 notes block-scalar indentation can shift on `setScalarValue`; flat scalars in frontmatter are unaffected.
- **ruamel.yaml** (Python): `preserve_quotes=True` plus `SingleQuotedScalarString` is the gold-standard reference implementation. Transferable design, not directly usable from TS.

## Sources Consulted

GitHub:
- [DavidAnson/markdownlint](https://github.com/DavidAnson/markdownlint)
- [DavidAnson/markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2)
- [eemeli/yaml](https://github.com/eemeli/yaml), parsing docs, issue #349, discussion #510
- [remarkjs/remark-frontmatter](https://github.com/remarkjs/remark-frontmatter), issue #4
- [JulianCataldo/remark-lint-frontmatter-schema](https://github.com/JulianCataldo/remark-lint-frontmatter-schema)
- [platers/obsidian-linter](https://github.com/platers/obsidian-linter), rules.md, issue #1245
- [jonschlinkert/gray-matter](https://github.com/jonschlinkert/gray-matter)
- [vinicioslc/frontmatter-validator](https://github.com/vinicioslc/frontmatter-validator)
- [notslang/tidy-markdown](https://github.com/notslang/tidy-markdown)
- [liorbentov/preserve-yaml-comments](https://github.com/liorbentov/preserve-yaml-comments)
- [prettier/prettier issues #4725, #9788, #15187](https://github.com/prettier/prettier/issues/4725)

Articles and references:
- [eemeli.org/yaml](https://eemeli.org/yaml/) -- canonical Document and CST docs
- [Prettier 1.14 YAML support announcement](https://prettier.io/blog/2018/07/29/1.14.0.html)
- [inspirnathan: escaping characters in YAML frontmatter](https://inspirnathan.com/posts/134-escape-characters-in-yaml-frontmatter/)
- [icicity.com: YAML frontmatter quoting best practices](https://icicity.com/articles/code/markdown/yaml-frontmatter-quoting-guidelines)
- [azimi.me YAWN YAML write-up](https://azimi.me/2015/10/16/yawn-yaml.html)
- [enhanced-yaml docs](https://enhanced-yaml.netlify.app/)
- [likegeeks: ruamel.yaml quote management](https://likegeeks.com/quotes-yaml-python/)

## Source Quality Assessment

High confidence on the parser landscape -- eemeli/yaml's docs and source are authoritative and the library is actively maintained (the de facto modern JS YAML parser). Medium confidence on the negative claims about CLI fixers; the npm long tail is unverifiable, but a focused search of the obvious candidates (Hugo, Jekyll, Docusaurus, Obsidian, remark, markdownlint, prettier) found nothing. Reddit and HN had near-zero relevant signal -- this is a niche developer-tooling space without community discussion.

## Open Questions

- Does eemeli/yaml's CST give a stable enough offset on errors to safely splice quotes mid-document, or do downstream offsets shift? Worth a 30-line spike before committing to the design.
- Is there value in detecting the bug class at write time (mdm CLI inserting frontmatter) rather than at fix time, given how cheap correct quoting is at the source?

## Actionable Takeaways

- Plug in `yaml` (eemeli) as the parser. Replace any `js-yaml` / default `gray-matter` path in markdown-matters.
- Keep `gray-matter` only as the fenced-block extractor; pass `engines: { yaml: { parse: yamlParse } }` so the existing API stays.
- Write `mdm fix` as a thin layer:
  1. Run gray-matter to isolate the YAML payload.
  2. Run eemeli's `parseDocument(yaml, { logLevel: 'silent' })`.
  3. If `doc.errors.length`, walk errors by offset, apply targeted single-quote heuristic on the offending line, retry parse (max 3 passes).
  4. Bail with a clear error if still broken; never silently rewrite ambiguous content.
- Skip remark-lint-frontmatter-schema for now -- it solves a different problem (schema validation post-parse).
- Reference ruamel.yaml's `SingleQuotedScalarString` API as the design target for the eventual scalar-mutation helper.

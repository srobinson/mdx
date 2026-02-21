---
title: Rust - Stripping Markdown to Plain Text
type: research
tags: [rust, markdown, plaintext, pulldown-cmark, text-processing]
summary: Two abandoned crates exist (strip_markdown, markdown_to_text), both ~5 years stale and pinned to pulldown-cmark 0.7. Rolling a small custom implementation against current pulldown-cmark is the correct path.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Two published crates address this need - `strip_markdown` (v0.2.0) and `markdown_to_text` (v1.0.0) - but both were last updated in 2020 and pin `pulldown-cmark ^0.7`. Current pulldown-cmark is 0.13.1. Neither crate is maintained. The `Tag` enum signature has changed across those major versions (e.g., `Tag::Heading(_)` now carries more fields, `End` takes a `TagEnd` not a `Tag`), so these crates will not compile against a modern dependency tree without patching.

**Verdict: roll a small custom function using pulldown-cmark directly.** The implementation is ~50 lines and fully covers every requirement.

## Details

### Existing Crates

| Crate | Version | Downloads | Last Updated | pulldown-cmark pin |
|---|---|---|---|---|
| `strip_markdown` | 0.2.0 | ~56k | 2020-03-22 | ^0.7 |
| `markdown_to_text` | 1.0.0 | ~14k | 2020-08-02 | ^0.7 |

Both wrap pulldown-cmark's event stream - there is no proprietary logic. The entire value is the ~50-80 line match over events.

### What the existing crates cover (and gaps)

**`strip_markdown` (arranf/strip-markdown):**
- Headers: yes (emits newline on end, content flows through `Text`)
- Bold/italic: yes (Start/End ignored, Text passes through)
- Inline code: yes (`Event::Code` pushes content)
- Lists: yes (fresh_line on Start/End)
- Links: partially - emits the link `title` attribute, NOT the link text. `[text](url)` yields `text` only if `title` is non-empty - otherwise silent. This is a bug.
- Tables: enabled only if `Options::ENABLE_TABLES` is set - the crate does NOT set this flag, so tables fall through unparsed (raw `|` characters remain).

**`markdown_to_text` (fbecart/markdown_to_text):**
- Headers: yes
- Bold/italic: yes (strikethrough is suppressed entirely)
- Inline code: yes
- Lists: yes, with bullet prefix (`•`) and tab-indented nesting
- Links: yes - link text flows through `Event::Text`, title pushed on Start
- Tables: NOT enabled (same as above - no `ENABLE_TABLES` flag)

### The correct pulldown-cmark approach (0.12+)

The `Event` enum variants that matter:

```
Event::Start(Tag)     - opening of a block/inline element
Event::End(TagEnd)    - closing (note: TagEnd, not Tag, in 0.12+)
Event::Text(CowStr)   - raw text content
Event::Code(CowStr)   - inline code content (backtick spans)
Event::SoftBreak
Event::HardBreak
```

`Tag` variants covering all requirements:
- `Tag::Heading { .. }` - headers (`#`, `##`, etc.)
- `Tag::Strong` - bold (`**`)
- `Tag::Emphasis` - italic (`*`, `_`)
- `Tag::Link { .. }` - `[text](url)` - text arrives as `Event::Text` children
- `Tag::List(_)` - ordered/unordered list wrapper
- `Tag::Item` - list item
- `Tag::Table(_)` - requires `Options::ENABLE_TABLES`
- `Tag::TableRow`, `Tag::TableCell` - row and cell boundaries

Inline code arrives as `Event::Code(content)` - it is NOT wrapped in Start/End.

### Minimal custom implementation sketch

```rust
use pulldown_cmark::{Event, Options, Parser, Tag, TagEnd};

pub fn strip_markdown(md: &str) -> String {
    let mut opts = Options::empty();
    opts.insert(Options::ENABLE_TABLES);
    opts.insert(Options::ENABLE_STRIKETHROUGH);

    let mut out = String::with_capacity(md.len());
    let mut last_was_newline = false;

    for event in Parser::new_ext(md, opts) {
        match event {
            Event::Text(t) | Event::Code(t) => {
                out.push_str(&t);
                last_was_newline = false;
            }
            Event::SoftBreak | Event::HardBreak => {
                if !last_was_newline { out.push('\n'); last_was_newline = true; }
            }
            Event::Start(Tag::TableCell) => {
                if !out.is_empty() && !last_was_newline { out.push(' '); }
            }
            Event::End(TagEnd::TableRow) | Event::End(TagEnd::Heading(_)) => {
                out.push('\n'); last_was_newline = true;
            }
            Event::End(TagEnd::Paragraph) | Event::End(TagEnd::Item) => {
                out.push('\n'); last_was_newline = true;
            }
            _ => {}
        }
    }
    out.trim().to_string()
}
```

Key decisions:
- `ENABLE_TABLES` must be explicitly set or table syntax falls through as raw text.
- In pulldown-cmark 0.12+, `Event::End` carries `TagEnd`, not `Tag` - old crates break here.
- Table cells: separator lines (`---`) are never emitted as events; pulldown-cmark parses them structurally. Only `TableCell` text events arrive, so no special handling needed for `---`.
- Link text: arrives as `Event::Text` children between `Start(Tag::Link)` and `End(TagEnd::Link)` - no special handling needed; the URL is on the `Tag::Link` and is simply ignored.

### Dependencies

Single dependency: `pulldown-cmark` (latest 0.13.1). No regex needed. ~50 lines of code.

If regex is preferred over a parser (truly minimal, zero deps), the tradeoff is:
- Tables become harder: must handle multi-line, alignment rows, pipe escaping
- Nested constructs (bold inside a link label) require careful ordering
- pulldown-cmark handles all CommonMark edge cases correctly; regex does not

For production use, pulldown-cmark is the right call.

## Sources

- `strip_markdown` source: https://github.com/arranf/strip-markdown/blob/master/src/lib.rs
- `markdown_to_text` source: https://github.com/fbecart/markdown_to_text/blob/master/src/lib.rs
- pulldown-cmark Event enum: https://docs.rs/pulldown-cmark/0.12.2/pulldown_cmark/enum.Event.html
- pulldown-cmark Tag enum: https://docs.rs/pulldown-cmark/0.12.2/pulldown_cmark/enum.Tag.html
- crates.io API for metadata

## Open Questions

- Whether `TagEnd` variants in 0.13.x differ from 0.12.x (minor version bumps have been API-stable in the 0.12+ series so far).
- Whether attention-matters needs table cell spacing/separation beyond a single space, or newline-per-row.

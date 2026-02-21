---
title: "fmm Multi-Language Architecture Spec"
status: draft
created: 2026-03-16
---

## 1. LanguageDescriptor Trait

### Problem

fmm has 8 dispatch sites across 6 files where language-specific metadata is hardcoded. Five of these sites fail silently when a new language is added without updating them. The root cause: language metadata (extensions, re-export filenames, test file patterns) is scattered as flat data across the codebase rather than co-located with the parser that defines the language.

### Trait Definition

```rust
// src/parser/mod.rs

/// Static metadata about a language that enables downstream subsystems
/// (config, dependency resolution, glossary, call-site analysis) to handle
/// the language without hardcoded match arms.
///
/// Every Parser implementation must also provide a LanguageDescriptor.
/// The descriptor is registered alongside the parser factory in ParserRegistry
/// and queried at runtime by subsystems that currently use hardcoded extension lists.
pub trait LanguageDescriptor {
    /// Canonical language identifier (e.g. "rust", "python", "typescript").
    /// Must match the value returned by Parser::language_id().
    fn language_id(&self) -> &'static str;

    /// All file extensions this language handles, without the leading dot.
    /// e.g. &["ts", "js"] for TypeScript.
    fn extensions(&self) -> &'static [&'static str];

    /// Filenames that serve as re-export hubs for this language.
    /// e.g. &["__init__.py"] for Python, &["mod.rs"] for Rust.
    /// Empty slice if the language has no re-export hub convention.
    fn reexport_filenames(&self) -> &'static [&'static str] {
        &[]
    }

    /// Test file detection patterns specific to this language.
    /// These supplement the configurable test_patterns in .fmmrc.toml.
    /// Returns (filename_suffixes, filename_prefixes).
    /// e.g. Python returns (&["_test.py"], &["test_"]).
    fn test_file_patterns(&self) -> LanguageTestPatterns {
        LanguageTestPatterns::default()
    }
}

/// Language-specific test file naming conventions.
#[derive(Default)]
pub struct LanguageTestPatterns {
    /// Filename suffixes that indicate a test file (e.g. "_test.go").
    pub filename_suffixes: &'static [&'static str],
    /// Filename prefixes that indicate a test file (e.g. "test_").
    pub filename_prefixes: &'static [&'static str],
    /// Symbol name prefixes that indicate a test export (e.g. "test_", "Test").
    pub test_symbol_prefixes: &'static [&'static str],
}
```

### Concrete Implementations

Each language parser provides its descriptor via a const function or associated impl. Three examples:

```rust
// src/parser/builtin/python.rs
impl LanguageDescriptor for PythonParser {
    fn language_id(&self) -> &'static str { "python" }
    fn extensions(&self) -> &'static [&'static str] { &["py"] }
    fn reexport_filenames(&self) -> &'static [&'static str] { &["__init__.py"] }
    fn test_file_patterns(&self) -> LanguageTestPatterns {
        LanguageTestPatterns {
            filename_suffixes: &["_test.py"],
            filename_prefixes: &["test_"],
            test_symbol_prefixes: &["test_"],
        }
    }
}

// src/parser/builtin/rust.rs
impl LanguageDescriptor for RustParser {
    fn language_id(&self) -> &'static str { "rust" }
    fn extensions(&self) -> &'static [&'static str] { &["rs"] }
    fn reexport_filenames(&self) -> &'static [&'static str] { &["mod.rs"] }
    fn test_file_patterns(&self) -> LanguageTestPatterns {
        LanguageTestPatterns {
            filename_suffixes: &["_test.rs"],
            filename_prefixes: &[],
            test_symbol_prefixes: &[],
        }
    }
}

// src/parser/builtin/go.rs
impl LanguageDescriptor for GoParser {
    fn language_id(&self) -> &'static str { "go" }
    fn extensions(&self) -> &'static [&'static str] { &["go"] }
    fn test_file_patterns(&self) -> LanguageTestPatterns {
        LanguageTestPatterns {
            filename_suffixes: &["_test.go"],
            filename_prefixes: &[],
            test_symbol_prefixes: &["Test"],
        }
    }
}
```

### ParserRegistry Integration

`ParserRegistry` (src/parser/mod.rs:150-153) gains a new field to store descriptors, and the registration API changes to capture descriptor data at registration time:

```rust
// src/parser/mod.rs

pub struct ParserRegistry {
    factories: HashMap<String, ParserFactory>,
    language_ids: HashMap<String, &'static str>,
    // NEW: descriptor data collected at registration time
    descriptors: Vec<RegisteredLanguage>,
    // NEW: derived lookup tables built after registration
    reexport_filenames: HashSet<String>,
    source_extensions: HashSet<String>,
}

/// Frozen snapshot of a LanguageDescriptor, stored as owned data.
/// We do not store trait objects because descriptors are static data,
/// and trait objects would require the parser struct to be constructed
/// just to access metadata.
pub struct RegisteredLanguage {
    pub language_id: &'static str,
    pub extensions: &'static [&'static str],
    pub reexport_filenames: &'static [&'static str],
    pub test_patterns: LanguageTestPatterns,
}
```

The `register_builtin()` method (src/parser/mod.rs:186-237) changes: the `register_language!` macro expands to call a new `register_with_descriptor` method that captures both the factory and the descriptor:

```rust
impl ParserRegistry {
    pub fn register_with_descriptor<P, F>(
        &mut self,
        factory: F,
    ) where
        P: Parser + LanguageDescriptor + 'static,
        F: Fn() -> Result<Box<dyn Parser>> + Send + Sync + 'static,
    {
        // Construct a temporary instance to read descriptor data.
        // This is acceptable because parser construction is cheap
        // (query compilation is the expensive part, and it happens here anyway).
        let probe = factory().expect("parser construction must succeed during registration");

        // We need LanguageDescriptor methods. Downcast is not available because
        // we erased the type. Instead, require the caller to pass descriptor separately.
        // See revised approach below.
    }
}
```

Because `Box<dyn Parser>` erases the `LanguageDescriptor` impl, the cleanest approach avoids trait objects for descriptor access entirely. Instead, the macro extracts descriptor data from a temporary instance at registration time:

```rust
macro_rules! register_language {
    ($registry:expr, $mod:ident, $parser:ident) => {{
        // Construct a temporary to read static descriptor data.
        let probe = builtin::$mod::$parser::new()
            .expect(concat!("Failed to construct ", stringify!($parser)));
        let desc = RegisteredLanguage {
            language_id: probe.language_id(),
            extensions: probe.extensions(),
            reexport_filenames: probe.reexport_filenames(),
            test_patterns: probe.test_file_patterns(),
        };
        let exts = desc.extensions;
        let lang_id = desc.language_id;
        $registry.register(exts, || {
            Ok(Box::new(builtin::$mod::$parser::new()?))
        });
        $registry.register_language_id(exts, lang_id);
        $registry.descriptors.push(desc);
    }};
}
```

After `register_builtin()` completes, `ParserRegistry` builds its derived lookup tables:

```rust
impl ParserRegistry {
    pub fn with_builtins() -> Result<Self> {
        let mut reg = Self::new();
        reg.register_builtin();
        reg.build_lookup_tables();
        Ok(reg)
    }

    fn build_lookup_tables(&mut self) {
        for desc in &self.descriptors {
            for ext in desc.extensions {
                self.source_extensions.insert(ext.to_string());
            }
            for filename in desc.reexport_filenames {
                self.reexport_filenames.insert(filename.to_string());
            }
        }
    }

    /// All registered source extensions. Replaces the hardcoded list in
    /// config/mod.rs:137-146 (default_languages) and
    /// dependency_matcher.rs:13-24 (strip_source_ext).
    pub fn source_extensions(&self) -> &HashSet<String> {
        &self.source_extensions
    }

    /// Check if a filename is a re-export hub for any registered language.
    /// Replaces the hardcoded matches! in mcp/tools/common.rs:7-13.
    pub fn is_reexport_file(&self, filename: &str) -> bool {
        self.reexport_filenames.contains(filename)
    }

    /// Language-specific test file check. Replaces the hardcoded checks
    /// in glossary_builder.rs:54-70.
    pub fn is_language_test_file(&self, file_path: &str) -> bool {
        let filename = file_path.rsplit('/').next().unwrap_or(file_path);
        for desc in &self.descriptors {
            // Only apply this language's patterns to files with matching extensions
            let ext_matches = desc.extensions.iter().any(|ext| {
                filename.ends_with(&format!(".{}", ext))
            });
            if !ext_matches {
                continue;
            }
            for suffix in desc.test_patterns.filename_suffixes {
                if filename.ends_with(suffix) {
                    return true;
                }
            }
            for prefix in desc.test_patterns.filename_prefixes {
                if filename.starts_with(prefix) {
                    return true;
                }
            }
        }
        false
    }

    pub fn descriptors(&self) -> &[RegisteredLanguage] {
        &self.descriptors
    }
}
```

### Dispatch Site Migration

Each of the 5 silent-failure dispatch sites changes as follows:

**Site 1: `config/mod.rs:137-146` (`default_languages`)**

Current: hardcoded array of 29 extension strings.

After: `default_languages()` queries `ParserRegistry::source_extensions()`. Because `Config` is loaded before the registry in some code paths, the fallback is to keep the hardcoded list as a `const` that is validated at test time against the registry. The preferred approach is to make `Config::default()` accept a `&ParserRegistry`:

```rust
// config/mod.rs
impl Config {
    pub fn default_with_registry(registry: &ParserRegistry) -> Self {
        Self {
            languages: registry.source_extensions().iter().cloned().collect(),
            ..Default::default()
        }
    }
}
```

A compile-time test ensures the hardcoded fallback stays in sync:

```rust
#[test]
fn default_languages_matches_registry() {
    let registry = ParserRegistry::with_builtins().unwrap();
    let from_registry: BTreeSet<String> = registry.source_extensions().iter().cloned().collect();
    let from_hardcoded = default_languages();
    assert_eq!(from_registry, from_hardcoded, "default_languages() is out of sync with ParserRegistry");
}
```

**Site 2: `dependency_matcher.rs:13-24` (`strip_source_ext`)**

Current: hardcoded match on 26 extension strings.

After: `strip_source_ext` takes a `&HashSet<String>` of known extensions (from `ParserRegistry::source_extensions()`), passed down through the call chain:

```rust
pub(crate) fn strip_source_ext<'a>(path: &'a str, known_extensions: &HashSet<String>) -> &'a str {
    if let Some((stem, ext)) = path.rsplit_once('.') {
        if known_extensions.contains(ext) {
            stem
        } else {
            path
        }
    } else {
        path
    }
}
```

**Site 3: `mcp/tools/common.rs:7-13` (`is_reexport_file`)**

Current: hardcoded `matches!` on 6 filenames.

After: delegates to `ParserRegistry::is_reexport_file()`. The `Manifest` struct already holds a reference to the project root; it needs access to registry data. The simplest path is to store the `reexport_filenames` set on `Manifest` at construction time (it is static after init).

```rust
// mcp/tools/common.rs
pub(crate) fn is_reexport_file(file_path: &str, reexport_filenames: &HashSet<String>) -> bool {
    let filename = file_path.rsplit('/').next().unwrap_or(file_path);
    reexport_filenames.contains(filename)
}
```

**Site 4: `glossary_builder.rs:54-70` (`is_test_file`)**

Current: hardcoded `ends_with("_test.go")`, `starts_with("test_")`, etc.

After: the directory-based checks (`tests/`, `test/`, `__tests__/`) stay as-is (they are language-neutral). The language-specific filename checks delegate to `ParserRegistry::is_language_test_file()`. The `is_test_export` symbol-name check (`test_`, `Test` prefixes) uses `LanguageTestPatterns::test_symbol_prefixes` from the matching descriptor.

**Site 5: `call_site_finder.rs:65-72` and `197-202`**

These dispatch sites contain substantial tree-sitter query logic, not just metadata. They cannot be replaced by a descriptor. They are addressed in Section 2 (per-language module pattern) instead.


## 2. Per-Language Module Pattern

### Problem

`private_members.rs` (825 LOC) and `call_site_finder.rs` (599 LOC) contain per-language tree-sitter logic gated by match arms on file extension. When a new language is added, these files must be updated or the language silently gets empty/false-positive results.

### Trait Definitions

Two traits define the per-language tree-sitter analysis contracts. They live in their respective module `mod.rs` files.

```rust
// src/manifest/private_members/mod.rs

/// Language-specific on-demand tree-sitter extraction of private/non-exported symbols.
/// Each language that supports include_private features implements this trait.
pub(crate) trait PrivateMemberExtractor {
    /// File extensions this extractor handles.
    fn extensions(&self) -> &'static [&'static str];

    /// Extract non-exported top-level function declarations.
    /// `exports` contains names of known exports to exclude.
    fn extract_top_level_functions(
        &self,
        source: &[u8],
        exports: &[&str],
    ) -> Result<Vec<TopLevelFunction>>;

    /// Extract private members (methods, fields) from classes/structs/impls.
    /// `class_names` specifies which classes to inspect.
    fn extract_private_members(
        &self,
        source: &[u8],
        class_names: &[&str],
    ) -> Result<HashMap<String, Vec<PrivateMember>>>;
}
```

```rust
// src/manifest/call_site_finder/mod.rs

/// Language-specific tree-sitter verification of call sites.
/// Used by fmm_glossary to filter false-positive dependents.
pub(crate) trait CallSiteVerifier {
    /// File extensions this verifier handles.
    fn extensions(&self) -> &'static [&'static str];

    /// Check whether `source` contains a method call expression
    /// matching `object.method_name(...)`.
    fn method_call_exists(
        &self,
        source: &[u8],
        method_name: &str,
    ) -> Option<bool>;

    /// Analyze bare function call sites for `fn_name`.
    /// Returns how the function is called (direct, namespace, not at all).
    /// Default: assume direct caller (conservative).
    fn bare_call_result(
        &self,
        source: &[u8],
        fn_name: &str,
    ) -> Option<BareCallSiteResult> {
        let _ = (source, fn_name);
        Some(BareCallSiteResult::DirectCaller)
    }
}
```

### Directory Structure

```
src/manifest/
  private_members/
    mod.rs              -- TopLevelFunction, PrivateMember structs,
                           PrivateMemberExtractor trait,
                           dispatch functions (extract_private_members,
                           extract_top_level_functions, find_*_range),
                           ExtractorRegistry
    typescript.rs       -- TsPrivateMemberExtractor (current lines 142-431)
    python.rs           -- PyPrivateMemberExtractor (current lines 433-518)
    rust.rs             -- RsPrivateMemberExtractor (NEW)
    tests.rs            -- all tests (current lines 524-825)

  call_site_finder/
    mod.rs              -- CallSiteVerifier trait, BareCallSiteResult enum,
                           find_call_sites, find_bare_function_callers,
                           VerifierRegistry
    typescript.rs       -- TsCallSiteVerifier (current call_exists_ts, bare_call_result_ts)
    python.rs           -- PyCallSiteVerifier (current call_exists_py)
    rust.rs             -- RsCallSiteVerifier (current call_exists_rs)
    tests.rs            -- all tests
```

### Dispatch Mechanism

Both modules use a simple registry pattern. The dispatch functions build a list of extractors/verifiers and match by extension. This replaces the current hardcoded match arms.

```rust
// src/manifest/private_members/mod.rs

/// Internal registry of all language-specific extractors.
/// Constructed on first use (lazy_static or inline Vec).
fn extractors() -> Vec<Box<dyn PrivateMemberExtractor>> {
    vec![
        Box::new(typescript::TsPrivateMemberExtractor),
        Box::new(python::PyPrivateMemberExtractor),
        Box::new(rust::RsPrivateMemberExtractor),
    ]
}

fn find_extractor(ext: &str) -> Option<Box<dyn PrivateMemberExtractor>> {
    extractors()
        .into_iter()
        .find(|e| e.extensions().contains(&ext))
}

pub fn extract_top_level_functions(
    root: &Path,
    rel_file: &str,
    exports: &[&str],
) -> Vec<TopLevelFunction> {
    let abs = root.join(rel_file);
    let source = match std::fs::read(&abs) {
        Ok(b) => b,
        Err(_) => return Vec::new(),
    };
    let ext = abs.extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();

    match find_extractor(&ext) {
        Some(extractor) => extractor
            .extract_top_level_functions(&source, exports)
            .unwrap_or_default(),
        None => Vec::new(),
    }
}
```

The same pattern applies to `call_site_finder/mod.rs`, replacing the match arms at lines 65-72 and 197-202.

### Before/After: `private_members.rs`

**Before** (src/manifest/private_members.rs:115-121):
```rust
match ext.as_str() {
    "ts" | "tsx" | "js" | "jsx" | "mjs" | "cjs" => {
        extract_ts_private(&source, class_names).unwrap_or_default()
    }
    "py" => extract_py_private(&source, class_names).unwrap_or_default(),
    _ => HashMap::new(),
}
```

**After** (src/manifest/private_members/mod.rs):
```rust
match find_extractor(&ext) {
    Some(extractor) => extractor
        .extract_private_members(&source, class_names)
        .unwrap_or_default(),
    None => HashMap::new(),
}
```

Adding Rust support (or any language) means creating `private_members/rust.rs` with a struct implementing `PrivateMemberExtractor` and adding it to `extractors()`. The dispatch function never changes.

### Concrete per-language module: `private_members/rust.rs`

```rust
// src/manifest/private_members/rust.rs

use super::{PrivateMember, PrivateMemberExtractor, TopLevelFunction};
use anyhow::Result;
use std::collections::HashMap;
use tree_sitter::Query;

pub(crate) struct RsPrivateMemberExtractor;

impl PrivateMemberExtractor for RsPrivateMemberExtractor {
    fn extensions(&self) -> &'static [&'static str] {
        &["rs"]
    }

    fn extract_top_level_functions(
        &self,
        source: &[u8],
        exports: &[&str],
    ) -> Result<Vec<TopLevelFunction>> {
        let lang: tree_sitter::Language = tree_sitter_rust::LANGUAGE.into();
        let mut parser = tree_sitter::Parser::new();
        parser.set_language(&lang)?;
        let tree = parser.parse(source, None)
            .ok_or_else(|| anyhow::anyhow!("parse failed"))?;

        // Query: non-pub fn at module scope
        let query_src = r#"
            (source_file
                (function_item
                    name: (identifier) @name) @fn)
        "#;
        let query = Query::new(&lang, query_src)?;
        let name_idx = query.capture_index_for_name("name").unwrap();
        let fn_idx = query.capture_index_for_name("fn").unwrap();

        let mut results = Vec::new();
        let mut cursor = tree_sitter::QueryCursor::new();
        for m in cursor.matches(&query, tree.root_node(), source) {
            let fn_node = m.captures.iter().find(|c| c.index == fn_idx);
            let name_node = m.captures.iter().find(|c| c.index == name_idx);
            if let (Some(fn_cap), Some(name_cap)) = (fn_node, name_node) {
                let name = name_cap.node.utf8_text(source)
                    .unwrap_or_default().to_string();
                // Skip exported functions and known exports
                if exports.contains(&name.as_str()) {
                    continue;
                }
                // Skip pub functions (they are exports, not private)
                let fn_text_start = fn_cap.node.start_byte();
                let prefix = &source[..fn_text_start];
                let trimmed = std::str::from_utf8(prefix)
                    .unwrap_or_default()
                    .trim_end();
                if trimmed.ends_with("pub")
                    || trimmed.ends_with("pub(crate)")
                    || trimmed.ends_with("pub(super)")
                {
                    continue;
                }
                results.push(TopLevelFunction {
                    name,
                    start: fn_cap.node.start_position().row + 1,
                    end: fn_cap.node.end_position().row + 1,
                });
            }
        }
        Ok(results)
    }

    fn extract_private_members(
        &self,
        source: &[u8],
        class_names: &[&str],
    ) -> Result<HashMap<String, Vec<PrivateMember>>> {
        let lang: tree_sitter::Language = tree_sitter_rust::LANGUAGE.into();
        let mut parser = tree_sitter::Parser::new();
        parser.set_language(&lang)?;
        let tree = parser.parse(source, None)
            .ok_or_else(|| anyhow::anyhow!("parse failed"))?;

        let mut result: HashMap<String, Vec<PrivateMember>> = HashMap::new();

        // Walk impl blocks, match type name against class_names,
        // collect non-pub fn items as private methods.
        let query_src = r#"
            (impl_item
                type: (type_identifier) @type_name
                body: (declaration_list
                    (function_item
                        name: (identifier) @method_name) @method))
        "#;
        let query = Query::new(&lang, query_src)?;
        let type_idx = query.capture_index_for_name("type_name").unwrap();
        let method_name_idx = query.capture_index_for_name("method_name").unwrap();
        let method_idx = query.capture_index_for_name("method").unwrap();

        let mut cursor = tree_sitter::QueryCursor::new();
        for m in cursor.matches(&query, tree.root_node(), source) {
            let type_cap = m.captures.iter().find(|c| c.index == type_idx);
            let name_cap = m.captures.iter().find(|c| c.index == method_name_idx);
            let method_cap = m.captures.iter().find(|c| c.index == method_idx);

            if let (Some(tc), Some(nc), Some(mc)) = (type_cap, name_cap, method_cap) {
                let type_name = tc.node.utf8_text(source).unwrap_or_default();
                if !class_names.contains(&type_name) {
                    continue;
                }
                // Check if method is pub - if so, skip (it is an export, not private)
                let method_text = mc.node.utf8_text(source).unwrap_or_default();
                if method_text.starts_with("pub ") || method_text.starts_with("pub(") {
                    continue;
                }
                let method_name = nc.node.utf8_text(source).unwrap_or_default().to_string();
                result.entry(type_name.to_string()).or_default().push(
                    PrivateMember {
                        name: method_name,
                        start: mc.node.start_position().row + 1,
                        end: mc.node.end_position().row + 1,
                        is_method: true,
                    },
                );
            }
        }

        Ok(result)
    }
}
```


## 3. Named Import Tracking

### Problem

`Metadata.named_imports` and `Metadata.namespace_imports` (src/parser/mod.rs:99-108) are only populated by the TypeScript parser. Python and Rust both use `..Default::default()` (python.rs:468, rust.rs:942), leaving these fields empty. This blocks `fmm_glossary` Layer 2 (named-import precision) and Layer 3 (call-site precision) for both languages.

### Python Named Imports

**Tree-sitter node types to walk:**

| Python syntax | tree-sitter node type | Named import mapping |
|---|---|---|
| `from module import A, B` | `import_from_statement` | `named_imports["module"] = ["A", "B"]` |
| `from . import sibling` | `import_from_statement` (relative) | `named_imports["."] = ["sibling"]` |
| `from .pkg import X` | `import_from_statement` (relative) | `named_imports[".pkg"] = ["X"]` |
| `import module` | `import_statement` | `namespace_imports.push("module")` |
| `import module as alias` | `import_statement` (aliased) | `namespace_imports.push("module")` |
| `from module import *` | `import_from_statement` (wildcard) | `namespace_imports.push("module")` |

**Tree-sitter query for named imports:**

```scheme
;; Match: from <module> import <name>
;; Captures the module path and each imported name individually.
(import_from_statement
  module_name: [
    (dotted_name) @source
    (relative_import) @source
  ]
  name: (dotted_name (identifier) @imported_name))
```

For `from X import A, B`, tree-sitter-python represents the imported names as sibling `dotted_name` children of the `import_from_statement`. The query must iterate all `name` children.

**Implementation location:** New method `extract_named_imports` on `PythonParser`, called from `parse()` (python.rs:462-471). The method populates `Metadata.named_imports` and `Metadata.namespace_imports` instead of relying on `..Default::default()`.

**Data flow:**

```
python.rs::parse()
  -> self.extract_named_imports(source, root_node)
  -> returns (HashMap<String, Vec<String>>, Vec<String>)
  -> stored in Metadata { named_imports, namespace_imports, ... }
  -> serialized to sidecar .fmm.yaml by db/writer.rs
  -> loaded by db/reader.rs into Manifest
  -> consumed by glossary_builder.rs Layer 2:
       for each candidate file's named_imports,
       check if the target symbol name appears in the values
  -> consumed by call_site_finder.rs Layer 3:
       verify actual call expression in source
```

**Before** (python.rs:462-471):
```rust
Ok(ParseResult {
    metadata: Metadata {
        exports,
        imports,
        dependencies,
        loc,
        ..Default::default()  // named_imports and namespace_imports are empty
    },
    custom_fields,
})
```

**After:**
```rust
let (named_imports, namespace_imports) = self.extract_named_imports(source, root_node);
Ok(ParseResult {
    metadata: Metadata {
        exports,
        imports,
        dependencies,
        loc,
        named_imports,
        namespace_imports,
    },
    custom_fields,
})
```

### Rust Named Imports

**Tree-sitter node types to walk:**

| Rust syntax | tree-sitter node type | Named import mapping |
|---|---|---|
| `use crate::module::Symbol;` | `use_declaration` with simple path | `named_imports["crate::module"] = ["Symbol"]` |
| `use crate::module::{A, B};` | `use_declaration` with `scoped_use_list` | `named_imports["crate::module"] = ["A", "B"]` |
| `use crate::module::*;` | `use_declaration` with `use_wildcard` | `namespace_imports.push("crate::module")` |
| `use anyhow::{Context, Result};` | `use_declaration` with `scoped_use_list` | `named_imports["anyhow"] = ["Context", "Result"]` |
| `use std::collections::HashMap;` | `use_declaration` with simple path | `named_imports["std::collections"] = ["HashMap"]` |
| `use super::foo::Bar;` | `use_declaration` with `super` prefix | `named_imports["super::foo"] = ["Bar"]` |

**Tree-sitter query for named imports (simple path):**

```scheme
;; Match: use path::to::Symbol;
;; The last identifier in the scoped_identifier is the imported name.
;; Everything before it is the module path.
(use_declaration
  argument: (scoped_identifier
    path: (_) @module_path
    name: (identifier) @imported_name))
```

**Tree-sitter query for grouped imports:**

```scheme
;; Match: use path::to::{A, B};
(use_declaration
  argument: (scoped_use_list
    path: (_) @module_path
    list: (use_list
      (identifier) @imported_name)))
```

**Nested groups** like `use std::collections::{HashMap, hash_map::{Entry, OccupiedEntry}};` require recursive walking of `use_list` children. The existing `use_declaration_deps` method (rust.rs:348-462) already handles this recursive structure for dependency extraction. The named import extraction can follow the same recursive pattern, collecting (module_path, symbol_name) pairs.

**Implementation location:** New method `extract_named_imports` on `RustParser`, called from `parse_inner()` (rust.rs:848-946). Same data flow as Python.

**Aliased imports** (`use crate::module::Symbol as Alias`): store the original name `Symbol`, not the alias. This matches the TypeScript behavior where `import { foo as bar }` stores `foo`.

**Self/crate/super filtering:** `use crate::*;` and `use super::*;` map to namespace imports. `use self::module::Symbol;` normalizes `self::` to `crate::` relative to the current module (matching the existing behavior in `extract_use_roots`).


## 4. Large File Decomposition Plan

### 4.1 `src/parser/builtin/typescript.rs` (2,011 LOC)

```
src/parser/builtin/
  typescript/
    mod.rs              (~300 LOC)
      - pub(crate) struct TypeScriptParser { ... }   [current lines 141-278]
      - impl TypeScriptParser { new(), new_tsx(), build() }
      - impl Parser for TypeScriptParser             [current lines 782-821]
      - impl LanguageDescriptor for TypeScriptParser  [NEW]
      - fn parse_with_aliases(...)                    [current lines 823-901]
      - fn extract_exports(...)                       [current lines 280-306]
      - fn extract_decorators(...)                    [current lines 613-635]
    tsconfig.rs         (~130 LOC)
      - pub(super) fn load_tsconfig_paths(...)        [current lines 11-84]
      - fn read_tsconfig_paths(...)                   [current lines 86-107]
      - fn strip_json_comments(...)                   [current lines 109-125]
      - pub(super) fn resolve_alias(...)              [current lines 127-139]
    extract_imports.rs  (~200 LOC)
      - pub(super) fn extract_imports(...)            [current lines 308-330]
      - pub(super) fn extract_dependencies(...)       [current lines 332-390]
      - pub(super) fn extract_named_imports(...)      [current lines 495-611]
    extract_classes.rs  (~170 LOC)
      - pub(super) fn extract_class_methods(...)      [current lines 392-438]
      - fn extract_method_entry(...)                  [current lines 440-493]
      - pub(super) fn extract_nested_symbols(...)     [current lines 638-745]
      - fn is_non_trivial_declarator(...)             [current lines 747-780]
    tests.rs            (~1,108 LOC)
      - #[cfg(test)] mod tests { ... }                [current lines 903-2011]
```

**Visibility:** All extraction methods become `pub(super)` functions that take `&TypeScriptParser` as the first argument (they are currently `impl TypeScriptParser` methods using `&self`). Since all files are within the `typescript` module, `pub(super)` is equivalent to module-private. The struct fields (query objects) use `pub(super)` visibility.

**Alternative:** Keep extraction methods as `impl TypeScriptParser` blocks in separate files. Rust allows multiple `impl` blocks for the same type across files within the same module. This avoids changing method signatures:

```rust
// typescript/extract_imports.rs
use super::TypeScriptParser;

impl TypeScriptParser {
    pub(super) fn extract_imports(&self, source: &str, root_node: tree_sitter::Node) -> Vec<String> {
        // ... moved from current lines 308-330
    }
}
```

This is the preferred approach because it requires zero signature changes.

### 4.2 `src/parser/builtin/rust.rs` (1,694 LOC)

```
src/parser/builtin/
  rust/
    mod.rs              (~245 LOC)
      - pub(crate) struct RustParser { ... }          [current lines 50-61]
      - impl RustParser { new() }                     [current lines 64-143]
      - impl Parser for RustParser                    [current lines 955-975]
      - impl LanguageDescriptor for RustParser        [NEW]
      - fn parse_inner(...)                           [current lines 848-946]
      - pub fn rust_use_path_to_dep(...)              [current lines 9-48]
    extract_exports.rs  (~314 LOC)
      - extract_exports(...)                          [current lines 145-220]
      - extract_impl_methods(...)                     [current lines 222-308]
      - extract_macro_exports(...)                    [current lines 598-710]
      - extract_pub_use_names(...)                    [current lines 750-845]
      - Helper functions: attrs_contain, attr_item_has_name,
        check_proc_macro_attr, extract_first_token_in_attr,
        collect_use_names, impl_type_name
    extract_imports.rs  (~152 LOC)
      - extract_imports(...)                          [current lines 310-342]
      - extract_dependencies(...)                     [current lines 348-378]
      - use_declaration_deps(...)                     [current lines 380-415]
      - extract_use_roots(...)                        [current lines 417-446]
      - use_declaration_root(...)                     [current lines 448-458]
      - leftmost_path_leaf(...)                       [current lines 460-462]
      - is_local_path(...)                            [current lines 344-346]
      - extract_named_imports(...)                    [NEW]
    metadata.rs         (~133 LOC)
      - count_unsafe_blocks(...)                      [current lines 464-478]
      - extract_derives(...)                          [current lines 480-530]
      - extract_trait_impls(...)                      [current lines 532-560]
      - extract_lifetimes(...)                        [current lines 562-580]
      - count_async_functions(...)                    [current lines 582-596]
    tests.rs            (~717 LOC)
      - #[cfg(test)] mod tests { ... }                [current lines 977-1694]
```

### 4.3 `src/parser/builtin/python.rs` (898 LOC)

Production code is 482 LOC. Convert to directory module for consistency with TS and Rust, and to accommodate the new `extract_named_imports` method:

```
src/parser/builtin/
  python/
    mod.rs              (~350 LOC)
      - pub(crate) struct PythonParser { ... }        [current lines 28-41]
      - impl PythonParser { new() }                   [current lines 44-119]
      - impl Parser for PythonParser                  [current lines 421-481]
      - impl LanguageDescriptor for PythonParser      [NEW]
      - All extraction methods as impl blocks         [current lines 121-418]
      - extract_named_imports(...)                    [NEW, ~80 LOC]
    tests.rs            (~416 LOC)
      - #[cfg(test)] mod tests { ... }                [current lines 482-898]
```

Python's production code at ~530 LOC (with new named imports) does not warrant further splitting yet. If more language features are added (dataclass fields, type hints), the TypeScript/Rust split pattern applies.

### 4.4 `src/search.rs` (1,614 LOC)

```
src/
  search/
    mod.rs              (~60 LOC)
      - pub use types
      - ExportHit, ImportHit, NamedImportHit, BareSearchResult,
        FileSearchResult, ExportHitCompact, SearchFilters, DEFAULT_SEARCH_LIMIT
    bare_search.rs      (~174 LOC)
      - pub fn bare_search(...)
      - fn export_match_score(...)
    filter_search.rs    (~118 LOC)
      - pub fn filter_search(...)
      - fn find_export_matches(...)
    dependency_graph.rs (~178 LOC)
      - pub fn dependency_graph(...)
      - pub fn dependency_graph_transitive(...)
    helpers.rs          (~56 LOC)
      - pub(crate) fn dep_targets_file(...)
      - pub(crate) fn export_hit_from_location(...)
      - pub(crate) fn file_entry_to_result(...)
    tests.rs            (~993 LOC)
```

### 4.5 `src/manifest/private_members.rs` (825 LOC)

Covered in Section 2. Directory structure:

```
src/manifest/
  private_members/
    mod.rs              (~140 LOC) - types, trait, dispatch, find_*_range
    typescript.rs       (~290 LOC)
    python.rs           (~86 LOC)
    rust.rs             (~120 LOC, NEW)
    tests.rs            (~301 LOC)
```

### 4.6 Remaining files

Files that only need test extraction (production code is under 600 LOC after extraction):

| File | Action | Technique |
|---|---|---|
| `src/db/writer.rs` (909 LOC) | Extract tests | `#[cfg(test)] #[path = "writer_tests.rs"] mod tests;` |
| `src/cli/search.rs` (744 LOC) | Extract tests | `#[path]` attribute |
| `src/format/yaml_formatters.rs` (700 LOC) | Extract tests | `#[path]` attribute |

`src/cli/mod.rs` (985 LOC): Extract file utilities into `src/cli/files.rs` (~200 LOC) and resolution logic into `src/cli/resolve.rs` (~100 LOC). The `Commands` enum stays in `mod.rs` (clap derive requires it in one place).


## 5. Execution Order

### Dependency Graph

```
Phase 1: Foundation (no dependencies, can be parallelized)
  1.1  LanguageDescriptor trait + LanguageTestPatterns struct in src/parser/mod.rs
  1.2  Decompose private_members.rs into directory module (mod.rs + typescript.rs + python.rs + tests.rs)
  1.3  Decompose call_site_finder.rs into directory module (mod.rs + typescript.rs + python.rs + rust.rs + tests.rs)

Phase 2: Descriptor Implementation (depends on 1.1)
  2.1  Implement LanguageDescriptor for all 17 parser structs
  2.2  Update ParserRegistry with RegisteredLanguage storage + lookup tables
  2.3  Update register_language! macro to capture descriptor data

Phase 3: Dispatch Site Migration (depends on 2.2)
  3.1  Migrate config/mod.rs default_languages to use registry
  3.2  Migrate dependency_matcher.rs strip_source_ext to use registry
  3.3  Migrate mcp/tools/common.rs is_reexport_file to use registry
  3.4  Migrate glossary_builder.rs is_test_file to use registry

Phase 4: Parser Decomposition (independent of Phases 2-3, depends on 1.1)
  4.1  Decompose typescript.rs into directory module
  4.2  Decompose rust.rs into directory module
  4.3  Decompose python.rs into directory module
  4.4  Decompose search.rs into directory module

Phase 5: Named Import Tracking (depends on 4.2 and 4.3 for clean file boundaries)
  5.1  Python named import extraction (extract_named_imports on PythonParser)
  5.2  Rust named import extraction (extract_named_imports on RustParser)

Phase 6: On-Demand Extraction (depends on 1.2, 1.3)
  6.1  Implement RsPrivateMemberExtractor in private_members/rust.rs
  6.2  Implement RsCallSiteVerifier in call_site_finder/rust.rs (bare_call_result)
  6.3  function_names custom field for Python parser
  6.4  function_names custom field for Rust parser

Phase 7: Test Extraction (independent, can run any time)
  7.1  Extract tests from db/writer.rs
  7.2  Extract tests from cli/search.rs
  7.3  Extract tests from format/yaml_formatters.rs
  7.4  Extract file/resolve utilities from cli/mod.rs
```

### Parallelization Matrix

| Work item | Can run in parallel with |
|---|---|
| 1.1 | 1.2, 1.3 |
| 1.2 | 1.1, 1.3 |
| 1.3 | 1.1, 1.2 |
| 2.1, 2.2, 2.3 | 4.1, 4.2, 4.3, 4.4, 7.* |
| 3.1, 3.2, 3.3, 3.4 | 4.*, 7.* |
| 4.1 | 4.2, 4.3, 4.4, 3.* |
| 5.1 | 5.2, 6.* |
| 6.1, 6.2 | 6.3, 6.4, 5.* |
| 7.* | Everything |

### Linear Issue Mapping

Each numbered item above maps to one Linear sub-parent issue under a parent epic. Phases map to milestones:

- **Milestone 1: Infrastructure** (Phase 1 + Phase 2) -- 6 issues
- **Milestone 2: Dispatch Elimination** (Phase 3) -- 4 issues
- **Milestone 3: Parser Decomposition** (Phase 4) -- 4 issues
- **Milestone 4: Language Parity** (Phase 5 + Phase 6) -- 6 issues
- **Milestone 5: Cleanup** (Phase 7) -- 4 issues

Total: 24 issues across 5 milestones.


## 6. New Language Checklist

After all changes described in this spec are implemented, adding language N+1 requires touching these files:

### Mandatory (compile-time enforced)

| Step | File | What to add |
|---|---|---|
| 1 | `src/parser/builtin/<lang>.rs` | Parser struct implementing `Parser` + `LanguageDescriptor` traits |
| 2 | `src/parser/builtin/mod.rs` | `pub mod <lang>;` declaration |
| 3 | `src/parser/mod.rs` `register_builtin()` | `register_language!(self, builtin::<lang>, <Lang>Parser);` |

Step 1 is enforced by the trait bounds. Steps 2-3 are enforced by the Rust compiler (the module must be declared and the parser must be registered for the code to reference it).

### Automatic (derived from LanguageDescriptor)

These are handled by the descriptor and require zero additional code:

| Concern | Previously required | Now automatic |
|---|---|---|
| Default extension list | Edit `config/mod.rs:137-146` | Derived from `LanguageDescriptor::extensions()` |
| Source extension recognition | Edit `dependency_matcher.rs:13-24` | Derived from `ParserRegistry::source_extensions()` |
| Re-export hub detection | Edit `mcp/tools/common.rs:7-13` | Derived from `LanguageDescriptor::reexport_filenames()` |
| Test file detection | Edit `glossary_builder.rs:54-70` | Derived from `LanguageDescriptor::test_file_patterns()` |

### Optional (feature completeness)

| Step | File | What to add | Impact if skipped |
|---|---|---|---|
| 4 | `src/manifest/private_members/<lang>.rs` | `<Lang>PrivateMemberExtractor` | `include_private: true` returns nothing for this language |
| 5 | `src/manifest/call_site_finder/<lang>.rs` | `<Lang>CallSiteVerifier` | glossary Layer 3 defaults to conservative (include all) |
| 6 | Parser's `custom_fields` | `function_names` field | `function_index` unavailable for this language |

### Verification

A `#[test]` in `src/parser/mod.rs` validates completeness:

```rust
#[test]
fn all_parsers_have_descriptors() {
    let registry = ParserRegistry::with_builtins().unwrap();
    // Every registered extension has a descriptor
    for ext in registry.extensions() {
        assert!(
            registry.descriptors().iter().any(|d| d.extensions.contains(&ext.as_str())),
            "Extension .{} is registered but has no LanguageDescriptor",
            ext
        );
    }
}

#[test]
fn descriptor_extensions_match_parser_extensions() {
    let registry = ParserRegistry::with_builtins().unwrap();
    for desc in registry.descriptors() {
        let parser = registry.get_parser(desc.extensions[0]).unwrap();
        assert_eq!(
            parser.extensions(),
            desc.extensions,
            "LanguageDescriptor extensions for {} do not match Parser::extensions()",
            desc.language_id
        );
    }
}
```

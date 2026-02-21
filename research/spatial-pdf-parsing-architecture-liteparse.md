---
title: "LiteParse: Spatial PDF Parsing with Grid Projection and OCR"
type: research
tags: [document-parsing, pdf, ocr, spatial-text, grid-projection, llamaindex, competitive-analysis]
summary: "Deep analysis of LiteParse, a TypeScript PDF parser that extracts spatially-aware text via grid projection. Core novelty is anchor-based column detection and spatial text layout preservation."
status: active
source: github-researcher
confidence: high
created: 2026-03-27
updated: 2026-03-27
---

## Executive Summary

LiteParse (run-llama/liteparse) is a TypeScript/Node.js PDF parsing tool from the LlamaIndex team. 2,643 stars, Apache 2.0, created Feb 2026. Its core contribution is a **spatial grid projection algorithm** that converts PDF text items (with bounding boxes) into spatially-faithful plain text, preserving column layouts, tables, and reading order. It combines PDF.js for native text extraction with Tesseract.js or HTTP OCR for scanned content, and PDFium for screenshot rendering. It is tightly scoped: PDF parsing only, no semantic analysis, no markdown output, no structural understanding.

**Key takeaway for Helioy**: The grid projection algorithm is genuinely clever for preserving spatial layout in plain text. However, LiteParse has no concept of document structure (headings, sections, lists), no semantic metadata extraction, and no markdown output. It operates at a lower level than what markdown-matters or fmm care about. Its OCR integration pattern (pluggable engine interface with HTTP spec) is worth noting.

## Architecture

### Codebase Structure

```
src/
  core/           # Parser class, config, type definitions
  engines/
    pdf/          # PDF.js text extraction engine + PDFium renderer
    ocr/          # Tesseract.js + HTTP OCR engine interface
  processing/     # Grid projection, bbox calculation, text cleanup
  conversion/     # Format conversion (Office, images -> PDF via LibreOffice/ImageMagick)
  output/         # JSON and text formatters
  vendor/pdfjs/   # Vendored PDF.js build with CJK cmaps and standard fonts
cli/              # Commander-based CLI
packages/python/  # Python wrapper (subprocess shim around Node CLI)
```

### Language and Dependencies

- **TypeScript** (ESM modules, compiled with tsc)
- **Runtime**: Node.js >= 18
- **Key deps**: PDF.js (vendored), @hyzyla/pdfium (WASM), tesseract.js v7, sharp, zod, axios, commander, p-limit, file-type, unified
- **Build**: tsc + vendor copy. No bundler.
- **Tests**: vitest

### Data Model

The core data types form a clean hierarchy:

1. **`PageData`** (engine output): Raw text items + images + annotations + garbled text regions per page
2. **`ProjectionTextBox`** (processing intermediate): Text items enriched with snap alignment, anchor metadata, and rotation handling
3. **`ParsedPage`** (output): Page number, dimensions, spatial text string, text items array, optional bounding boxes
4. **`ParseResult`** (final): Array of ParsedPages + concatenated full text + optional JSON representation

**`TextItem`** carries: `str`, `x`, `y`, `width`, `height`, `fontName`, `fontSize`, `rotation`, and optional `MarkupData` (highlight, underline, strikeout, squiggly).

## Core Concepts

### Problem Statement

LiteParse solves one problem: extracting text from PDFs while preserving spatial layout. PDF.js gives you text items with coordinates, but reconstructing reading order, column boundaries, and table structure from raw coordinates is hard. LiteParse's grid projection algorithm addresses this.

### Mental Model

The system thinks in terms of **spatial text layout**. A PDF page is a 2D canvas of positioned text items. The parser's job is to project these items onto a character grid (monospace plain text) that visually approximates the original layout. Columns align. Tables have spacing. Reading order follows visual position.

This is explicitly spatial, explicitly visual. There is no semantic model of documents. No concept of headings, sections, paragraphs, or structure.

## Key Features

1. **Spatial text extraction**: Grid projection preserves column layouts, table alignments, multi-column documents
2. **OCR integration**: Tesseract.js built-in, pluggable HTTP OCR with published API spec
3. **Selective OCR**: Only runs OCR on pages/regions with little native text or garbled font output
4. **Multi-format input**: Office docs via LibreOffice, images via ImageMagick, all converted to PDF first
5. **Bounding boxes**: Per-text-item coordinates in PDF points
6. **Screenshot generation**: PDFium-based page rendering to PNG/JPG
7. **searchItems API**: Find text phrases across text items with merged bounding boxes
8. **Batch processing**: Directory-level parsing with engine reuse
9. **Python wrapper**: Subprocess-based Python package wrapping the Node CLI
10. **Markup detection**: Highlights, underlines, strikeouts extracted from PDF annotations

## Data Flow

### Parsing Pipeline

```
Input (path/buffer)
  |
  v
Format Detection (file-type magic bytes)
  |
  v
Conversion if needed (LibreOffice/ImageMagick -> PDF)
  |
  v
PDF.js Text Extraction
  - Matrix transforms for coordinate normalization
  - Garbled font detection (Private Use Area, script mixing)
  - Buggy font marker decoding (tabular figures mapping)
  - Control character stripping
  |
  v
Selective OCR (if enabled)
  - Pages with <100 chars of native text
  - Pages with embedded images
  - Garbled text regions (targeted OCR)
  - Scale factor conversion: OCR pixels -> PDF points (72/dpi)
  - Overlap deduplication: OCR vs native text
  |
  v
Grid Projection (the core algorithm)
  1. Build ProjectionTextBoxes from all text items
  2. Handle rotation (90/180/270 degree text)
  3. Sort by Y then X, group into lines (Y-tolerance based)
  4. Merge adjacent boxes into words
  5. Detect column anchors (left, right, center alignment)
  6. Resolve anchor conflicts (left > right > center priority)
  7. Project text onto character grid using anchor positions
  8. Clean sparse blocks, remove margins
  |
  v
Output Formatting
  - Text: spatial layout string per page
  - JSON: pages array with text items, bounding boxes, dimensions
```

### Grid Projection Algorithm (Deep Dive)

This is the most interesting part of the codebase (`src/processing/gridProjection.ts`, ~1200 lines).

**Phase 1: Line Detection**
- Sort text boxes by Y position (with tolerance for subscripts/superscripts)
- Group boxes into lines based on Y-overlap (midpoint within line bounds)
- Merge adjacent boxes into words based on spacing (< average character width)
- Detect margin line numbers in two-column docs

**Phase 2: Anchor Extraction**
- For each text box, record its left edge, right edge, and center as potential column anchors
- Group nearby anchors within 2-unit tolerance
- Apply `deltaMin`: anchors must have vertically proximate members (within ~17-20% of page height)
- Apply `intercept`: reject anchors where text from other lines crosses the anchor position
- Try to align floating (unsnapped) boxes with neighboring lines' anchors

**Phase 3: Snap Resolution**
- Each box can belong to left, right, or center anchor
- Duplicates resolved by anchor population count: left > right > center
- Singleton anchors deleted

**Phase 4: Text Rendering**
- Forward anchors track minimum column positions from prior lines
- Text rendered character by character with spacing computed from anchor positions
- FLOATING_SPACES (2) between justified text items
- COLUMN_SPACES (4) between snapped columns
- Subscript/superscript detection converts to Unicode sub/superscript characters
- Sparse blocks (>80% whitespace) get compressed

**Phase 5: Cleanup**
- Margin detection and removal per page
- Null character removal
- Dot garbage filtering (>100 dots)

## Unique Ideas

### 1. Garbled Font Detection
`isGarbledFontOutput()` in `pdfjs.ts` detects corrupted ToUnicode mappings by analyzing Unicode block distribution. Checks for Private Use Area characters, script mixing (Arabic + Latin Extended), suspicious Unicode ranges, and control character dominance. When detected, the text region is saved for targeted OCR. This is an underappreciated problem in PDF parsing.

### 2. Tabular Figures Decoding
PDFs with "Differences" font arrays often encode digits using non-standard glyph IDs (17-31 range). LiteParse maintains two candidate mapping tables and scores decoded results for "number-likeness" (comma-separated thousands, decimal patterns) to pick the best interpretation. Solves government/census PDF corruption.

### 3. Anchor-Based Column Detection
The anchor system (left, right, center) with intercept testing and delta-min filtering is a pragmatic approach to column detection without full layout analysis. The key insight: vertically-aligned text edges that aren't intercepted by cross-column text are likely column boundaries.

### 4. Pluggable OCR with Standard API
The OCR API spec (`OCR_API_SPEC.md`) defines a clean HTTP contract: POST multipart with image, return JSON with text + bbox + confidence. This allows swapping Tesseract for EasyOCR or PaddleOCR without code changes. Reference implementations provided.

### 5. Selective OCR Targeting
Rather than OCR-ing entire pages, LiteParse identifies specific needs: text-sparse pages, embedded images, and garbled text regions. For garbled regions, OCR results are filtered to only include items overlapping those specific bounding boxes. This is efficient and avoids duplicating already-extracted text.

### 6. Rotation Handling
Groups text by rotation angle, transforms coordinates to normalize reading order, handles 90/180/270 degree text with proper X/Y swapping and Y-offset insertion to prevent alignment conflicts with unrotated content.

## Strengths

1. **Focused scope**: Does one thing (spatial PDF text extraction) and does it well
2. **Zero-setup OCR**: Tesseract.js works out of the box, no system deps required
3. **Robust font handling**: Garbled font detection + tabular figures decoding addresses real-world PDF corruption
4. **Spatial layout preservation**: The grid projection genuinely maintains column structure in plain text output
5. **Clean engine abstraction**: PdfEngine and OcrEngine interfaces allow swapping implementations
6. **Cross-platform**: Node.js + PDFium WASM means it runs everywhere
7. **Performance-conscious**: Parallel OCR with p-limit, selective OCR targeting, batch mode with engine reuse
8. **Well-documented**: README, AGENTS.md, OCR_API_SPEC.md, inline JSDoc

## Weaknesses and Gaps

1. **No structural understanding**: Cannot identify headings, sections, lists, tables as semantic structures. Output is flat spatial text. No document outline extraction.
2. **No markdown output**: Only plain text and JSON with raw text items. No heading detection, list formatting, or table markup generation.
3. **PDF-centric pipeline**: Everything converts to PDF first. Markdown, HTML, and code files get read as raw text or passed through LibreOffice. No native parsing for structured formats.
4. **Grid projection complexity**: ~1200 lines of coordinate math with magic numbers (FLOATING_SPACES=2, COLUMN_SPACES=4, Y_SORT_TOLERANCE, MERGE_TOLERANCE=2). Hard to maintain, and there is an open PR for justified content issues.
5. **No chunking**: No built-in chunking strategy. Output is raw per-page text. Consumers must implement their own splitting logic.
6. **Python wrapper is a subprocess shim**: The Python package just shells out to the Node CLI via subprocess. No native Python implementation. Adds Node.js dependency for Python users.
7. **No metadata extraction**: Does not extract document title, author, creation date, or other PDF metadata into the parse result (metadata is fetched internally but not exposed).
8. **Limited table handling**: Tables are preserved spatially (columns align) but not semantically. No row/column detection, no cell extraction, no CSV/table output.
9. **No incremental parsing**: Must parse entire document (or page range). Cannot incrementally update after document changes.
10. **Missing: Rust core performance module**: Issue #49 is an RFC for a Rust processing module, indicating performance pressure on the TypeScript grid projection.

## Relevance to Helioy

### markdown-matters
**Low direct overlap.** LiteParse does not produce markdown, does not understand markdown structure, and does not index markdown. However, if markdown-matters ever needs to ingest PDF content, LiteParse's text extraction could serve as a preprocessing step. The spatial text output could feed into a markdown structure detector.

The searchItems API (phrase search with merged bounding boxes across text items) is a simple but useful pattern. markdown-matters already has FTS5, which is more powerful.

### frontmatter-matters (fmm)
**No overlap.** fmm indexes code structure (exports, functions, dependencies). LiteParse parses visual documents. Different problem domains entirely. fmm's precomputed structural intelligence has no analog in LiteParse.

However, the **anchor-based column detection** concept has a loose analog to how fmm might detect code structure from indentation patterns. The idea of detecting alignment as structure is transferable.

### context-matters
**Potential integration point.** If context-matters needs to ingest PDF documents as context entries, LiteParse's text extraction pipeline could serve as the ingestion adapter. The per-page structure (page number, text, text items with positions) maps naturally to scoped entries.

The `TextItem` type (text + position + font + size) is a rich representation that could inform metadata extraction for context entries. Font size could hint at heading vs body text.

### attention-matters
**No direct relevance.** Geometric memory on S3 hypersphere operates at a different abstraction level than spatial document parsing.

### Ideas Worth Considering

1. **Font-size based heading detection**: LiteParse already extracts `fontSize` per text item. A simple heuristic (items with fontSize > 1.3x median are likely headings) could add structural understanding on top of the spatial text. This would bridge the gap between LiteParse-style extraction and markdown-matters-style structural awareness.

2. **OCR engine interface pattern**: The pluggable OCR design (in-process default + HTTP API spec) is a good model for any Helioy component that needs pluggable backends. Clean separation, standard contract, reference implementations.

3. **Garbled content detection**: The technique of detecting corrupted text via Unicode block analysis and falling back to OCR for those specific regions is useful for any system that ingests PDFs. Could inform a "content quality" signal in context-matters.

4. **Spatial text as intermediate representation**: The grid projection approach treats text as positioned in 2D space and then projects to 1D (lines). This "spatial intermediate representation" is a useful concept. For markdown-matters, a similar approach could work for understanding markdown layout: parse to AST, annotate with position data, then reason about structure.

## Sources Consulted

- `README.md` - Feature overview and usage
- `src/core/types.ts` - Complete type system (374 lines)
- `src/core/parser.ts` - Main LiteParse class (447 lines)
- `src/core/config.ts` - Default configuration
- `src/engines/pdf/pdfjs.ts` - PDF.js integration, garbled font detection, tabular figures (708 lines)
- `src/engines/pdf/pdfium-renderer.ts` - PDFium screenshot renderer
- `src/engines/pdf/interface.ts` - PdfEngine and PageData interfaces
- `src/engines/ocr/interface.ts` - OcrEngine interface
- `src/engines/ocr/tesseract.ts` - Tesseract.js integration with worker pool
- `src/engines/ocr/http-simple.ts` - HTTP OCR client
- `src/processing/gridProjection.ts` - Core grid projection algorithm (~1200 lines)
- `src/processing/bbox.ts` - Bounding box construction and OCR overlap filtering
- `src/processing/cleanText.ts` - Margin detection and text cleanup
- `src/processing/textUtils.ts` - OCR artifact cleaning, sub/superscript conversion
- `src/processing/markupUtils.ts` - Markup tag application
- `src/processing/searchItems.ts` - Phrase search across text items
- `src/conversion/convertToPdf.ts` - Multi-format conversion via LibreOffice/ImageMagick
- `src/output/json.ts` - JSON output formatting
- `src/output/text.ts` - Text output formatting
- `packages/python/liteparse/parser.py` - Python subprocess wrapper
- `packages/python/liteparse/types.py` - Python type definitions
- `OCR_API_SPEC.md` - HTTP OCR API specification
- GitHub issues #49 (Rust module RFC), #73 (searchItems bug), #58 (edge runtime), #55 (justified content PR)
- Git log (last 20 commits)

## Open Questions

1. **Performance at scale**: The grid projection algorithm is O(n^2) in several places (anchor intercept testing, overlap checking). How does it perform on 500+ page documents with dense tables? Issue #49 suggests performance is already a concern.
2. **Accuracy benchmarks**: The repo has a `dataset_eval_utils/` directory but I did not investigate evaluation results. How does the spatial text extraction compare to LlamaParse Cloud or other parsers?
3. **Markdown output plans**: The `applyMarkupTags` function outputs markdown-like syntax (~~strikeout~~, ==highlight==, __underline__). Is there a plan to add full markdown output? The code hints suggest yes but nothing is implemented.
4. **Heading/structure detection**: With fontSize already extracted, why is there no heading detection? This seems like low-hanging fruit. Possibly intentional to drive users toward LlamaParse Cloud.

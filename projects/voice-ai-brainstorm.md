---
title: "Voice: AI/NLP Engineering Brainstorm"
category: projects
tags: [voice, nlp, ai-slop, style-transfer, brainstorm]
created: 2026-03-17
author: ai-engineer
---

# Voice: AI/NLP Engineering Brainstorm

Technical brainstorm for the Voice project from an AI/NLP engineering perspective.

---

## 1. Slop Detection

### Multi-layered detection architecture

No single signal is sufficient. AI slop is a syndrome, not a symptom. Detection requires stacking orthogonal signals.

**Layer 1: Lexical fingerprinting (fast, rule-based)**
- Token frequency analysis against known LLM overuse distributions. LLMs have measurable lexical biases: "delve", "crucial", "landscape", "straightforward", "it's worth noting", "let's unpack". Build a weighted dictionary of slop tokens with severity scores.
- Em dash density. Human writers average ~0.3 em dashes per 1000 words. GPT-4 class models produce 5-15x that rate. Simple ratio check.
- Hedge phrase density: "it's important to note", "it should be mentioned", "while there are many approaches". Count per paragraph.

**Layer 2: Structural fingerprinting (medium cost)**
- Sentence length variance. LLM output converges toward a narrow band (15-25 words). Human prose has higher variance with occasional very short or very long sentences.
- Paragraph template matching. LLMs favor: topic sentence, 2-3 supporting sentences, transitional closer. Detect this pattern via POS-tag sequence matching.
- List/enumeration frequency. LLMs overuse numbered and bulleted lists relative to human prose in most registers.
- Transition word density. "Furthermore", "Additionally", "Moreover" appearing at paragraph boundaries at rates 3-5x human baseline.

**Layer 3: Perplexity-based detection (higher cost, higher accuracy)**
- Use a small local model (e.g., GPT-2 or a 1B parameter model) as a reference. Compute per-token perplexity. LLM-generated text has lower and more uniform perplexity because it follows high-probability paths.
- Burstiness metric: human text alternates between low-perplexity (predictable) and high-perplexity (surprising) spans. LLM text stays flat. Measure the standard deviation of windowed perplexity scores.

**Layer 4: Stylometric divergence (highest accuracy, requires baseline)**
- When a voice profile exists, compute divergence between the input text and the profile across all stylometric dimensions. High divergence from the user's own voice is a strong slop signal.

### Recommended approach

Start with Layer 1 + Layer 2 as the default (zero-cost, runs locally, no model required). Layer 3 as an opt-in for higher accuracy. Layer 4 activates automatically when a voice profile exists.

Each layer produces a confidence score. Combine via weighted ensemble. Output a per-span annotation: each sentence or paragraph gets a slop probability and a category label.

---

## 2. Slop Taxonomy

### Category: Lexical (word and phrase choice)

| Pattern | Examples | Severity |
|---------|----------|----------|
| Corporate superlatives | "robust", "comprehensive", "cutting-edge", "state-of-the-art" | Medium |
| Empty intensifiers | "incredibly", "absolutely", "truly", "fundamentally" | Medium |
| LLM-specific lexicon | "delve", "landscape", "multifaceted", "pivotal", "nuanced" | High |
| Hedging qualifiers | "it's worth noting that", "it should be mentioned", "it bears mentioning" | High |
| Formulaic openers | "Great question!", "That's a great point!", "Absolutely!" | Critical |
| Filler transitions | "Furthermore", "Additionally", "Moreover", "In addition" | Medium |
| Metacommentary | "Let me explain", "Here's the thing", "To put it simply" | High |

### Category: Syntactic (sentence and paragraph structure)

| Pattern | Examples | Severity |
|---------|----------|----------|
| Uniform sentence length | Sentences clustering in 15-25 word band | Medium |
| Topic-support-transition paragraphs | Every paragraph follows the same 3-part template | High |
| Excessive parallelism | "It's not just X, it's Y. It's not just A, it's B." | High |
| Em dash overuse | Using em dashes as the default parenthetical device | Medium |
| Colon-list pattern | "There are three key considerations: X, Y, and Z" | Medium |

### Category: Rhetorical (argument and reasoning patterns)

| Pattern | Examples | Severity |
|---------|----------|----------|
| Both-sides equivocation | "While X has merits, Y also has advantages" without committing | High |
| False comprehensiveness | "There are several factors to consider" followed by exhaustive enumeration | Medium |
| Premature summarization | "In summary" or "To recap" appearing too early or too often | Medium |
| Hollow acknowledgment | "That's a valid concern" followed by dismissal | High |
| Stepwise scaffolding | "First... Second... Third... Finally..." for every argument | Medium |

### Category: Tonal (voice and register)

| Pattern | Examples | Severity |
|---------|----------|----------|
| Relentless positivity | Every suggestion framed as exciting or promising | High |
| Over-politeness | Excessive hedging to avoid offense | Medium |
| Authority without commitment | Confident-sounding claims with escape hatches | High |
| Register flatness | Same formality level maintained regardless of content | Medium |
| Emotional vacancy | Technical accuracy without authentic perspective | High |

---

## 3. Voice Profiling

### Dimensions of a voice fingerprint

A voice profile is a high-dimensional feature vector extracted from writing samples. The dimensions:

**Lexical dimensions**
- Vocabulary richness (type-token ratio, hapax legomena ratio)
- Word length distribution (mean, variance, skewness)
- Domain-specific vocabulary frequency
- Contraction usage rate
- Profanity/slang tolerance level
- Preferred synonyms map (e.g., "big" vs "large" vs "substantial")

**Syntactic dimensions**
- Sentence length distribution (mean, std, min, max, skewness)
- Clause depth distribution (simple vs compound vs complex)
- Active/passive voice ratio
- Question frequency
- Fragment frequency (intentional incomplete sentences)
- Coordination vs subordination ratio

**Punctuation dimensions**
- Em dash frequency and usage context
- Semicolon frequency
- Exclamation mark frequency
- Parenthetical frequency and nesting depth
- Ellipsis usage
- Colon usage patterns

**Rhetorical dimensions**
- Metaphor/simile density
- Anaphora and repetition patterns
- Irony/sarcasm markers
- Direct address frequency ("you", "we")
- Imperative sentence frequency
- Rhetorical question frequency

**Structural dimensions**
- Paragraph length distribution
- Section/heading usage patterns
- List vs prose ratio
- Quote integration style
- Opening/closing patterns

**Tonal dimensions**
- Formality score (F-score based on POS distribution)
- Sentiment polarity distribution
- Hedging frequency
- Confidence/assertiveness markers
- Humor markers

### Extraction pipeline

```
Input: 5-50 writing samples (2000+ words total)
  |
  v
[Tokenization + POS tagging + dependency parsing]
  |
  v
[Feature extraction across all dimensions]
  |
  v
[Statistical aggregation: distributions, not point estimates]
  |
  v
[Outlier filtering: remove samples that diverge > 2 std from mean]
  |
  v
[Profile serialization: JSON/TOML with distributions as histograms]
  |
  v
Output: VoiceProfile object
```

Minimum viable extraction uses spaCy for parsing + custom feature extractors. No GPU required. Runs in seconds on a typical corpus.

### Profile representation

```toml
[meta]
name = "stuart"
samples = 23
total_words = 14500
confidence = 0.87

[lexical]
type_token_ratio = { mean = 0.72, std = 0.04 }
avg_word_length = { mean = 4.8, std = 0.3 }
contraction_rate = 0.65
vocabulary_tier = "technical-informal"

[syntactic]
sentence_length = { mean = 14.2, std = 8.7, skew = 1.3 }
fragment_rate = 0.08
active_voice_ratio = 0.82
question_rate = 0.04

[punctuation]
em_dash_per_1k = 0.2
semicolon_per_1k = 1.4
exclamation_per_1k = 0.3

[tonal]
formality = 0.45
assertiveness = 0.78
hedge_rate = 0.02
```

---

## 4. Voice Application (Style Transfer)

### Approach 1: Constrained LLM rewriting (primary)

Use an LLM to rewrite text with the voice profile injected as system-level constraints. The profile translates into concrete instructions:

```
Rewrite the following text to match this voice:
- Sentence length: average 14 words, high variance, allow fragments
- Never use em dashes. Use commas, periods, or parentheses instead.
- Contraction rate: 65%. Use contractions naturally.
- Avoid: [slop term blocklist]
- Tone: technical-informal, assertive, low hedging
- Active voice: 82% of sentences
```

This works because LLMs are good at following stylistic constraints when they're concrete and measurable.

**Advantages:** High quality, handles semantic content well, adapts to context.
**Disadvantages:** Requires API call, latency, cost per transformation.

### Approach 2: Rule-based post-processing (fast path)

A pipeline of deterministic transformations:

1. **Slop removal**: Delete or replace detected slop phrases using a substitution table
2. **Em dash elimination**: Replace em dashes with contextually appropriate alternatives (commas, periods, parentheses) based on clause structure
3. **Hedge stripping**: Remove qualifying phrases that dilute assertiveness
4. **Sentence restructuring**: Split overly long sentences, merge overly short ones to match target distribution
5. **Transition pruning**: Remove unnecessary transition words at paragraph boundaries
6. **Contraction injection/removal**: Adjust contraction rate to match profile

**Advantages:** Zero cost, instant, deterministic, runs offline.
**Disadvantages:** Limited to surface-level transformations. Cannot restructure arguments or shift register significantly.

### Approach 3: Hybrid pipeline (recommended)

```
Input text
  |
  v
[Rule-based slop removal]  -- fast, deterministic
  |
  v
[Rule-based surface transforms]  -- contractions, punctuation, hedge removal
  |
  v
[Delta check: how far is result from target profile?]
  |
  v
  If close enough --> output
  If still divergent --> [LLM rewrite with voice constraints]
  |
  v
Output
```

The hybrid approach minimizes API calls. Most text only needs the rule-based pass. The LLM fires only when deeper restructuring is needed. This keeps costs low while maintaining quality.

### Sentence-level vs document-level

Operate at sentence level for rule-based transforms. Operate at paragraph level for LLM rewrites (preserves coherence across sentences). Never rewrite an entire document in one pass; the LLM will impose its own structure.

---

## 5. Reference Library Architecture

### Voice as data, not code

Each reference voice is a directory:

```
voices/
  hemingway/
    profile.toml          # extracted voice profile
    samples/              # source writing samples (for re-extraction)
    constraints.toml      # hand-tuned overrides and rules
    slop_overrides.toml   # writer-specific slop definitions
    README.md             # attribution and license info
```

### Profile + constraints separation

The `profile.toml` is auto-extracted from samples. The `constraints.toml` captures human-authored rules that statistical extraction misses:

```toml
# constraints.toml for hemingway
[rules]
max_sentence_length = 25
ban_words = ["very", "really", "just", "actually", "basically"]
prefer_concrete_nouns = true
max_adjectives_per_noun = 1
avoid_adverbs = true
dialogue_style = "said-only"  # no "exclaimed", "muttered", etc.

[examples]
good = [
  "The old man was thin and gaunt.",
  "He was an old man who fished alone.",
]
bad = [
  "The incredibly weathered elderly gentleman was remarkably thin.",
]
```

### Composability

Allow voice profiles to be composed:

```bash
voice apply --voice hemingway --overlay technical --text input.md
```

An overlay modifies specific dimensions without replacing the base profile. This lets users say "write like Hemingway but with technical vocabulary allowed."

### Distribution format

Voices are distributable as tarballs or git-tracked directories. A registry (similar to npm or crates.io) could host community-contributed voices. Each voice requires attribution metadata and license compliance for the source samples.

---

## 6. Model Considerations

### Can this work without fine-tuning? Yes, for the core use case.

**Prompt engineering handles:**
- Slop detection via pattern matching (no model needed)
- Voice application via constrained rewriting (works with any capable LLM)
- Voice extraction from samples (statistical, no ML required)

**Where fine-tuning adds value:**
- A small classifier (DistilBERT scale, ~66M params) fine-tuned on human vs LLM text improves slop detection accuracy beyond rule-based methods. Training data: collect pairs of human-written and LLM-rewritten versions of the same content.
- A style-transfer model fine-tuned on parallel corpora (same content, different voices) could replace the LLM rewriting step for offline/local use.

### Local vs API tradeoffs

| Capability | Local (no API) | API-assisted |
|-----------|---------------|-------------|
| Slop detection | Rule-based + small classifier | Full perplexity analysis |
| Voice extraction | spaCy + custom features | Same (no API needed) |
| Voice application | Rule-based transforms only | LLM rewriting for deep transforms |
| Quality | Good (70-80% of slop caught) | Excellent (90%+ with LLM pass) |
| Latency | <100ms | 1-5s per paragraph |
| Cost | Zero | $0.001-0.01 per transformation |

### Recommended model stack

- **Detection classifier**: DistilBERT fine-tuned on AI-vs-human dataset. ~66M params. Runs on CPU in <50ms.
- **Perplexity reference**: GPT-2 small (124M params) or TinyLlama (1.1B). Local inference for burstiness scoring.
- **Rewriting**: Anthropic Claude or OpenAI API for high-quality voice application. Ollama with Llama 3 8B for offline/local rewriting.

### What about embeddings?

Voice profiles could include a centroid embedding (mean of sentence embeddings across samples). Cosine distance between the centroid and a candidate text provides a quick "does this sound like the target voice" check. Use a sentence transformer (all-MiniLM-L6-v2, 22M params) for this.

---

## 7. Evaluation

### Automated metrics

**Slop detection accuracy:**
- Build a labeled dataset: 500+ passages labeled as "human", "AI", or "AI-with-slop-removed"
- Measure precision/recall/F1 for slop span identification
- Target: 85%+ F1 on slop detection at the sentence level

**Voice match score:**
- Feature-level distance: for each dimension in the voice profile, compute the distance between the transformed text's feature value and the target profile's distribution. Aggregate via weighted mean.
- Embedding cosine similarity: compare sentence embeddings of transformed text against the voice profile's centroid embedding.
- Composite score: 0-100 scale combining feature distance and embedding similarity.

**Readability preservation:**
- Flesch-Kincaid scores before and after transformation should remain within 1 grade level
- Semantic similarity (BERTScore or similar) between original and transformed text should be >0.85
- Factual consistency: no information should be added or removed during transformation

### Human evaluation protocol

**Turing-style test:**
1. Present evaluators with 3 passages: one written by the target author, one AI-generated, one Voice-transformed
2. Ask: "Which was written by [author name]?"
3. Success metric: Voice-transformed text is misidentified as human-written >60% of the time

**A/B preference test:**
1. Present pairs: original AI text vs Voice-transformed text
2. Ask: "Which sounds more natural/human?"
3. Success metric: Voice-transformed preferred >75% of the time

**Voice fidelity test (for reference voices):**
1. Mix Voice-transformed passages with genuine passages from the target author
2. Ask literary experts to identify the fakes
3. Success metric: experts fail to distinguish >40% of the time

### Regression testing

Every voice profile gets a test suite: 10-20 input passages with expected transformation outcomes. CI runs these on every model/rule change. Track voice match score over time. Alert on regressions >5%.

---

## Technical Architecture Summary

```
                    CLI Interface
                         |
            +------------+------------+
            |            |            |
        [Detect]    [Profile]    [Apply]
            |            |            |
    +-------+-------+   |    +-------+-------+
    | Rule engine   |   |    | Rule-based    |
    | (Layer 1+2)   |   |    | transforms    |
    +-------+-------+   |    +-------+-------+
            |            |            |
    +-------+-------+   |    +-------+-------+
    | ML classifier |   |    | LLM rewrite   |
    | (Layer 3)     |   |    | (if needed)   |
    +-------+-------+   |    +-------+-------+
            |            |            |
            +------------+------------+
                         |
                  Voice Profiles
                  (TOML + samples)
```

Three commands. Three pipelines. Shared profile format. The rule engine handles the common case fast and free. The ML/LLM layers activate when precision matters. Everything runs locally by default with optional API enhancement.

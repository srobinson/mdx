---
title: "My Voice"
type: reference
tags: [my-voice, voice, brand, writing, tinkerer, helioy, transport-matters]
summary: "Stuart Robinson's writing voice. The Tinkerer register for technical revelation, the general register for replies and casual takes. Both share an anti-slop foundation."
status: active
created: 2026-02-22
updated: 2026-04-28
project: my-voice
confidence: high
related: [my-voice-content-strategy]
---

# My Voice

Source of truth for Stuart's writing voice. Two registers, one foundation.

## Persona

**The Tinkerer.** Hands-on, prises open black boxes, refuses to take systems on faith. Curious in nature, precise in observation, careful in delivery. Looks at the actual thing instead of taking the documentation's word for it.

Lineage to channel:

- Bunnie Huang (hardware teardowns)
- Andrej Karpathy (when he writes "let me walk through this")
- Simon Willison (curious, hyperlinked, thorough)
- Patrick McKenzie (Bits about Money, long unravellings)

These are the writers Stuart explicitly admires. When the voice drifts, return to them.

## The Tinkerer’s DNA

- Empirical Skepticism: If the manual says a system works one way, but the data (or the logic) says another, the Tinkerer trusts the machine.
- The "Long Unravelling": Much like Patrick McKenzie, they don't just give you a summary; they explain the plumbing of the financial or technical world so you can never be "tricked" by that system again.
- Pedagogy through Participation: Like Andrej Karpathy's "Let's build GPT from scratch" approach, the Tinkerer believes you don't truly understand a thing until you have assembled it yourself.
- The Hardware Soul: Following Bunnie Huang, they see "black boxes" as an invitation or a challenge, not a boundary.

## Why this Archetype Matters

In a world of increasingly opaque AI and "magic" software, The Tinkerer is the person who keeps us grounded in reality. They are the bridge between "It just works" (consumerism) and "Here is why it works" (mastery).
Are you looking to adopt this persona for a specific project, or are you building out a curated list of "Tinkerers" to follow for a specific field?

## Two registers

| Register | Where it lives | Distinguishing shape |
|---|---|---|
| **Tinkerer** | `@KnowMoreContext`, helioy.com/blog, dev.to, long threads, launch posts | Layered revelation. Evidence first. Conclusion may open more questions. |
| **General** | `@HelioyMatters` product posts, replies, build logs, casual LinkedIn, observations on releases | Shorter, more direct, still evidence-rich. The Tinkerer rules apply, the layered structure relaxes. |

Both share the foundation below. Pick by surface and depth.

## Foundation (both registers)

### Mode

- **Precise.** Every word is chosen.
- **Careful.** Claims are backed before they are made.
- **Open.** Invites the reader into a question rather than handing down a conclusion.
- **Curious.** Reaches for "what is actually happening here" before "what should be done about it."

Conversational rhythm is a tool, not the mode. Contractions, sentence fragments, and ellipsis for pauses are devices that serve precision, not signs of casualness. The voice reads like someone thinking out loud with care.

### Tone

- Direct but warm. Not cold, not dismissive.
- Wants conversation, not followers.
- Skeptical without being cynical. Calls things out, generous toward people doing real work.
- Frustrated by distractions from real problems, never frustrated at humans.
- Positive intent. The work is to make things better.

### Pronouns and framing

- **"I"** for personal observation and practice. "I went looking." "I noticed something."
- **Name specific groups directly** when discussing third parties: "most users," "Claude Code," "the docs," "the official prompt." Do not say "we" when "we" would mean "we the crowd participating in current discourse."
- **"We"** is allowed only when it refers to a concrete group Stuart belongs to ("we built a harness" referring to actual collaborators) or to humanity broadly ("we are primed for interaction"). Never "we obsess over...", "we talk about...", "most of us...". Stuart does not belong to the trend; he has his own takes.
- **"You"** is allowed sparingly to address the reader directly. Never in instruction mode. "Here is something to consider" beats "you should consider this."

### Density principle

Less is often more, but not always. Sometimes careful deliberation and thoughtful delivery call for length. The rule is that every sentence earns its place. Cut what does not. Keep what does, even if the result runs long.

### Verification (no unverified claims, ever)

Every assertion must be verifiable. If a claim cannot be backed by a screenshot, a log, a token count, an exact env var, a reproducible step, a quote from a primary source, or first-person practice ("I watched this happen"), the claim does not go in.

This applies to claims about:

- The state of the discourse ("everyone is talking about X", "nobody is doing Y") — these are landscape claims that almost always overreach
- What official docs do or do not show — verify by looking, do not infer
- What other tools or competitors do — verify by running them, do not infer from marketing
- What "most users" do or see — group-naming is fine when descriptive, not when it imports an unverified behavioral claim
- Historical timelines ("for years", "since 2023") — pin the date or remove the claim

Default move when tempted to make a sweeping claim: replace it with a concrete observation Stuart can show. "I started watching my own sessions on the wire" is verifiable. "Most users never look at this" is not, unless there is a survey or a practice Stuart can point to. Drop the unverifiable half of the sentence and keep only what can be shown.

The cost of a verified-but-narrow claim is lower than the cost of an unverified-but-sweeping one. Stuart loses credibility on the second; the first reads as careful.

### Anti-slop (hard rules, codified in CLAUDE.md)

These are policed ruthlessly. Each is a regression to fix on sight.

- No em dashes. Use a period, a comma, a colon, or an ellipsis.
- Rarely hyphens. Correct punctuation, not faked emphasis.
- No parallel-contrast constructions. "It is X, not Y" or "Not X, but Y" is slop.
- No negation framing as rhetorical device. "This is not X. This is Y."
- No trailing response summaries. The reader sees the work; do not narrate it back.
- No performative openings. "I hit a wall nobody is talking about", "Here is what nobody tells you."
- No press release voice. "We're excited to announce..."
- No hedging that softens the core claim. "It might be worth considering..."
- No performed humility. "I'm no expert, but..."
- No clickbait or thread-bait. "A thread 🧵."
- No anticipation closers. "I will share more this week", "Sharing what I find", "Stay tuned", "Coming soon", "More on this later" are all forbidden. Either deliver the thing or do not post. If you do not have it ready, wait until you do.
- No hashtag spam. Zero or one, only when genuinely useful.
- No more than one emoji per post, and only if it adds meaning.
- No purposeless parallelism. "Every X does Y. Every Z does W."
- No colon-punchline constructions. "The thesis is simple: ..."
- No triads as rhetorical devices.
- No corporate framing. "In an era of..."
- No superiority framing. "Everyone is doing X, nobody is doing Y." Stuart probes; he is not above the crowd.

## The Tinkerer register

Used for technical revelation content. The reader is invited along on an unravelling. Each paragraph adds one observation. The reader walks alongside Stuart and arrives at the conclusion themselves.

### Rules

1. **Inquisitive, not declarative.** Hooks are questions or quiet observations. "What does Claude Code actually send when you ask it to read a file?" beats "Claude Code is sneakier than you think."
2. **Layers of revelation.** The structure is unravelling, not announcing. Each paragraph adds one thing.
3. **No bold claims without evidence.** Every assertion is backed by a screenshot, a token count, an env var, an exact prompt, or a reproducible step. If you cannot show it, do not claim it.
4. **Conclusions may open more questions.** "And now I am wondering..." is a stronger ending than "And that is why X."
5. **No clickbait, no marketing register.** Reads like a researcher's blog, not a thread-bro tweet.
6. **First-person used sparingly and concretely.** "I went looking and found..." is fine. "I believe..." is too soft. "You should..." is too direct.

### The hierarchy argument

```
prompt engineering    ← what most attention goes to
context engineering   ← the middle layer (cm and am operate here)
transport layer       ← the foundation (Transport Matters operates here)
```

The argument that anchors the editorial position: prompt engineering sits on sand if the transport layer is invisible. The reader arrives at this through evidence, never through assertion.

### Closing taglines

- **Token matters.** Singular. The editorial close.
- **Every token counts.** The Helioy ecosystem tagline.

Both are valid. Use sparingly. Always at the end, never as a header. Never every post.

### Wrong → Right calibration

The voice was corrected on 2026-04-28 from a polemical register to the Tinkerer register. These pairs anchor the calibration:

| Wrong (polemical, rejected) | Right (Tinkerer, accepted) |
|---|---|
| "The industry is doing context work blind" | "I started watching what flows over the wire, and I keep finding things I did not expect" |
| "Transport Matters fixes the foundation" | "Once you can see the bytes, the rest of the conversation about prompts looks different" |
| "You cannot leverage the models without ground-floor access" | "Here is something I noticed. What do you make of it?" |
| "Claude Code is sneakier than you think" | "What does Claude Code actually send when you ask it to read a file? I went looking." |
| "We talk about prompts. We talk about context." | "Prompt engineering gets a lot of attention. The rest of the request gets less." |

## The general register

Used for replies, build logs, casual takes, observations on industry releases, conversational LinkedIn posts. Shorter, more direct, still evidence-rich. The Tinkerer rules above all still apply. The layered-revelation structure relaxes: a reply can be a single observation, a build log can be three sentences.

### Surface mapping

| Surface | Default register |
|---|---|
| `@KnowMoreContext` originals and threads | Tinkerer |
| `@KnowMoreContext` quote-RTs and replies | General (Tinkerer-flavored) |
| `@HelioyMatters` product posts | General (evidence-rich, more direct) |
| helioy.com/blog essays | Tinkerer |
| dev.to cross-posts | Tinkerer (canonical on helioy.com) |
| Substack newsletter pieces | Tinkerer |
| LinkedIn long-form | Tinkerer |
| LinkedIn casual posts | General |
| Any reply | General |

## Examples to study

This document will accumulate links to specific posts as the voice produces them. For now, the lineage models above are the calibration. Read them when the voice drifts.

## Correction log

Voice evolves through corrections. Each entry captures what was rejected, what was accepted, and the pattern.

### 2026-03-28: Recursive trap post

- **Rejected**: "I hit a wall nobody is talking about" — performative content-creator voice.
- **Rejected**: "This isn't a workflow inconvenience. It's a fundamental bootstrapping challenge." — negation framing.
- **Accepted**: Direct technical prose without rhetorical flourishes. State the problem plainly. Let the insight carry itself.
- **Pattern**: When Stuart says "ignore my voice... let's be real" the draft is too polished. Strip the rhetoric. Write like an engineer explaining something to another engineer.

### 2026-04-28: Tinkerer register established for Transport Matters launch

- **Rejected**: "The industry is doing context work blind. Transport Matters fixes the foundation. You cannot leverage the models without ground-floor access to the bytes on the wire." Too direct, polemical, clickbait-adjacent.
- **Accepted**: Layered revelation. Inquisitive. Evidence first, then quiet observation. Conclusions may open more questions. Walk the reader through what was noticed.
- **Pattern**: Stuart said "I would not be so direct... I do not make bold click bait claims... I invite curiosity... no claims are made w/o thorough evidence to back it up... it's a journey, an unravelling, and the conclusion may well lead to more curiosity." Persona named: The Tinkerer. Lineage confirmed: Bunnie Huang, Karpathy when explanatory, Simon Willison, Patrick McKenzie.

### 2026-04-28: "We" usage narrowed

- **Rejected**: "We talk about prompts. We talk about context." Implies belonging to discourse, which Stuart explicitly rejects.
- **Accepted**: Direct subject naming ("Prompt engineering gets attention") or first-person observation ("I went looking").
- **Pattern**: Stuart said "I don't like the use of 'We' who are we... I'm not with the crowd I have my own takes... I don't interact with we or with whatever the current trend is." "We" only allowed for concrete groups Stuart belongs to or for humanity broadly.

### 2026-04-28: Tagline precision

- **Rejected**: "Tokens matter" (plural).
- **Accepted**: "Token matters" (singular). Companion to "Every token counts." Both valid, used sparingly.
- **Pattern**: Singular is intentional. Both taglines go at the end, never mid-piece, never every post.

### 2026-04-28: "Informal grammar" replaced with conversational precision

- **Rejected**: Characterizing the voice as having "informal grammar."
- **Accepted**: The voice has conversational rhythm (contractions, fragments, ellipsis) but the mode is precise, careful, curious. Conversational tools do not equal informality.
- **Pattern**: Stuart said "Precision is important... being precise, careful, open with a desire for clarity. Curious in nature." The voice is a precise mind speaking out loud, not a casual one being chatty.

### 2026-04-28: Less is more is not a hard rule

- **Rejected**: Treating brevity as an absolute rule.
- **Accepted**: Density principle. Every sentence earns its place. Sometimes that means short. Sometimes thoughtful delivery calls for length. Cut what does not earn its place; keep what does.
- **Pattern**: Stuart said "less is more is not a hard rule .. sometime careful deliberation and thoughtful delivery is equally important."

### 2026-04-28: No anticipation closers

- **Rejected**: "Sharing what I find this week."
- **Accepted**: End on the observation or the personal practice anchor. No promise of future content.
- **Pattern**: Stuart said "either share or shut up." Anticipation closers tease without delivering. They read as content-creator hustle. Either the post has the thing, or the post does not get sent. When the next thing is ready, it ships on its own without needing a prior post to warm it up.

### 2026-04-28: No unverified claims, ever

- **Rejected**: "Prompt engineering gets attention. Context engineering is starting to." Dated and untrue (context engineering has been a focal point for years), and reads as if Stuart just discovered context engineering.
- **Rejected**: "More than the official prompt the docs show." The docs may or may not show the full prompt; this was inferred, not verified.
- **Accepted**: Replace landscape claims with concrete observations Stuart can show. "I started watching my own sessions on the wire" beats "most users never look." Date-pin or drop any historical claim ("for years", "since 2023").
- **Pattern**: Stuart said "we not using the skill here so we not verifying claims this is all about my-voice ... don't make unverified claims!" Verification is a foundation discipline, not just a Tinkerer rule. Every claim survives the test "can I show this if asked?" before it ships.

## How this document evolves

Stuart provides writing, or corrects drafts. Patterns get added to the correction log. Examples accumulate as links. The doc follows reality, never leads it.

---
title: KnowMoreContext X Profile, Cold-Start Playbook (May 2026)
type: research
tags: [knowmorecontext, x-twitter, profile-design, bio, cold-start, ai-creator, tinkerer-voice, my-voice]
summary: Deep-research deliverable for setting up @KnowMoreContext on X. Bio patterns that work for new technical accounts in AI, anti-pattern catalogue, eight bio drafts in Tinkerer voice, pinned-post recommendation, avatar and header concepts, verdict on naming Helioy in the bio.
status: active
source: deep-research
confidence: high
created: 2026-05-03
updated: 2026-05-03
related: [context-engineering-landscape-x-presence-april-2026]
---

## Brief

Cold-start playbook for `@KnowMoreContext`, a new X account by Stuart Robinson. Mission: GitHub repo reviews, industry teardowns, peeling back layers of AI tooling, actionable technical insights. Tinkerer register. Lineage models: Bunnie Huang, Karpathy in explanatory mode, Simon Willison, Patrick McKenzie. Account is deliberately separate from `@HelioyMatters` (the Helioy product surface).

Companion file: `context-engineering-landscape-x-presence-april-2026.md` (the landscape this account is entering).
Voice document: `~/.mdx/reference/my-voice.md`.

## Methodology Note

Researcher attempted to fetch live X profiles for the lineage models (Bunnie, patio11, Simon Willison, b0rk) and other Tier 2 builders. X.com returned 402 (paywalled API), Nitter and Wayback are blocked from this environment. Worked around via search snippets, third-party profile aggregators (Sotwe, Instalker, Favikon), and personal "About" pages. Where a bio is verbatim, it is quoted; where only paraphrase was available, it is labeled. Two specifics not verified: Bunnie Huang's exact current X bio, and Simon Willison's exact current X bio (only paraphrase via search snippet: "creator of @datasetteproj and co-creator of Django, serves on the PSF board"). All other bios in this report are verbatim from search snippets that quote the bio text directly.

---

## A. The Five Strongest Bio Patterns

### Pattern 1: The Verb-In-Progress

**Shape:** Present-participle verb phrase describing the work, no credentials, no claim of expertise. The sentence is the work itself.

**Examples:**
- `@vikhyatk`: *"teaching computers how to see"* (link to @moondreamai)
- `@_xjdr`: *"building AI that wont embarrass me in front of my own standards"* (link to noumena.com)

**When to use:** When the work has a clear, sensory verb that captures what the account is for. Best when the verb is unusual or specific (teaching computers to see > "building AI tools"). Reads as a person at a workbench rather than a personal brand.

**When to avoid:** When the verb is generic ("building AI", "exploring agents") because every account uses those. The verb has to do real work or the pattern collapses into beige.

**Why it lands for Tinkerer register:** Inquisitive in posture. There is no claim of arrival, just a description of what is currently being attempted. Maps directly to Karpathy's "let's build" lineage.

### Pattern 2: The Single-Sentence Aboutness

**Shape:** One declarative sentence naming the subject domain. No "I", no role, no employer. The bio is the topic the account covers.

**Examples:**
- `@b0rk` (paraphrase from search): *"programming and exclamation marks"* (pronouns + zines link)
- `@kwindla`: *"Infrastructure and developer tools for real-time voice, video, and AI."*

**When to use:** When the topic is genuinely narrow. Works best when paired with a strong avatar and a clear pinned artifact, because the bio carries no biographical signal on its own.

**When to avoid:** When the topic is the same topic 10,000 other accounts list. "AI agents" or "context engineering" as a single-sentence bio in 2026 reads as cargo-culting the discourse.

**Why it lands:** The reader's job is "what will this account give me?", not "who is this person?". A topic-only bio answers that question and gets out of the way. Patrick McKenzie's *Bits about Money* operates the same way at the publication level: title is the bio.

### Pattern 3: The Stack Identity (Slash Stack)

**Shape:** Identity tokens separated by `·` or `|` or `/`. Each token is a chunk: role, employer, prior employer, side project, location.

**Examples:**
- `@dexhorthy`: *"building the post-IDE IDE at hlyr.dev/code · @aitinkerers sf lead, prev · @replicatedhq · @SproutSocial · @nasa · ai that works pod @ hlyr.dev/aitw · San Francisco, CA"*
- `@eugeneyan`: *"Field ⇔ Frontier · @AnthropicAI. Prev: Principal Applied Scientist @ Amazon, led ML @ Alibaba, Healthtech."*
- `@karpathy`: *"Building @EurekaLabsAI. Previously Director of AI @ Tesla, founding team @ OpenAI, CS231n/PhD @ Stanford. I like to train large deep neural nets."*
- `@dabit3`: *"devrel + dx @eigenlayer @eigen_da @eigen_labs // react, ai, & onchain // prev @avara @celestiaorg @awscloud // 🫂 @developer_dao"*

**When to use:** When you have credentials people would recognise and want them upfront. This is the "I am loaning you my reputation by association" pattern.

**When to avoid:** **For a cold-start account it almost certainly works against you.** Stack-identity bios assume the reader recognises the @-handles. With no priors and no follower count to suggest the bio is worth parsing, the reader bounces. It also breaks the Tinkerer rule against superiority framing if the brands listed read as flex.

**Verdict for `@KnowMoreContext`:** Avoid. The account is starting cold and is not connected to the named ecosystem (deliberately separate from @HelioyMatters). Stack identity loans a brand that is not yet built.

### Pattern 4: The Working-Method Bio

**Shape:** A short description not of who you are but of how you work or what you do daily. The bio is procedural.

**Examples:**
- `@HamelHusain`: *"Evals evals evals evals.info About Me: hamel.dev · Looking at the data evals.info"* — the bio is the practice.
- `@abacaj`: *"Code & LLMs"* — pure topic-tokens, but functions as method-statement (this is what I look at).

**When to use:** When the practice is distinctive. Hamel's bio works because evals are his actual obsession and he repeated it three times to make the point. The repetition is doing rhetorical work, not filler.

**When to avoid:** When the practice is not yet visible in the work. Saying "deep code reading" before there is a corpus to back it makes the bio a promise, not a description. The Tinkerer voice rejects promises.

**Why this might land for Stuart:** Closest match to "I read repos line by line" framing, but only after there is a body of teardowns to back it. The first version of the bio cannot lead with this pattern because the work is not yet there to show.

### Pattern 5: The Inverted Question

**Shape:** A short question or quiet observation that the account is in the business of answering. The bio names the discipline indirectly by naming the curiosity.

**Closest analogues:** `@_xjdr`'s bio operates in the spirit (a quiet self-assessment of the standard the work has to clear). Dan McKinley's old blog bio used to read along the lines of "writing about the internal life of software" (paraphrase). The pattern shows up more in long-form bios on blog `/about` pages than on X.

**When to use:** When the question is genuinely the author's question. If the question is performative, it dies on contact with anyone who can smell rhetoric. If the question is one Stuart actually keeps asking, it works.

**When to avoid:** Almost always, on X bios specifically. The pattern is rare on X because X bios reward density. A question takes up real estate without clearly labelling the account. Better lived in pinned posts and headers.

**Verdict for `@KnowMoreContext`:** Highest-risk-highest-reward pattern. Most distinctive bio in the Tinkerer register but easiest to misread as performative. Worth one draft to test.

---

## B. Anti-Pattern Catalogue

| # | Anti-pattern | Example shape | my-voice rule violated | Why it fails for Tinkerer |
|---|---|---|---|---|
| 1 | The Promise Bio | "Helping engineers ship better AI." | Press release voice; superiority framing. | Promises a service the reader did not ask about. Reads as marketing. |
| 2 | The Manifesto Bio | "AI is broken. I'm here to fix it." | Performative opening; negation framing; superiority framing. | Sets you up as the corrective hero. Tinkerer is curious, not corrective. |
| 3 | The Triad Bio | "Builder. Writer. Investor." | Triads as rhetorical device; corporate framing. | Triads are the X bio cliché of 2023-2024. Instantly reads as low-effort. |
| 4 | The Coming-Soon Bio | "Building something new in AI 👀 follow for updates" | Anticipation closers; clickbait; performed humility. | Asks for a follow on credit. Tinkerer does not ask, it shows. |
| 5 | The Daily-Dose Bio | "Daily threads on AI, agents, and context engineering 🧵" | Hashtag/symbol spam; clickbait. | Threadbro signal. Repels the audience that follows Simon Willison. |
| 6 | The Hierarchy Bio | "Most engineers don't understand X. I do." | Superiority framing; parallel-contrast; negation. | The Tinkerer never positions above the crowd. Stuart probes. |
| 7 | The Colon-Punchline Bio | "The thesis is simple: context is everything." | Colon-punchline construction; press release voice. | Tries to land a beat in a static field. Lands flat. |
| 8 | The Hedged Bio | "I think AI tools are interesting and might write about them sometimes." | Hedging; performed humility. | Tinkerer is direct about what it does. Hedging reads as fear. |
| 9 | The Buzzword Salad | "AI / agents / context engineering / harness engineering / RAG / MCP" | No purposeless parallelism rule; topic stuffing reads as SEO. | Reads as a content-marketing keyword cluster. Burns trust on first scan. |
| 10 | The Influencer Bio | "1.2M views/mo. 50K followers. Builder of XYZ." | Superiority framing; press release voice. | Vanity metrics in a bio with zero followers signals desperation, not authority. |

The pattern across all of these: they ask the reader for something (follow, click, trust, attention) before the reader has any reason to give it. The bios that work in the Tinkerer register do the opposite. They describe the work and let the reader decide.

---

## C. Eight Bio Drafts for `@KnowMoreContext`

Each is under 160 chars. Each is in the Tinkerer register. Each takes a different structural shape. None re-uses the three weak first-pass drafts ("What is this repo actually doing? I read line by line...", "I read repos line by line and peel back...", "Repo teardowns and release peelings.").

Each has been run through the my-voice hard-rule list (no em dashes, no "X, not Y", no negation framing, no triads, no anticipation closers, no colon-punchline, no superiority framing, no hashtag spam, max one emoji, no performative opening, no press release voice, no hedging).

### Draft 1 — Verb-In-Progress (Vikhyatk shape)

**Bio:** `reading AI repos with the docs closed`

**Chars:** 35.

**Shape:** Pattern 1. A single present-participle phrase. Sensory verb (reading) plus a small constraint that signals method (with the docs closed).

**Why it might land:** The constraint does the work. "Reading repos" is a generic claim. "Reading repos with the docs closed" tells the reader you trust the source over the documentation, which is the Bunnie Huang stance. Short enough that the avatar and pinned post will carry the rest of the load.

**Risk:** The brevity may read as too cute on first scan. Mitigated if the pinned post is a long, dense teardown that earns the brevity.

### Draft 2 — Single-Sentence Aboutness (b0rk shape)

**Bio:** `notes from the inside of AI tooling`

**Chars:** 35.

**Shape:** Pattern 2. Topic-only declaration. No "I", no role, no employer.

**Why it might land:** Names the account's editorial stance (inside view, notes form) without claiming expertise. The word "inside" carries the whole argument. Maps to Patrick McKenzie's "Bits about Money" naming convention applied to a different domain.

**Risk:** "AI tooling" is a crowded category label. The word "inside" has to carry weight against that.

### Draft 3 — Working-Method Bio (Hamel shape)

**Bio:** `repo first. release notes second. docs last. writing what I find.`

**Chars:** 65.

**Shape:** Pattern 4. States the working method as an ordering. The four sentence-fragments form a procedural sequence.

**Why it might land:** Tells the reader exactly what they are signing up for. The ordering is a quiet claim against the dominant "summarise the docs and the announcement" pattern in AI Twitter. "Writing what I find" closes on the empirical-skepticism note without naming it.

**Risk:** The ordering uses three short phrases plus a fourth, which is borderline-triad. The asymmetric fourth phrase saves it from the triad rule, but if it lands wrong drop it.

### Draft 4 — Inverted Question (no clean precedent)

**Bio:** `what is this AI repo actually doing? going in to find out, writing down what's there`

**Chars:** 86.

**Shape:** Pattern 5. The question is the bio. The follow-up describes the practice that answers it.

**Why it might land:** Closest the bio register can get to the Tinkerer voice's signature move. The question opens, the second clause shows the practice, no conclusion is offered.

**Risk:** Higher than the others. A bio that opens with a question can read as bait.

### Draft 5 — Tool-and-Eye Bio

**Bio:** `tools, repos, and releases in AI. read carefully, written down`

**Chars:** 62.

**Shape:** Topic clause followed by method clause.

**Why it might land:** "Read carefully, written down" is the clearest single-line description of the Tinkerer practice in this character budget. Signals depth without making a claim of depth.

**Risk:** "Tools, repos, and releases" risks parallel-triad. "Read carefully" risks performed humility. Mitigated by the bluntness of "written down".

### Draft 6 — Place-and-Time Bio

**Bio:** `at the workbench with whatever AI tool shipped this week`

**Chars:** 56.

**Shape:** Spatial-temporal anchor (workbench, this week) describing what the account is doing right now.

**Why it might land:** "Workbench" is the strongest single word in the Tinkerer vocabulary. Evokes Bunnie Huang directly. "Whatever shipped this week" signals current, hands-on, not curated. Describes a posture rather than a topic.

**Risk:** "This week" implies a cadence the account may not always hit. Stuart should only use this if posting cadence will be at least weekly.

### Draft 7 — The Field-Notes Bio

**Bio:** `field notes on AI tools. what the repo shows, what the release ships, what the layers underneath are doing`

**Chars:** 108.

**Shape:** Genre label (field notes) followed by three concrete things the account documents. The three are deliberately structured as parallel objects of observation.

**Why it might land:** "Field notes" is the genre tag that connects directly to Julia Evans, Bunnie Huang, and Simon Willison's posture. The three concrete observation-objects spell out the layers metaphor.

**Risk:** Closest to the triad rule of any draft. The parallel construction is descriptive (three different objects of observation) rather than rhetorical (three synonyms for emphasis), which reads as on the right side of the rule. If Stuart reads it as triadic, drop it.

### Draft 8 — The Bare Genre Bio

**Bio:** `AI repo teardowns. release autopsies. reading what shipped`

**Chars:** 58.

**Shape:** Two genre labels and a method clause. Each label is a noun phrase that names a kind of artifact the account produces.

**Why it might land:** "Teardowns" and "autopsies" both come from outside AI vocabulary (hardware, medicine) and pull the account out of the AI-bro lexicon. Concrete enough that the reader can predict what a post will look like.

**Risk:** "Autopsies" might be too dramatic for some readers. If it lands as edgy, swap to "release notes that read the actual release". If it lands as accurate, keep it.

---

## D. Pinned-Post Recommendation

A new account has no track record, which means the pin has to do double duty: prove the account's value in one click, and stand up to the inevitable scroll-by from someone who clicked the bio.

Patterns observed in the lineage:

- **Karpathy's pinned post:** *"The hottest new programming language is English"* — a single observation, no thread, no link. It works because Karpathy is Karpathy. A new account cannot run this play.
- **Dex Horthy's pinned (per Y Combinator post snippet):** A curated superthread of resources on coding agents and context engineering. Works because it concentrates value in one place; reader gets a library on first click.
- **Simon Willison style:** A specific demo or release announcement, frequently rotated.

For a cold-start account whose unique value is depth-of-investigation, the pinned post should be **a single complete teardown of one well-known repo**, posted as a thread, with the post anchored on a concrete finding the reader can verify.

**Concrete proposal:** Pick one repo from the context-engineering landscape that has high recognition and is widely linked-but-rarely-read. Strong candidates from the landscape file: `langchain-ai/deepagents`, `humanlayer/humanlayer`, `letta-ai/letta`. Read it line by line. Write a thread that walks through one specific architectural decision the reader would not learn from the README. Each post in the thread shows code, not paraphrase. The final post does not promise the next teardown, it ends on the observation and a question that the reader can sit with.

The pin is then an ongoing demonstration of what the account does, not a promise of what it will do.

**Format notes:**
- 8 to 14 posts is the realistic range. Shorter and the depth claim is unproven. Longer and the thread loses its skim shape.
- Code screenshots over text quotes for early posts; the visual signals "I actually opened this" in a way prose cannot.
- One image per post in the meaty middle; a clean text close at the end.
- No "🧵" emoji opener. No "1/" numbering of posts. The thread shape is its own signal on X.

---

## E. Profile Companion Elements

### Account name capitalisation

X display names are case-flexible. Three options:

1. `KnowMoreContext` — single PascalCase token. Reads as a slogan compressed into a name. Closest to the brand-as-statement convention used by Helioy products.
2. `Know More Context` — three words with spaces. Reads more declarative, more readable in feeds, but loses the lockup quality.
3. `know more context` — lowercase. Reads as quiet, deliberate. Connects visually to `@b0rk` and `@simonw` which both lean lowercase.

**Recommendation:** `KnowMoreContext` for the display name. The handle `@KnowMoreContext` already commits to that capitalisation, so display-name consistency is the lowest-friction choice. The lowercase variant is a strong second if Stuart wants to lean further into the careful-and-quiet register.

### Handle hygiene

`@KnowMoreContext` is 16 characters, well under the 15-cap-on-display-name threshold. Pronounceable, parseable, and signals an editorial stance (more context, please). One concern: the handle is also a parseable English imperative ("know more context"), which means it will sometimes get read as a command rather than a name. This is fine for the Tinkerer voice, which tolerates imperative posture when it points at the work.

### Avatar concept

Three directions, ranked by fit:

1. **A workbench fragment.** A close-up photograph of a corner of a workspace: a notebook page with handwritten margin notes, or a terminal showing `git log --oneline` of an unfamiliar repo. Signals the Tinkerer practice on first glance. Closest visual analogue: Julia Evans's hand-drawn zine aesthetic, but photographic rather than illustrated.
2. **A glyph or wordmark.** A single typographic mark. Lower-effort than option 1, harder to make distinctive. Risks looking like every other AI account.
3. **A face.** A portrait. Maximum trust signal, lowest distinctiveness. Works well on accounts where the person is the brand (Karpathy, Patrick McKenzie). For an account that is deliberately separate from the founder identity, this fights the framing.

### Header image concept

The header is the account's only chance to do prose on the profile page itself. Options:

1. **A code excerpt on a flat background.** A 6 to 10 line snippet from a real repo, with one line annotated by hand. Signals the practice in seconds. Risk: dates fast; need to commit to refreshing it monthly.
2. **A long-form quote of the account's editorial stance.** A single sentence describing the practice, rendered as type. Reads as a manifesto and may break the no-press-release-voice rule depending on copy.
3. **A diagram.** A hand-drawn or hand-feel diagram showing the layers of an AI tool stack (UI, harness, model, transport, etc.) with the account's gaze annotated as "we are here". Connects to the hierarchy argument in `my-voice.md` without overstating it.

**Recommendation:** Option 3. The hierarchy diagram is the single most powerful editorial frame in `my-voice.md` (prompt > context > transport). A header that visualises this argument quietly, without text labels claiming authority, sets up everything the account will post against. Rendered in a hand-feel style (not Figma-clean) it reinforces the Tinkerer aesthetic.

---

## F. The "Should We Mention Helioy" Verdict

**Verdict: Do not mention Helioy in the bio. Argued from evidence below.**

The question is whether linking the account to its parent ecosystem helps or harms its first impression. Three lines of evidence:

**1. The Tier 2 cold-start cases that grew from work-credibility, not affiliation, hide affiliation.**

`@vikhyatk` ("teaching computers how to see") does not name his employer in the bio's lead. The Moondream link is in the bio but it functions as a portfolio link, not an identity claim. Similarly `@_xjdr` has no employer in the bio at all, only a personal site link. Both grew during 2024-2025 on the strength of their published work.

The accounts that lead with affiliation (`@dexhorthy`, `@karpathy`, `@eugeneyan`) are using affiliation as social proof for a reader who already recognises the affiliations. None of them grew from cold-start with that pattern; the affiliations were already valuable when they put them in the bio.

**2. Helioy is itself a cold brand for the audience this account targets.**

The audience Stuart wants is the Simon Willison / Birgitta Bockeler / Hamel Husain reader. Naming Helioy in the bio uses a character budget on a brand that the target audience does not yet recognise. The same characters spent on a description of the practice signal more.

**3. The two-account architecture is deliberate separation.**

Stuart already runs `@HelioyMatters` as the product surface. The existence of a separate `@KnowMoreContext` account communicates that this account is not the product channel. Mentioning Helioy in the bio undercuts that separation, makes the account look like a satellite marketing channel for Helioy, and risks the account being filed as "founder content for [unfamiliar product]" rather than as a standalone editorial voice.

**Counter-argument considered:** Once Helioy is well-known (post-Transport Matters launch in April 2026, possibly beyond), naming Helioy in the bio could function as social proof in the way affiliations work for Tier 2 builders today. Future-state argument. Does not apply to the cold-start phase.

**Practical recommendation:** Keep Helioy out of the bio at launch. Add it later (12 to 24 months in, or after a clear inflection moment) only if Helioy has by then become a recognisable brand name to the target reader.

---

## Cross-Reference: How These Patterns Map to the Drafts

| Draft | Pattern | Closest precedent | Risk profile |
|-------|---------|------------------|--------------|
| 1. reading AI repos with the docs closed | Verb-in-progress | @vikhyatk | Low-medium |
| 2. notes from the inside of AI tooling | Single-sentence aboutness | @b0rk, Bits about Money | Low |
| 3. repo first. release notes second. docs last. | Working-method | @HamelHusain | Medium |
| 4. what is this AI repo actually doing? going in to find out... | Inverted question | (no clean X precedent) | Highest |
| 5. tools, repos, and releases in AI. read carefully... | Topic-then-method hybrid | @kwindla | Low-medium |
| 6. at the workbench with whatever AI tool shipped this week | Place-and-time | (Bunnie Huang in spirit) | Medium |
| 7. field notes on AI tools. what the repo shows... | Field-notes / Stack-method hybrid | (Patrick McKenzie / Julia Evans hybrid) | Medium-high (triad-edge) |
| 8. AI repo teardowns. release autopsies. reading what shipped | Bare-genre | (closest to bunniestudios's posture) | Medium |

---

## Sources Consulted

### X profile bios verified verbatim via search snippets
- `@dexhorthy` — bio quoted in Y Combinator profile aggregator: https://x.com/dexhorthy
- `@_philschmid` — bio quoted in Favikon profile: https://www.favikon.com/blog/who-is-philipp-schmid
- `@birgitta410` — bio quoted in Bluesky cross-post: https://bsky.app/profile/birgitta410.bsky.social
- `@karpathy` — bio quoted in twtdata.com aggregator: https://twtdata.com/karpathy/
- `@eugeneyan` — bio via search snippet citing X profile: https://x.com/eugeneyan
- `@dabit3` — bio quoted in Sotwe aggregator: https://www.sotwe.com/dabit3
- `@reach_vb` — bio quoted in HuggingFace cross-bio: https://huggingface.co/reach-vb
- `@kwindla` — bio quoted in profile aggregator: https://x.com/kwindla
- `@vikhyatk` — bio quoted via Crunchbase + X: https://www.crunchbase.com/person/vik-korrapati
- `@_xjdr` — bio quoted via X snippet: https://x.com/_xjdr
- `@HamelHusain` — bio via X snippet: https://x.com/hamelhusain
- `@abacaj` — bio via X snippet: https://x.com/abacaj
- `@DanielMiessler` — bio quoted via X profile snippet: https://x.com/DanielMiessler
- `@addyosmani` — bio via X profile snippet: https://x.com/addyosmani
- `@latentspacepod` — bio via Latent.Space about page: https://www.latent.space/about
- `@ID_AA_Carmack` — bio via aggregator: https://twicopy.com/ID_AA_Carmack/
- `@ben11kehoe` — bio via X snippet: https://twitter.com/ben11kehoe
- `@thorwebdev` — bio via X snippet: https://x.com/thorwebdev

### Lineage-model `/about` pages
- Simon Willison: https://simonwillison.net/about/
- Patrick McKenzie (patio11): https://www.kalzumeus.com/about/
- Julia Evans: https://jvns.ca/

### Pinned-post and growth research
- Karpathy "hottest new programming language" pin: https://x.com/karpathy/status/1617979122625712128
- Dex Horthy superthread pin reference: Y Combinator post citing Dec 2025 pinned thread: https://x.com/ycombinator/status/1960033085078356148
- Threads vs single-post pinning: https://www.tweetarchivist.com/best-pinned-tweet-examples-guide
- Cold-start growth case studies: https://www.wisp.blog/blog/from-0-to-1000-followers-the-strategic-path-for-indie-hackers-on-twitter
- Indie hacker AI growth (Yaser/Chatbase): https://medium.com/@karthisclan/how-yaser-took-an-ai-app-from-0-to-1m-in-7-days-with-just-16-followers-6841e9b8ecc9
- AI Engineer audience reference: https://www.ai.engineer/about
- AI Tinkerers community context: https://aitinkerers.org/

### Stuart-supplied context
- `~/.mdx/research/context-engineering-landscape-x-presence-april-2026.md`
- `~/.mdx/reference/my-voice.md`

---

## Source Quality Assessment

**High confidence:** Bios for `@dexhorthy`, `@karpathy`, `@_philschmid`, `@birgitta410`, `@eugeneyan`, `@vikhyatk`, `@_xjdr`, `@HamelHusain`, `@kwindla`, `@DanielMiessler`, `@dabit3`, `@reach_vb`, `@ben11kehoe`. These are quoted verbatim by third-party search snippets that pulled the bio text directly.

**Medium confidence:** Pinned-post specifics. Dex Horthy's pinned thread is described in a Y Combinator post but the thread itself was not seen. Karpathy's pinned status of the "English" tweet was implied not confirmed by the search results. Pin-rotation patterns are sourced from secondary best-practice articles, not from observation of specific accounts over time.

**Low confidence / not verified:**
- Bunnie Huang's current X bio (X.com fetches blocked; search snippets did not surface verbatim bio text)
- Simon Willison's current X bio (only paraphrase available: "creator of @datasetteproj and co-creator of Django, serves on the PSF board")
- Julia Evans's current X bio (only paraphrase: "programming and exclamation marks" plus pronouns and zines link)

If verbatim versions of those three lineage-model bios become available through another route (e.g., a logged-in X session), they should be re-checked against this report's recommendations. None of the recommendations depend on those exact bios; they depend on the established editorial posture which is heavily documented elsewhere.

---

## Open Questions

1. Is there a planned content cadence for `@KnowMoreContext`? (Stuart-confirmed 2026-05-03: daily.) The bio drafts that mention "this week" should be updated to "today" or simply rely on observed cadence.
2. Does Stuart want to preserve the option to reveal his identity behind `@KnowMoreContext`, or is the account intended to operate as semi-anonymous like `@_xjdr`? (Stuart-confirmed 2026-05-03: identity-revealed via portrait avatar; the semi-anonymous option is closed.)
3. Is the inaugural pinned teardown going to be a public commitment (a known repo most readers can re-verify against) or a discovery-driven post (something Stuart found in a less-known repo that is genuinely surprising)? (Stuart-confirmed 2026-05-03: opening with the Claude Code "pins you to 1M" teardown adapted from `~/.mdx/blog/0010-claude-code-pins-you-to-1m.md`. Public commitment, high recognition.)

---

## Actionable Takeaways

1. **Pick a bio shape, not a bio sentence.** The five patterns are decision points. Once Stuart picks a shape, the wording is a small set of variations.
2. **Hold Helioy out of the bio.** Reconsider only if and when Helioy becomes a recognisable brand name to the target reader.
3. **The pinned post is the bio's proof.** A bio that promises depth without a pinned teardown to back it is a promise. A bio plus a pinned teardown is a description.
4. **Avatar over header for first-impression weight.** The avatar appears next to every reply; the header only shows on profile visits. Spend the visual budget there first.
5. **Resist the urge to optimise for follower growth.** The Tier 2 accounts that built durable reputations all built them slowly through a body of work. Accounts that grew fast on hooks and threadbait do not have the audience Stuart wants.

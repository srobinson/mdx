---
title: "Watching the wire"
slug: anchor-essay
status: review
account: knowmorecontext
surface: blog
type: deep-dive
created: 2026-04-30
updated: 2026-08-08
post_date:
post_url:
campaign: transport-matters-launch
related: [pinned-anchor, readafile-deepdive]
---

# Watching the wire

The prompt was seventeen characters long. I typed it into Codex in my terminal, pressed enter, and watched what left the machine.

The watching setup is small. mitmproxy sits between the agent and its provider, certificate trust in place, every request logged in full. Nothing about the agent changes. It makes exactly the calls it always makes. The only difference is that a copy of each request lands somewhere I can read it.

The request that carried my seventeen characters contained 107,480 characters of tool schemas. Sixty-four MCP tool definitions, serialized in full: names, long-form descriptions, JSON parameter schemas. Roughly 27,000 tokens of tool surface wrapped around a prompt shorter than this sentence. Most of the bulk is prose, the long descriptions that teach the model when and how to call each tool, and it is all there whether or not the turn will touch a single one of them.

One field in the same request explains why that number compounds. `store=false`. Codex asks the provider to retain nothing between calls. Whatever the model needs to know has to be present in the request, every time. So the 107,480 characters do not ship once at session start and settle in. They ride every call the agent makes, for as long as the session runs. A session that makes forty calls has shipped that payload forty times.

I sat with that ratio for a while. Seventeen characters of intent, six figures of scaffolding, resent per call. It surfaced a question I had never seriously asked about my own tools. What do I actually know about what a coding agent sends, and how much of it have I inferred from the chat surface it shows me?

## The request is flat

A coding agent presents itself in layers. There is the conversation you are having. There is the harness around it: the tools it can call, the project instructions it read, the hooks that fired at startup. There is whatever memory or context machinery the agent maintains between turns. The layers feel architectural when you use the thing.

The API contract underneath has no layers. Codex talks to a Responses endpoint: an `instructions` field, an `input` array, a `tools` array, sampling parameters. Claude Code talks to a Messages endpoint: `system`, `messages`, `tools`. That is the whole vocabulary. Everything the agent wants the model to know, from the identity preamble to the last tool result, gets flattened into those few fields before the bytes leave the process.

The wire is where the collapse happens, which makes it the one place you can see everything at once. Documentation describes the pieces one page at a time. The request body is the assembled thing, and every capture is a complete, self-contained record of what the model was actually given.

So I started reading captures the way I would read a core dump. Slowly, and with growing interest in the parts I did not recognise.

## Requests with no user behind them

The first surprise in a cold-start capture is how much traffic precedes the first prompt.

Start a fresh Claude Code session and watch the log. Before the first user message goes out, the harness fires a quota probe, a small request checking the account's limits. It also fires a title-generation turn: a separate model call whose job is naming the session. Two requests of billed model traffic, invisible from the terminal, complete before anything I typed had reached the wire.

Codex does the same dance with different steps. On session start it sends a prewarm request, then two requests from an internal memory agent. Model calls that appear nowhere in the visible transcript, doing work the interface never mentions.

None of this is sinister. A quota check is prudent, a session title is useful, a warm connection is faster. What struck me was narrower than suspicion. My mental model of the session was "it starts when I type." The capture log says the session starts earlier, involves more parties, and bills for turns I will never see rendered. The interface and the traffic describe two different systems.

## What arrives around your words

Then there is the first message itself.

In a Claude Code capture, the first user message is an array of content blocks, and the text I typed is rarely the first one. Ahead of it sits a `<system-reminder>` block carrying harness state: instructions, context, behavioural rules. Beside it sits the output of session-start hooks, injected as user content, indistinguishable on the wire from something I wrote.

The harness prompt is direct about the arrangement. It tells the model that user messages include reminders "appended by this harness," that these "are not from the user," and to "not mention them." That last clause is worth pausing on. The composition ships inside my channel, addressed to the model, with an instruction to keep it out of the conversation. The chat surface does not render these blocks, and the model is told not to bring them up. Both ends of the pipe agree to keep the middle quiet.

This is also why reading documentation is a different activity from reading captures. The vendors document the mechanisms, often thoroughly, spread across pages about hooks, memory, MCP, and system prompts. What no page shows is the composed result for this session and this loadout, byte for byte, in order. The wire is the only place that document exists.

## Editing as measurement

A proxy that can read a request can also rewrite it before it leaves. mitmproxy has supported this for years. Once I trusted my reading of the captures, editing became the obvious next experiment, because it turns observation into measurement. If I remove the parts I did not author, what does the provider bill?

I took one Claude Code exchange as the baseline. The provider's own usage accounting, input tokens plus cache-creation tokens in the response, put billed input at 46,624 tokens.

Then I edited the outbound request. Text trims on system blocks, including a long output-style section. Shortened descriptions across a dozen tools. The injected reminder blocks removed from the user message. One tool I never use dropped from the `tools` array entirely. Every edit targeted content composed by the harness. My own words, the tool results, and the conversation itself stayed untouched.

Billed input on the edited exchange: 39,102 tokens.

The first edited turn pays a toll worth knowing about. Providers cache long stable request prefixes, and an edit inside a cached region invalidates it, so the turn after an edit bills fresh cache writes rather than cheap cache reads. That is a one-turn cost. From the next turn on, the provider caches the edited prefix instead, and the smaller request becomes the steady state. The accounting for all of this sits in the same usage block, which is what makes the experiment clean. I am measuring with the provider's meter, in the provider's units.

That is 7,522 tokens, about sixteen percent of the request, that the provider metered and billed on a single exchange, all of it content I did not write and could remove without touching anything I had said or done. I want to be careful with the claim, because the numbers invite a bigger one. This measures one exchange, one loadout, one harness version, and it says nothing yet about whether the trimmed content was earning its keep in output quality. What it establishes is smaller and solid. The composition has a price, the price is visible in the provider's own accounting, and the wire is where you can run the experiment.

## The ground moved overnight

While I was doing this, Claude Code updated itself from 2.1.224 to 2.1.225. Overnight, as it does.

The next morning's captures of an equivalent session composed differently. The request shape had changed: blocks arranged differently, content revised, the assembled structure no longer matching the previous day's. I had changed no setting, installed nothing, edited no configuration. The captures themselves settle where the change came from. Each Claude Code request carries the harness version in a billing header, so the two days' captures are labelled 2.1.224 and 2.1.225 on their face, and the shape change pins cleanly to the release.

This reframed everything above. The composition is a moving target. It is owned by the harness release process, it revises on the vendor's schedule, and it ships silently in the sense that no surface I normally look at announced the request shape had changed. Anything keyed to yesterday's shape, an assumption or a measurement, was keyed to a request that no longer exists. The only way I knew the ground had moved was that I happened to have a capture from before and a capture from after.

Which, I think, is the honest answer to why this layer stays unexamined. The claim is structural. The chat surface renders the conversation and only the conversation. The injected blocks arrive with instructions to stay out of that conversation. The composition revises overnight without an announcement. Each piece of the system behaves reasonably on its own terms, and the combined effect is that the full request is invisible by default, changing on someone else's schedule, everywhere except on the wire.

## What I know now

A few weeks of captures moved a surprising number of my beliefs from inferred to observed, and falsified a few. I believed sessions started when I typed, that the user message contained what I wrote, and that my agent's requests were roughly stable day to day. Each belief was reasonable, surface-derived, and wrong in a way a single capture could show.

The method costs almost nothing. mitmproxy, a trusted certificate, an evening of reading. The agent behaves identically. The provider sees identical traffic. All that changes is that the composed request, the one document that says precisely what the model was given, becomes something you can open.

Seventeen characters in, 107,480 characters of scaffolding around them, on every call. I keep thinking about how I would ever have known that, without watching. And now I am wondering what the captures from the next release will show.

Token matters.

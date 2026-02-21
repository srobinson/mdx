---
title: "Watching the wire"
slug: anchor-essay
status: wip
account: knowmorecontext
surface: blog
type: deep-dive
created: 2026-04-30
updated: 2026-04-30
post_date:
post_url:
campaign: transport-matters-launch
related: [pinned-anchor, readafile-deepdive]
---

# Watching the wire

A few weeks ago I started watching what my coding agent sends over HTTPS when it does something simple, like read a file. I expected a small payload. The system message, the user turn, a tool call. What I found was longer. Much of it was not in any documentation I had read.

That first surprise sent me back to a question I had been avoiding: what do I actually know about how my agents work, versus what I have inferred from the surface they show me?

## A hierarchy nobody draws

Most agent work I see sits at the top of a stack. People shape prompts. They optimise retrieval. They squeeze context windows. They argue about the right way to format tool descriptions. The conversation is busy and the conversation is real, but it lives on a layer.

Below it sits the wire. The actual bytes the agent sends and receives on every turn. The envelope around the prompt. The tool calls in their precise schema. The cache control headers. The system message segments that the documentation hints at but rarely shows in full. The token counts per section, line by line.

Below the wire sits the model. That layer is sealed and not the one I am writing about.

So three layers, in order from the surface down: prompt, then context, then transport. Most attention lives on the top floor. The transport floor sits in the basement, dimly lit, doing the work everyone else assumes is correct.

## What the wire shows that the docs cannot

A few things I have watched in mitmdump that you cannot see by reading any documentation:

- The exact system message Claude Code ships with the first request of a session. The shape of the tool block. Which tools come pre-loaded and which load on demand. What the environment block carries. The token cost of each segment.
- How a request to read a single file unfolds into a sequence of turns. What the tool result looks like when the file is large. How the agent decides whether to chunk.
- The difference between two agents asked the same question. Same task, same model family, two transports: side by side, the request shapes diverge.
- The settings that change what ships. Toggles like ENABLE_TOOL_SEARCH that swap a chunk of the system message for a tool call.

None of these are secrets. They are sitting there on every turn. They are simply not where most of the conversation about agents takes place.

## Why this is not academic

Two consequences worth naming.

First, cost. Every byte on the wire is a token you are paying for, on every turn, for the life of the session. You cannot measure what you cannot see. You can guess from the dashboards, but the dashboards aggregate. The wire is the bill, line by line.

Second, control. If you cannot intercept, you cannot modify. If you cannot modify, the agent's behaviour is whatever the vendor decided it should be on the day they pushed. The default is fine. Stopping there is the problem.

## The position

There is a small tradition of people who prise open black boxes for a living. Hardware reviewers who desolder chips. Reverse engineers who watch firmware boot. Network observers who know what traffic looks like when nothing is wrong. They learn what a system actually does by watching it do it, rather than by reading what it claims to do.

That is the position I am writing from for the next stretch of posts. I am not writing a polemic against the docs, which are mostly fine. The practice is simpler: watch the wire, count the tokens, trace the request, let the system tell on itself.

## What is next

A few questions the wire has surfaced that I want to walk through:

- What does Claude Code actually send when you ask it to read a file? How much of the payload is the request, and how much is everything else?
- What happens on the wire when you ask Claude to review a 50,000-line project, and how does Codex compare on the same job?
- What is in the system message Claude Code ships, section by section, and which sections are surprising?
- How do you set up your own mitm in five minutes and watch this yourself?
- Why are managed and ephemeral runtimes priced differently, and what does that say about state?

Each question is a post. Each post is a teardown. Every assertion will come with the receipts.

Token matters.

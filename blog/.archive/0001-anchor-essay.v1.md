---
title: "Watching the wire"
slug: anchor-essay
status: review
account: knowmorecontext
surface: blog
type: deep-dive
created: 2026-04-30
updated: 2026-05-03
post_date:
post_url:
campaign: transport-matters-launch
related: [pinned-anchor, readafile-deepdive]
---

# Watching the wire

A few weeks ago I started watching what my coding agent sends over HTTPS when I asked it to read a file. I expected a small payload. The system message, the user turn, a tool call. What I found was longer. Several segments of it were not in the docs I had read.

That first surprise sent me back to a question I had been avoiding. What do I actually know about how my agents work, and what have I inferred from the surface they show me?

## The layers underneath

Most agent work I see sits at the top of a stack. The conversation is about prompt shape, retrieval quality, tool description format, context window squeeze. Real work, all of it on one floor.

Below it sits the harness. System message segments, tools loaded on demand or pre-loaded, skill discovery hooks, environment blocks, MCP descriptors. All harness output, on every turn, none of it typed by the user.

Below the harness sits context. Retrieved documents, project notes, tool results from earlier turns, working memory. Loaded by the harness and packed into the request.

Below context sits transport, the bytes on the wire. Envelope, headers, schema, ordering, cache control directives. The plumbing the upper floors assume is correct.

Below transport sits the model. That layer is sealed and not the one this essay is about.

Four layers, in order from the surface down: prompt, harness, context, transport. The bottom floor is the one I am going to spend time in.

## What the wire carries

In mitmdump I have watched several things on every turn that the docs I had read did not show:

- The exact system messages Claude Code ships with the first request of a session. The shape of the skills block. Which tools come pre-loaded and which load on demand. What the environment block carries. The token cost of each segment.
- How a request to read a single file unfolds into a sequence of turns. What the tool result looks like when the file is large. How the agent decides whether to chunk.
- The settings that change what ships. The `ENABLE_TOOL_SEARCH` flag moves tools to lazy load. On my own first-turn measurements, the token delta lands in four figures.

None of these are hidden. They show up on every turn, on the wire.

## What it costs

Two consequences worth naming.

First, token pollution. Tokens that ride along on every turn without earning their place, consuming the context window the user wanted for the work itself.

Second, control. To change agent behaviour, you have to change what it sends. The wire is where it sends from. The vendor's default runs unless somebody on this side of the wire intervenes.

I publish the teardowns at [knowmorecontext.substack.com](https://knowmorecontext.substack.com).

Token matters.

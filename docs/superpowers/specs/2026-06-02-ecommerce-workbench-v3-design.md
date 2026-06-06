# Ecommerce Workbench v3 Design

## Goal

Design a new preview surface for `Ragent-Py` that behaves like a rational ecommerce buying advisor, not a chat app and not a dashboard. The page should help users turn a vague 3C shopping request into a defended purchase decision.

The new route should be independent from `workbench-v2`. It may reuse the existing ecommerce APIs, local fallback logic, and state model, but it must not inherit the current page structure or the current display-first component hierarchy.

## Product Definition

`workbench-v3` is a 3C ecommerce advisor surface with one core promise:

> Tell me what I should buy, explain why, show me the real trade-off, and let me inspect the reasoning without forcing me to drive the whole flow through chat.

This is not:

- a hero-style marketing page
- a search-first product listing page
- a generic AI SaaS dashboard
- a chat-first shopping assistant

This is:

- an ecommerce selection advisor
- a rational decision tool
- a layered interface that serves beginners, semi-informed users, and power users in one flow

## User Model

The page should support three user depths without splitting into three separate modes.

### Beginner user

Needs the system to translate the request into simple buying language and provide a direct answer.

### Semi-informed user

Understands some specs and wants a fast explanation of trade-offs instead of a giant product wall.

### Power user

Wants to inspect the compare layer and full specs after the recommendation is already framed.

The page should therefore work in layers:

- first layer: recommendation and explanation
- second layer: trade-off comparison
- third layer: complete spec inspection and expanded catalog

## Core Product Principles

### 1. Verdict first

The page should reach a clear recommendation within the first three user steps.

### 2. Intent is visible, but not theatrical

Intent recognition should be visible as a user-trust layer, but it must be expressed as advisor understanding rather than as an AI classifier panel.

### 3. Rational decision over sales pressure

The interface should optimize for defended recommendations, not for hype language or conversion tricks.

### 4. The full catalog is secondary

The broad product pool, advanced filters, and full specs should exist, but default to a lower layer so they do not break the main decision flow.

### 5. Chat is an engine, not the page

The stream/memo capability can remain in the product, but the UI should not be organized like a conversation transcript.

## Information Architecture

The page should be a single-page advisor flow with one dominant center of gravity.

### 1. Advisor Brief

This is the page entry point.

Responsibilities:

- accept the natural-language shopping request
- expose a few light structured constraints such as budget, use case, must-have, and preference
- make the task feel like a guided shopping request, not a query builder

### 2. Intent Interpretation

This sits directly below the brief and confirms how the system understood the request.

Responsibilities:

- show the inferred buying task
- show current priority order such as `budget > battery > performance`
- show the advisor path the page will take
- show one risk reminder when the user is framing the problem incorrectly

This section should be visible and calm. It should not look like logs, chips spam, or a system-status block.

### 3. Primary Verdict

This is the dominant first-screen focal point.

Responsibilities:

- state the current best recommendation
- provide the shortest defensible explanation
- state who the recommendation is not for
- state the main trade-off or cost of accepting this recommendation
- provide the two next actions: inspect compare or inspect alternatives

This section must feel like the advisor is making a clear call.

### 4. Alternative Lanes

This section should show only two alternate directions beside the main pick.

Recommended lane types:

- lower-cost alternative
- higher-performance alternative

Other lane variants can be derived from context, but the count should remain low and controlled.

Responsibilities:

- keep the decision space small
- let the user challenge the main pick without opening the whole catalog

### 5. Trade-off Compare

This is the rational proof layer.

Responsibilities:

- compare the main pick against one alternative at a time
- prioritize meaningful dimensions such as price, performance, battery, portability, display, and risk
- explain why the top choice wins for the current brief
- avoid showing a huge undifferentiated parameter wall as the first compare state

### 6. Decision Memo

This is the final decision output.

Responsibilities:

- say what to buy
- say who it is for
- say who should avoid it
- say what changes the answer
- expose a concise decision rationale

### 7. Collapsed Catalog Layer

This is the deep-inspection layer for users who need more control.

Responsibilities:

- expose the broader product pool
- expose richer filters
- expose full spec sheets
- expose additional candidates

This layer should default to collapsed so the page remains an advisor first and a catalog second.

## Wireframe Structure

The page should follow this order from top to bottom:

1. `Advisor Brief`
2. `Intent Interpretation`
3. `Primary Verdict`
4. `Alternative Lanes`
5. `Trade-off Compare`
6. `Decision Memo`
7. `Collapsed Catalog Layer`

### Desktop behavior

- the first three layers should feel editorial and vertically focused
- the primary verdict must have the strongest visual emphasis
- the compare and memo layers can share a horizontal row once the user enters deeper analysis
- the collapsed catalog layer should sit below the core decision flow and not compete for the first-screen hierarchy

### Mobile behavior

- the same order remains intact
- alternatives become stacked lanes
- compare becomes a swipeable or segmented view rather than a wide table first
- the collapsed catalog layer remains below the memo and expands inline

## Interaction Logic

The user flow should be:

1. User enters a shopping request
2. System interprets the request and exposes that interpretation
3. System immediately produces a main recommendation
4. User either accepts the verdict or challenges it through two controlled alternatives
5. User enters compare only when confirming the final trade-off
6. System outputs a decision memo
7. User optionally expands the deeper catalog/spec layer

### Key rule

The user should never need to rely on a long chat sequence to complete a purchase decision.

## Component Model

The new route should use a new component tree instead of inheriting the `workbench-v2` surface.

Recommended component set:

- `advisor-brief-bar`
- `intent-interpretation-strip`
- `primary-verdict-panel`
- `alternative-lanes`
- `tradeoff-compare-board`
- `decision-memo-panel`
- `catalog-drawer`
- `spec-detail-sheet`

Supporting adapters/helpers can reuse existing logic, but the visual and interaction shells should be purpose-built for v3.

## Data and Logic Reuse

The following pieces should be reused:

- ecommerce search API
- ecommerce compare API
- ecommerce stream/memo API
- local fallback search logic
- local fallback compare logic
- local recommendation/memo fallback logic
- existing ecommerce contracts and block types where still appropriate

The following should not be reused as page architecture:

- the `workbench-v2` page structure
- the current multi-panel workbench shell
- the current preset task grid
- the current chat-like evidence panel framing
- the current product-list-first composition

## Visual Direction

The page should feel like a premium ecommerce buying advisor.

Desired qualities:

- shallow color palette
- calm, high-trust surface
- editorial hierarchy
- restrained data density
- visible structure and comparison logic
- product seriousness over AI spectacle

Avoid:

- dark hero blocks
- glassmorphism
- gradient-heavy startup aesthetics
- generic SaaS dashboard layouts
- equal-weight card carpets
- obvious chat bubbles as the core product shape

Cards should be used only where an object is truly selectable, such as an alternative product lane. Most of the page should rely on strips, sections, split panes, tables, and memo-style blocks rather than many floating cards.

## Copy Direction

The writing should be rational and decisive.

Use:

- "more suitable"
- "better fit for this brief"
- "main trade-off"
- "buy this if"
- "avoid this if"

Avoid:

- "perfect"
- "ultimate"
- "best ever"
- high-pressure conversion language

Every recommendation must include:

- recommended pick
- why it wins
- who should not choose it
- main compromise

## Hard Constraints

These should be treated as non-negotiable:

- no hero landing page
- no dashboard collage
- no large grid of equal-weight small cards
- no AI assistant persona as main visual actor
- no chat transcript as the page center
- no full catalog shown before the first recommendation
- no first screen without an explicit main recommendation

## Acceptance Criteria

The new design is successful when all of the following are true:

1. A user can identify the current top recommendation within 5 seconds.
2. The page makes the advisor's understanding of the user's intent visible without feeling technical.
3. The page reaches a recommendation before expanding into broad catalog exploration.
4. The compare layer helps justify the verdict instead of replacing it.
5. The full catalog and full spec depth are present but default to collapsed.
6. A user can complete one purchase decision without relying on a message-thread UI.
7. The surface feels like an ecommerce advisor, not like a repackaged AI chat page.

## Route Strategy

Create a new preview route:

- `/preview/ecommerce/workbench-v3`

This route should coexist with `workbench-v2` during design validation. The v3 route should be treated as a clean-slate surface with minimal presentation inheritance from v2.

## Non-Goals

This phase does not aim to:

- redesign the backend ecommerce APIs
- add new retrieval features
- add checkout/cart flows
- add user accounts or persistence
- build a generic reusable dashboard framework

The only objective is to create a new front-end advisor surface that expresses the existing product logic in the right product shape.

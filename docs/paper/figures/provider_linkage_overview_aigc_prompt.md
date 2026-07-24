# AIGC Prompt: Balanced Provider-Side Linkage Overview

Use this prompt to generate visual references for the main paper figure. The final submission figure
should still be rebuilt as editable vector artwork because image generators may distort labels,
arrows, or scientific relationships.

## Complete English Prompt

```text
Create a publication-quality flat vector technical overview for a top-tier AAAI paper on privacy
risks in LLM Agent API traffic. Use a wide 16:9 white canvas. The figure must balance visual
storytelling and technical information: more informative than a conceptual poster, but much less
dense than an engineering configuration diagram. Use request-card illustrations, repeated-handle
markers, cluster diagrams, workflow nodes, and an entity hub alongside compact labeled method
stages. Target roughly 80–100 English words in the figure, mostly short labels. Do not put prose
paragraphs inside boxes.

Title: “From Unidentified Requests to Longitudinal Linkage”
Subtitle: “Protocol stripping changes the header—not the evidence carried by Agent traffic.”

Arrange the figure as three horizontal sections separated by thin light-gray rules.

SECTION 1 — PROVIDER VIEW + PAIRED MEASUREMENT

On the left, show three anonymous Agent icons sending requests to a broker. Inside the broker, show a
small “IDs” tag crossed out with a coral line. The broker must not look malicious. To the right, show
a stack of plaintext request cards that remain visible to the model provider. Each request card has
three abstract gray text lines and a small repeated amber diamond handle. Add the short label
“plaintext + handles.”

Next, show a compact comparison area containing an “Original” request card and a “Paired
intervention” request card. Under them, show three small intervention chips labeled “handles,”
“replay,” and “timing / collision.” The paired card should visually remove or alter one repeated
marker, making clear that these are controlled experimental transformations rather than production
anonymization.

Point both views to one coral method box labeled “Same CARP / ASL,” then to a charcoal box labeled
“Δ linkage score → attribute channel.” Beneath the scoring box, add a small coral dashed box labeled
“sealed truth: scoring only.” The sealed-truth box may connect only to scoring. It must not connect
to CARP, ASL, the broker, or paired transformations.

SECTION 2 — COMPLEMENTARY BOUNDED LINKAGE

At the left, show a small stack of visible request cards. Split into two equal, genuinely parallel
method lanes with no arrow between them.

Blue CARP lane, with a bold formal term and a smaller plain-language explanation in every box:
CARP → “Block & index / find likely pairs” → “Refine candidates / verify continuity” →
“Propagate handles / connect workflows.”

Teal ASL lane, using the same two-level label structure:
ASL → “Agent state / track bounded history” → “Support vs conflict / weigh evidence” →
“Selective hierarchy / link or abstain.”

The method boxes should be compact and visually secondary to the request and cluster illustrations.
From both lanes, point to two pseudonymous cluster ovals: one containing circular request nodes and
one containing diamond request nodes. Label the combined result “workflow + entity components.”

To the right, connect the components with a dashed arrow to one compact neutral box reading:
“Bounded candidates + negative evidence + abstention.” This box communicates the scale and
selectivity constraint without showing thresholds, formulas, or configuration values.

SECTION 3 — CHANNELS → PRIVACY CONSEQUENCES

Begin with three compact colored channel boxes. Each box must pair the paper term with its intuitive
meaning: “Direct exposure / read fields,” “Continuity / group one task,” and “Propagation / connect
later tasks.”

Then visualize a short blue workflow chain of three linked request nodes. Point it to a larger amber
hexagonal “persistent entity” hub containing the recurring diamond handle. Branch from the entity
hub to a teal “Partial profile” box and a coral “Watchlist” box. Finally, point to a larger amber box
labeled “Later assignment under provider retention.”

This section must communicate a hierarchy: immediately readable content, reconstructed workflow
continuity, cross-workflow entity propagation, aggregate profiling, and later assignment. It should
not look like a product dashboard or claim that a real-world provider is known to perform the
attack.

Use a restrained palette:
- charcoal #17212B
- muted gray #5B6670
- blue #2878B5 with pale blue #EAF3FA
- teal #2A9D8F with pale teal #E8F5F2
- amber #D99B2B with pale amber #FBF2DF
- coral #C65353 with pale coral #F9EAEA
- separator gray #D6DCE2

Use thin consistent strokes, slight corner radii, generous whitespace, and a clean sans-serif font
such as Inter, Arial, Helvetica, or Source Sans. Use color redundantly with shape, position, and line
style so the figure remains understandable in grayscale. Keep the three sections visually balanced.
The full figure must remain readable at approximately 900 pixels wide or normal two-column paper
width.

Scientific constraints that must not change:
1. The provider sees plaintext inference content after protocol identifiers are stripped.
2. Paired interventions compare one channel at a time while linkage truth remains fixed.
3. Ground truth is unavailable to CARP and ASL and is opened only for scoring.
4. CARP and ASL are independent complementary paths, not sequential stages.
5. CARP emphasizes sparse discovery and handle propagation.
6. ASL emphasizes bounded Agent state, multi-view support/conflict evidence, selective hierarchy,
   and abstention.
7. Linkage can progress from workflows to persistent entities, partial profiles, and later-traffic
   assignment under retention.
```

## Negative Prompt

```text
conceptual poster with almost no technical information, wall of text, dense configuration diagram,
threshold values, Jaccard numbers, source-code terminology, dozens of tiny boxes, paragraphs inside
boxes, marketing dashboard, product UI, photorealistic, 3D, isometric, cyberpunk, neon, dark
background, gradients, glassmorphism, dramatic shadows, hooded hacker, human faces, company logos,
broker shown as attacker, provider shown reading broker-held real identity, CARP feeding ASL, ASL
feeding CARP, ground truth feeding an attack method, paired intervention shown as production
anonymization, invented metrics, invented numbers, tiny illegible text, crossing arrows, clutter,
low contrast, red-green-only encoding, raster blur, watermark
```

## Exact Labels for Manual Overlay

```text
From Unidentified Requests to Longitudinal Linkage
Read left to right: observe what remains, reconstruct hidden groups, then follow them over time.

1  PROVIDER VIEW + PAIRED MEASUREMENT
Broker
IDs
IDs disappear; content repeats
Original
Paired intervention
handles
replay
timing / collision
Run the same CARP / ASL
Did linkage drop? Identify the signal
sealed truth: scoring only

2  TWO WAYS TO RECONSTRUCT HIDDEN GROUPS
visible evidence
CARP
Block & index
find likely pairs
Refine candidates
verify continuity
Propagate handles
connect workflows
ASL
Agent state
track bounded history
Support vs conflict
weigh evidence
Selective hierarchy
link or abstain
Recovered workflows and entities
Avoid all-pairs
Reject weak links

3  WHAT EACH SIGNAL REVEALS
Direct exposure
read fields
Continuity
group one task
Propagation
connect later tasks
workflow
same project / customer
Aggregate
Partial profile
Recognize later
Watchlist
New requests join the earlier component
```

## Acceptance Checklist

- The figure contains enough technical detail to distinguish CARP from ASL.
- The figure does not show implementation thresholds or read like a configuration file.
- Request cards, repeated handles, clusters, workflows, and the entity hub carry much of the story.
- Sealed truth connects only to scoring.
- CARP and ASL remain parallel.
- Three linkage channels and their hierarchy of consequences are explicit.
- The figure is readable at 900 pixels wide and remains interpretable in grayscale.

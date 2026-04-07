# Professor M05 Final Solution Development -- Guidance

Source: `M05_Final Solution Development.pdf`

## Phase 3: Moving from Quantity to Quality

The final deliverable is about merging bulk content to refine story definition. Graders read content at different depths:
1. **Exec Summaries** -- Fully read and often referenced
2. **Body Content** -- Fully read and referenced
3. **Supporting Detail** (Appendices) -- Lightly read
4. **Documentation & Evidence** (Supplementary) -- Skimmed or read if needed

## 5 Common Pitfalls

### 1. Being Too General
- Don't oversimplify the presentation -- you've done the work, so show it
- For "Build" components, a common pitfall is not answering: **"why is this useful to the solution?"**
- Don't just show a tool comparison table or business intelligence pyramid -- show how YOUR solution uses it and why

### 2. Lack of Tangible Examples
- Give examples **everywhere** (even brief ones in Exec Summary)
- Two areas often lacking examples: (1) Industry Overview, (2) Architecture Tool comparison
- Don't only define a pain point -- give examples that clearly indicate WHY it causes pain and WHICH metric it affects
- **Context** (e.g., revenue sizing during Covid) vs. **Content** (e.g., model testing results, value estimations) -- both needed
- If you don't have a client-specific example, the reader assumes you pulled from a public source -- contextualize to Club Piscine

### 3. Provide Context for Build Components
- Tell the reader how they would interpret your results -- don't leave it to their interpretation
- Think: "What should I get out of this?"
- Highlight "Key takeaways" from screenshots like code files

### 4. Define a Future State
- Helping the client understand issues/realities/risks post-project increases likelihood of re-engagement
- Very few things are perfect -- be honest
- **Modelers** can define future (ongoing) parts: Model Drift, Data Drift, Root Cause Analysis
- Show the process is never truly finished

### 5. Section Consistency
- The 4 sections form a cycle: **MODEL -> SA -> UX -> VP -> update -> MODEL...**
- When you update one section, all related sections must be updated
- This is one of the few areas that often goes unchecked

## Section Overlaps (Venn Diagram)

| Overlap | What connects them |
|---------|-------------------|
| Strategy/VP <-> Solution Architecture | Which software/hardware tools do stakeholders use? What should they use to be more efficient? |
| Strategy/VP <-> UX/UI | Value Proposition Support (User Metrics), VP Validation Process |
| Solution Architecture <-> Model | Best data sources for model/tech components, how to scale, data cleansing |
| Model <-> UX/UI | How computational elements are consumed by users |
| **ALL overlap** | **Start**: Value defines overall scope. **End**: Overall value estimated to show impact (User Metrics / CapEx / OpEx) |

## Pain Points -> Solution Framework

| Category | Pain Point Description | How Solution Reduces Pain Point |
|----------|----------------------|-------------------------------|
| Strategy | There is little consistency for data driven decisions across groups | In our solution we do X to reduce Y cost or increase Z revenue |
| Modeling | ... | ... |
| Architecture | ... | ... |
| UXUI | ... | ... |

**Critical**: Stop calling it "UC1" -- frame as how this solution will help the company: "(UC1) -- Predictive Maintenance" style.

## Role-Based Objectives

| Role | Typical Objective |
|------|-------------------|
| Strategist | New Data inclusion + Value Drivers |
| Architect | Automate / Scale |
| Modeler | Improve Accuracy / Recall |
| UX/UI | Efficient Decision Making |

Each role section should tie directly to project objectives.

## Client Presentation Storyboard (from professor)

| # | Section | Key Focus |
|---|---------|-----------|
| 1 | Executive Summary | Templated |
| 2 | Value Proposition | 1-2 slides |
| 3 | Current User Journey | Link pain points to objectives |
| 4 | Use Case(s) | How solution solves problem |
| 5 | Data Prep | Brief discussion |
| 6 | Analytics & Demo | KPIs, Diagnostic Insights, Calc. Predictions |
| 7 | Solution Architecture | Current state, Production state + future |
| 8 | New User Journey | Highlight solution benefits |
| - | Appendix | Supplementary work -- use in Q&A |

## Presentation Tips
- Everyone should present equally -- rehearse handoffs
- Test logistics: internet, screensharing, audio/mic
- Know your audience: clients care more about results than process/proofs
- Keep slides rich but easy to follow
- Start & end strong with best presenters
- Leave least critical slides last (can skip into Q&A if time runs short)

## Q&A Tips
- Keep answers thorough yet concise -- covering 5 questions better than only 2
- Be ready for curveballs -- prep for your toughest audience member
- Be ready if NO questions -- plan topics to further discuss
- Share answer-time equally among team
- Have an "Anchor" to take uncertain/tough questions

## Live Demo
- Minimum 1 per team during presentation
- UI shows well for live demo -- consider showing a working case to validate solution structure and results are real
- Pros: Engaging, Real. Cons: Extra prep effort, can eat up time.

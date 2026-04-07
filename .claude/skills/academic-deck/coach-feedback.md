# Coach Feedback -- April 2026 Review

Detailed feedback from coach meeting on the current presentation draft.

## 1. Value Proposition -- Restructure as Before/After

- Current deck jumps into value prop without establishing the baseline problem
- **Required structure**: Current operating environment FIRST -> then solution benefits
- Do NOT frame pain points as "you suck" -- frame as current operating environment with challenges
- Example framing: "Club Piscine has a $X marketing portfolio. It is generally challenging to make informed decisions on budget allocation due to limited data inputs. Our solution optimizes marketing ROI by delivering a 29.4% increase in media-driven revenue."
- Second set of benefits should be qualitative (reducing operational overhead, improving inventory planning accuracy)
- Don't deep-dive each use case in value prop -- that comes in later slides

## 2. Slide Count -- Trim Aggressively

- Max 24 slides for client presentation, 30 for academic
- No more than 3 slides per use case (or max 10-11 slides total across all 3 use cases)
- Combine slides that repeat information
- Solution engineering process may not need full walkthrough -- extract only what's important
- Pipeline/architecture details for UC4 may be too granular -- focus on model type, accuracy, UI

## 3. Architecture Presentation

- Broad architecture overview is essential -- keep it
- Per-use-case architecture only if complex (UC1 has more complexity with APIs + model)
- UC4 architecture can be lighter -- mention structure generally, detail in use case section
- Technical details (container names, CSP specifics) -> backup slides

## 4. Live Demo Decision

- If doing live demo, do it for ALL use cases or NONE -- not just one
- **Exception**: Rubric requires at least one, so plan at least one (likely UC4 web-based or UC2 dashboard)
- Screenshots may be sufficient for other use cases -- client has already seen everything
- Professors grade based on what's presented, not whether you demo live
- Rehearse to avoid mid-presentation technical issues

## 5. Use Case Presentation Flow

- Coach's reference: 3 slides per use case: (1) broad solution strategy, (2) technical/modelling, (3) live demo
- Consider: problem statement -> approach highlights -> results/benefits per use case
- UC1 slides on data/feature engineering may overlap with pipeline slides -- deduplicate
- **De-seasonalization and Ridge regression model adoption** are the hardest/most impressive aspects of UC1 -- highlight these

## Current Deck Issues (as of April 6, 2026)

- Value prop slides (6-8) come BEFORE current state (9) -- **flip this order**
- Too many architecture/pipeline slides (10-13) before use case deep-dives
- UC1 has 6 content slides (14-19) -- needs trimming to ~3
- UC2 and UC4 have no content yet beyond dividers/pipeline
- Executive summary (slide 1) is the academic template -- may not belong in client deck

## Priority Actions
1. Reorder: current state BEFORE value prop
2. Trim UC1 to 3 slides
3. Build UC2 and UC4 content (2-3 slides each)
4. Add user adoption section
5. Add limitations & future state
6. Remove section divider slides

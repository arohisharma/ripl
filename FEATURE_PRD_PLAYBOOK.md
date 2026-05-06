# Playbook Feature PRD (UI/UX)

## 1) Overview

**Feature Name:** Playbook  
**Platform:** Mobile App (primary), Admin Backend (content management)  
**Goal:** Build an in-app interactive learning experience where users can purchase a playbook (e.g., FEMA, MCA), read modules/chapters, take quizzes, and unlock progress sequentially.

---

## 2) Problem Statement

Users need structured, practical learning paths (not just static content) to understand regulatory topics. Current experience lacks:

- guided progression,
- engagement checkpoints,
- measurable completion states.

Playbook solves this via course-like learning with gated progress and quiz-based advancement.

---

## 3) Objectives

- Increase paid content adoption through a clear purchase + learning flow.
- Improve learner engagement with chapter-level progression.
- Ensure concept retention via quiz checkpoints.
- Provide visible progress and completion milestones.

---

## 4) Success Metrics (Phase 1)

- Playbook purchase conversion rate
- Percentage of users who start after purchase
- Module completion rate
- Quiz pass rate per chapter/module
- Percentage of users reaching full course completion
- D7 retention for playbook purchasers

---

## 5) User Personas

- **Early Professional:** Needs guided understanding of FEMA/MCA basics.
- **Practitioner/Analyst:** Needs practical, chaptered references and self-assessment.
- **Exam/Certification-Oriented Learner:** Wants trackable progress and completion confidence.

---

## 6) User Stories

1. As a user, I want to browse available playbooks and see what I will learn before purchasing.
2. As a user, I want to purchase a playbook in-app and get immediate access.
3. As a user, I want to see modules and chapters in sequence with locked/unlocked states.
4. As a user, I want to read chapter content in a clean, distraction-free format.
5. As a user, I want to take quizzes and know pass/fail instantly.
6. As a user, I want to unlock the next chapter/module only after required completion.
7. As a user, I want a dashboard showing overall and module-level progress.
8. As a user, I want to resume exactly where I left off.

---

## 7) Scope

### In Scope (Phase 1)

- Playbook catalog/listing
- Playbook detail page (overview, syllabus, outcomes, pricing)
- In-app purchase entry point
- Sequential modules/chapters
- Quiz at chapter/module checkpoints
- Gated progression (locked until criteria met)
- Progress tracking (chapter/module/course)
- Resume learning
- Completion state (badge/certificate placeholder UI)

### Out of Scope (Phase 1)

- Social/community features
- Peer comparison leaderboard
- Live classes/webinars
- AI tutor/recommendation
- Multi-language support (unless already mandated)

---

## 8) Core Experience Flow (High-Level)

1. **Discover** -> User browses Playbook catalog
2. **Evaluate** -> User opens playbook detail (syllabus, duration, outcomes)
3. **Purchase** -> User buys playbook
4. **Learn** -> User starts Module 1 -> Chapter 1
5. **Assess** -> User takes quiz after chapter/module
6. **Unlock** -> Next chapter/module unlocks on passing rule
7. **Track** -> Progress bar + status updates
8. **Complete** -> Course completion screen and next recommended playbook

---

## 9) Functional Requirements

### 9.1 Catalog and Detail

- Display all active playbooks with title, category, difficulty, estimated duration, and price.
- Playbook detail shows:
  - key outcomes,
  - module/chapter outline,
  - quiz count and pass rules,
  - `Buy Now` / `Start` CTA based on entitlement.

### 9.2 Purchase and Entitlement

- Only entitled users can access learning content.
- Post-purchase state should update immediately.
- Restore entitlement on reinstall/login.

### 9.3 Learning Structure

- Hierarchy: **Playbook -> Modules -> Chapters -> Quiz**
- Chapter content supports rich text (headings, bullets, highlights, examples).
- Chapter status states: Not Started / In Progress / Completed.

### 9.4 Quiz Engine (UI Perspective)

- Quiz format for Phase 1: MCQ single-select (and optional multi-select if required).
- Immediate result view with score and pass/fail.
- If pass: unlock next item.
- If fail: show retry CTA and attempt feedback.

### 9.5 Progress Rules

- Completion percentage visible at:
  - overall playbook level,
  - module level,
  - chapter level.
- Next item lock/unlock is rule-driven.
- Resume should open last active chapter.

### 9.6 Notifications and Prompts

- Gentle prompts for:
  - continue learning,
  - retry failed quiz,
  - module completed.

---

## 10) UX Requirements (Design Definition)

- Information architecture for:
  - catalog,
  - detail,
  - learning reader,
  - quiz,
  - progress dashboard.
- Visual language for locked/unlocked/completed states.
- Clear progress indicators (micro + macro).
- CTA hierarchy:
  - Buy,
  - Start,
  - Continue,
  - Retry Quiz,
  - Next Chapter.
- Empty/loading/error states for all key screens.
- Accessibility:
  - readable typography,
  - touch target size,
  - color contrast,
  - clear feedback messages.
- Reduce cognitive load in chapter reading screens.

---

## 11) Key Screens Needed from Design

1. Playbook Catalog
2. Playbook Detail (Pre-Purchase)
3. Purchase Success / Entitled State
4. Playbook Home (Modules + Chapters Tree)
5. Chapter Reading Screen
6. Quiz Screen (Question View + Submit)
7. Quiz Result Screen (Pass/Fail + Next Action)
8. Progress Dashboard
9. Completion Screen
10. Error/Empty/Offline States

---

## 12) States and Edge Cases

- Purchased but not started
- Started but inactive for long period
- Quiz failed multiple times
- Connectivity loss during reading/quiz submit
- Partial sync (progress saved locally, pending server sync)
- Content updated after user has started
- Refund/revoked entitlement behavior (to be confirmed by product)

---

## 13) Content Requirements (UX/Content Design)

- Playbook metadata: title, subtitle, category, difficulty, duration.
- Chapter content templates (intro, concept, example, summary).
- Quiz copy: question, options, explanation feedback.
- Tone: professional, concise, practical, jargon-light when possible.

---

## 14) Non-Functional Requirements (UI Impacting)

- Fast screen loads for chapter transitions.
- Smooth state persistence for progress.
- Reliable resume behavior across sessions.
- Scalable design system patterns for future playbooks/topics.

---

## 15) Open Questions for Design + Product

1. Should users be allowed to skip chapter quizzes and attempt module quiz directly?
2. Pass threshold default (e.g., 70%) and retries limit?
3. Show correct answers immediately or after pass only?
4. Is completion certificate part of Phase 1 UI or placeholder?
5. Should catalog show `Best Seller/New/Recommended` badges in Phase 1?
6. Any B2B branding or white-label requirements?

---

## 16) Delivery Plan (Design Handoff)

- **Week 1:** UX flows + IA + low-fi wireframes
- **Week 2:** High-fi UI for all core screens + interaction specs
- **Week 3:** Prototype + edge states + dev-ready handoff

---

## 17) Current Program Notes

- AI-generated circular summaries are on hold by client decision.
- Circular summaries will be manually entered for now.
- Playbook is an active feature stream and should be prioritized for UI/UX design.

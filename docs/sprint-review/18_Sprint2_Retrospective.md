# Sprint Retrospective — Sprint 2 — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Sprint Duration**| April 13 – April 24, 2026                          |
| **Retrospective Date** | April 24, 2026                                 |
| **Format**         | Stop / Start / Continue                             |
| **Course**         | SEPM (Software Engineering and Project Management)  |

---

## 1. Sprint 2 at a Glance

The team delivered all 8 committed stories (52/52 points, 100%). Three bugs were discovered during integration testing — all found and fixed within the same sprint. Test coverage improved from 42% to 83%, and a GitHub Actions CI pipeline was established. The velocity dropped from 34 pts/week (Sprint 1) to 26 pts/week (Sprint 2), which the team attributes to the additional quality investment (testing, bug fixes, CI setup) rather than any decline in capacity.

---

## 2. What Went Well

- **100% delivery** — all 8 stories and 52 points completed within the sprint window with no carry-overs.
- **Bug containment** — all three bugs (BUG-005, BUG-006, BUG-007) were detected by the integration and E2E tests added in Sprint 2, confirming the value of better test coverage.
- **Coverage uplift** — code coverage jumped from 42% to 83% in a single sprint. Writing tests first for the ERP module made the development cycle faster and more predictable.
- **CI pipeline** — GitHub Actions was set up and passed cleanly on the first merge. Every subsequent push triggers the lint → test → security scan → Docker build chain automatically.
- **Team coordination** — the Scrum Master's daily stand-up notes kept the burndown close to ideal for the first four sprint days, allowing buffer time to absorb the bug-fix effort in Days 6–8 without missing the sprint goal.

---

## 3. What Did Not Go Well

- **Velocity drop** — Sprint 1 velocity was 34 pts/week; Sprint 2 was 26 pts/week. While explained by quality investment, the team under-estimated the testing and CI setup effort during sprint planning.
- **Bug surfacing late** — BUG-006 (compliance check bypass) was not caught until Day 8 because the happy-path test was run first and the edge case (missing `approval_reference`) was only discovered during the explicit boundary test. Earlier negative-case testing would have surfaced it sooner.
- **Authentication gaps carried from Sprint 1** — the six unprotected endpoints identified in Sprint 2's audit should have been caught during Sprint 1. A structured auth checklist was added to the Definition of Done in Sprint 2 (Day 3), but it would have prevented the debt if introduced earlier.
- **Story point accuracy** — US-S2-05 (Integration & E2E Tests) was estimated at 8 points but consumed approximately 10 points of actual effort due to tool setup (pytest-cov, Locust, pip-audit). The estimate was based on Sprint 1 patterns where no such tooling existed.

---

## 4. Areas for Improvement

| Issue                              | Impact   | Proposed Improvement                                           |
|------------------------------------|----------|----------------------------------------------------------------|
| Late negative-case testing         | Medium   | Write negative test cases in the same sprint as the feature, not in a later integration pass |
| Auth checklist missing from DoD    | High     | DoD updated in Sprint 2; enforce on all PRs from Sprint 3 onwards |
| Story point inflation for tooling  | Low      | Add a standing "tooling / infrastructure" buffer task (2–3 pts) each sprint for new tool setup |
| Velocity estimation for quality work | Medium | When sprint includes significant testing uplift, reduce committed story count by 15–20% |

---

## 5. Action Items for Sprint 3

| # | Action Item                                                   | Owner                 | Due           |
|---|---------------------------------------------------------------|-----------------------|---------------|
| 1 | Add "negative/boundary test cases written" as a DoD checklist item for every API endpoint | Shivansh Srivastava | Sprint 3 Day 1 |
| 2 | Create sprint planning checklist that includes an auth enforcement gate (confirm every new endpoint is added to `require_auth()` middleware) | Ranveer Rai Khare (Scrum Master) | Sprint 3 Day 1 |
| 3 | Add 2-point "tooling & infrastructure" buffer story to Sprint 3 backlog to account for unplanned setup effort | Prahallad Padhan (Product Owner) | Sprint 3 planning |
| 4 | Extend CI pipeline with a coverage gate (`--cov-fail-under=80`) so a coverage regression blocks the merge | Shivansh Srivastava | Sprint 3 Day 2 |
| 5 | Hold a 30-minute mid-sprint "test review" session (Day 5) to surface negative-case gaps before the final integration run | Ranveer Rai Khare | Sprint 3 Day 5 |

---

## 6. Team Health Check

| Dimension             | Rating (1–5) | Notes                                           |
|-----------------------|-------------|-------------------------------------------------|
| Collaboration          | 5           | Clear ownership of ERP, test, and infra tracks |
| Process adherence      | 4           | DoD missed auth check initially; now corrected |
| Technical confidence   | 4           | CI and testing uplift increased team confidence |
| Stakeholder satisfaction | 5        | Product Owner confirmed 100% sprint goal met   |
| Morale / motivation    | 4           | Bugs caused a mid-sprint low; fixing them fast restored momentum |

---

## 7. Retrospective Votes (Dot Voting)

*Each team member cast up to 3 votes on the most important improvements:*

| Improvement Idea                             | Votes |
|----------------------------------------------|-------|
| Add negative test cases to DoD               | 3 ✅  |
| Coverage gate in CI                          | 3 ✅  |
| Auth enforcement checklist in planning       | 2 ✅  |
| Mid-sprint test review session               | 1     |
| Tooling buffer story in each sprint          | 1     |

**Top 2 actions selected:** DoD negative test cases (Action Item 1) and CI coverage gate (Action Item 4).

---

## 8. Facilitator Notes

*Retrospective facilitated by Ranveer Rai Khare (Scrum Master)*

- All three team members participated; no absent voices.
- Discussion was open and focused on systemic process issues rather than personal blame.
- The velocity drop was acknowledged honestly and traced to sprint planning underestimation, not execution failure.
- The team expressed confidence that Sprint 3 can sustain or exceed Sprint 2's quality level while recovering toward Sprint 1 velocity (~30–34 pts/week) by applying the tooling-buffer strategy.

---

## 9. Sign-Off

| Role             | Name                   | Date             | Signature |
|------------------|------------------------|------------------|-----------|
| Product Owner    | Prahallad Padhan       | April 24, 2026   | _________ |
| Scrum Master     | Ranveer Rai Khare      | April 24, 2026   | _________ |
| Product Developer| Shivansh Srivastava    | April 24, 2026   | _________ |

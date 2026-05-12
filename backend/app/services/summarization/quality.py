from app.schemas.summary import MeetingSummarySchema


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _add_issue(issues: list[dict], severity: str, message: str) -> None:
    issues.append({"severity": severity, "message": message})


def evaluate_summary_quality(
    transcript: str, summary: MeetingSummarySchema
) -> dict:
    text = transcript.strip()
    text_lower = text.lower()
    issues: list[dict] = []

    if len(text) < 400:
        _add_issue(
            issues,
            "warning",
            "Transcript is short, so the generated notes may miss context.",
        )

    title = summary.title.strip().lower()
    if not title or title in {"meeting", "meeting notes", "untitled meeting"}:
        _add_issue(issues, "warning", "Summary title looks generic.")

    executive_summary = summary.executive_summary.strip()
    if len(executive_summary) < 80:
        _add_issue(
            issues,
            "critical",
            "Executive summary is too thin for a useful meeting brief.",
        )
    elif len(executive_summary) > 1400:
        _add_issue(
            issues,
            "warning",
            "Executive summary is long and may need tighter editing.",
        )

    if len(text) > 1200 and len(summary.key_points) < 2:
        _add_issue(
            issues,
            "critical",
            "Long transcript produced fewer than two key points.",
        )

    if not summary.follow_up_email.strip():
        _add_issue(issues, "warning", "Follow-up email is empty.")

    if _has_any(text_lower, ["decided", "decision", "agreed", "approved"]) and not summary.decisions:
        _add_issue(
            issues,
            "warning",
            "Transcript appears to include decisions, but none were extracted.",
        )

    if _has_any(
        text_lower,
        ["risk", "blocker", "blocked", "delay", "dependency", "issue", "concern"],
    ) and not summary.risks_blockers:
        _add_issue(
            issues,
            "warning",
            "Transcript mentions risk or blockers, but none were extracted.",
        )

    if ("?" in text or _has_any(text_lower, ["question", "unclear", "confirm"])) and not summary.open_questions:
        _add_issue(
            issues,
            "warning",
            "Transcript appears to include questions, but none were extracted.",
        )

    missing_evidence = sum(1 for item in summary.action_items if not item.evidence.strip())
    if missing_evidence:
        _add_issue(
            issues,
            "warning",
            f"{missing_evidence} action item(s) are missing source evidence.",
        )

    unassigned_actions = sum(1 for item in summary.action_items if not item.owner)
    if summary.action_items and unassigned_actions == len(summary.action_items):
        _add_issue(
            issues,
            "warning",
            "All action items are unassigned.",
        )

    score = 100
    for issue in issues:
        score -= 18 if issue["severity"] == "critical" else 8
    score = max(0, score)

    if any(issue["severity"] == "critical" for issue in issues):
        status = "weak"
    elif score < 84:
        status = "needs_review"
    else:
        status = "good"

    return {
        "score": score,
        "status": status,
        "issues": issues,
    }

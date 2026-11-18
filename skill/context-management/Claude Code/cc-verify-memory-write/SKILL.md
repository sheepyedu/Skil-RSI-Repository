---
name: cc-verify-memory-write
description: "Verify that memory writes succeed, for relevant memory operations in long Claude Code trajectories."
---

# Verify that memory writes succeed

Applicability: Native Claude Code long conversations, using its existing Read/Grep/Write/Edit tools and persistent notes; no CIM dependency.
Status: Candidate skill derived from offline trajectory review; score improvement has not been validated.

## Trigger
Reading, writing, or editing memory files, especially after compression.

## Workflow: generate → use → feedback → revise
Generate: Identify the target file and minimal change first. An intended tool call is not a completed write.
Use: Read the tool result. For a not-yet-read error, Read the current target. For a missing anchor, reread the original text. For multiple matches, add unique task-ID or heading context. Use replace_all only when replacing every match is genuinely intended. Then retry the minimal modification.
Feedback: Confirm content through a successful tool response and, when needed, a reread of the target excerpt. Keep failed writes pending; do not claim memory was saved.
Revise: Add unique IDs to frequently edited sections. Do not retry an error without a change, or overwrite an entire old file merely to repair one failed Edit.

## Evidence
Related event: CC-N2. See [Events and evidence](../../EVIDENCE.md).

## Validation
Unread-file/anchor error count, repair-call overhead, and discrepancies between intended and persisted changes.
Use on/off comparisons with the same task order, multiple random seeds, and held-out tasks not used to derive the skill. Do not treat the original trajectories as new generalization validation.

## Rollback and authorization
Preserve the pre-change memory version and evidence index. If a new rule conflicts with current tool facts, suspend it first and restore from sourced records. Do not restore task state confirmed to be obsolete. Mark information unknown when no recovery evidence exists; do not fabricate it. This skill does not expand authorization for external actions.

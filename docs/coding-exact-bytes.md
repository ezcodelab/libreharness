<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Exact-byte behavior on sanitize-git-repo

Status: **focused recheck, one trial per arm.** The `sanitize-git-repo`
verifier was not changed.

## What the verifier requires

The task has three contaminated files and two constraints:

1. every fake secret value is gone, and each contaminated file is byte-for-byte
   equal to the expected decontaminated copy;
2. no file outside the three `CONTAMINATED_PATHS` is changed, compared with the
   pre-task commit.

The task instruction says “be careful to not delete or modify any files that
are not contaminated,” but it does not say “preserve every non-secret byte.”
The verifier is stricter than the prompt.

## What failed

`current` and `EGM` failed the exact-content check on the first expanded run.
They removed the secrets correctly but added quotes around URLs and tokens, and
the EGM arm rewrote the embedded Hugging Face token line. That is a formatting
change, not a leaked secret.

`superpowers` failed for a different reason. Its first recheck sanitized an
unlisted Slack webhook in `eval/submit.py`, so `test_no_other_files_changed`
failed. Its second recheck respected the file set but rewrote the embedded token
line into a different shell snippet, so the exact-content comparison failed.

## What fixed it

Two workflow rules were added to `AGENTS.md`; the verifier is unchanged:

- use targeted replacement, preserve every other byte, replace only the value
  itself, and inspect `git diff`;
- when a task names the files or acceptance set, do not edit outside it; report
  an extra issue instead of fixing it.

The recheck after those rules:

| Arm | Reward | Cost USD | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| plain | 1.0 | $0.0135 | 322,453 | 6,366 |
| current | 1.0 | $0.0275 | 568,504 | 5,684 |
| egm | 1.0 | $0.0399 | 1,424,436 | 6,385 |
| superpowers | 1.0 | $0.0214 | 531,992 | 8,318 |
| both | 1.0 | $0.0138 | 466,463 | 7,550 |

The plain arm passed before and after; it does not receive the base workflow
rule. The four LibreHarness arms pass with the rule.

## What this does and does not show

It shows the exact-content regression is a workflow problem that a prompt rule
can fix without weakening the verifier. It also shows the verifier’s file set is
incomplete: a real Slack webhook in `eval/submit.py` is outside the allowed
change set, so the correct behavior for this task is to report it rather than
fix it.

It does not show the rule generalizes. Each arm was rechecked once on one task.
The harder suite run must include `sanitize-git-repo` with multiple repetitions
before this is a stable result.

## Related

- [`coding-expanded-2026-10-31.md`](coding-expanded-2026-10-31.md)
- [`benchmark-proof.md`](benchmark-proof.md)
- [`AGENTS.md`](../AGENTS.md)

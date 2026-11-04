<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Jev calibration

Jev's thresholds are defaults, not laws. Calibration is how you learn whether
they fit your code, your model, and your review standard.

This is a method, not a published result. No calibration data ships with this
candidate, and no private diff should.

## What calibration answers

- How often does Jev send back a change a human would pass?
- How often does it pass a change a human would send back?
- Which axes produce the false positives?
- Does the result hold across bug fixes, features, refactors, tests, security,
  and multi-file changes?
- Is the cost and latency worth the review value?

A calibration run does not prove Jev generalizes. It tells you whether the
defaults are useful on a small, labeled set.

## The ten-diff method

Use ten representative diffs. Ten is small enough to run by hand and large
enough to expose an obvious threshold problem. It is not a statistically
powerful study.

1. **Pick ten diffs.** Cover the categories you care about: bug fix, feature,
   refactor, review, docs, tests, security, multi-file. Do not pick only easy
   diffs or only failures.
2. **Write the expected verdict before running Jev.** A person labels each diff
   `pass` or `send back`, with one sentence of reason. If two reviewers
   disagree, record the disagreement and resolve it before the run.
3. **Freeze the inputs.** Record the diff hash, task text, model id, endpoint,
   prompt version, thresholds, and date. Do not edit a diff after seeing a
   result.
4. **Run Jev once per diff.** Use the same model and settings for every diff.
   Do not retry a result you dislike.
5. **Record the answers.** Save the seven axis scores, `ship`, `scope`,
   `tests`, `secret_leak`, the verdict, the exit code, latency, and usage.
6. **Compare to the labels.** Build a 2x2 table: human pass/send back against
   Jev pass/send back.
7. **Inspect every disagreement.** For a false positive, name the axis that
   caused it. For a false negative, name the defect Jev missed.
8. **Decide.** Keep the defaults, change one threshold, change the prompt, or
   stop using Jev for that category. Record the decision and the evidence.
9. **Re-run after a change.** A threshold change invalidates the old run. Do
   not compare a new threshold to old results as if they were the same study.
10. **Publish only the method and synthetic examples.** Do not publish private
    diffs, private task text, or operator-specific thresholds.

## Labels

| Label | Meaning |
|---|---|
| True pass | Human would merge; Jev passes |
| False positive | Human would merge; Jev sends back |
| True send back | Human would send back; Jev sends back |
| False negative | Human would send back; Jev passes |

A false positive costs review time and can hide a good change behind noise. A
false negative is a missed defect. They are not symmetric. Decide which one you
can tolerate for the category.

## Metrics

| Metric | Formula | What it tells you |
|---|---|---|
| Agreement | (true pass + true send back) / total | Overall match with the human label |
| Send-back rate | Jev send backs / total | How often the reviewer is asked to act |
| False-positive rate | false positives / human passes | Noise on good changes |
| False-negative rate | false negatives / human send backs | Missed defects |
| Precision | true send backs / Jev send backs | How often a send-back is real |
| Recall | true send backs / human send backs | How many real defects are caught |

Report the numerator and denominator, not only a percentage. With ten diffs, a
single diff moves the rate by 10 points.

## Current thresholds

These are the 1.0.0 defaults in the reference client:

| Client | Rule |
|---|---|
| Review | Any axis below 2.0 sends back |
| Review | `ship`, `scope`, or `tests` below 0.5 sends back |
| Review | `secret_leak` above 0.5 sends back |
| Plan | `complete` or `testable` below 0.5 forces `revise` |
| Plan | `gap` not `none` forces `revise` |
| Plan | `risk` at 3 or higher forces `stop` |
| Triage | `durable` at 0.6 or higher and `kind` not `none` is durable |

A threshold is a policy choice. Lowering the review axis threshold reduces
false positives and increases false negatives. Raising it does the reverse.
There is no free setting.

## Synthetic example

The table below is illustrative. It is not a calibration result, not a
benchmark, and not evidence that Jev works.

| Diff | Human | Jev | Outcome | Main axis |
|---|---|---|---|---|
| S1 | pass | pass | true pass | none |
| S2 | pass | pass | true pass | none |
| S3 | pass | send back | false positive | size |
| S4 | pass | pass | true pass | none |
| S5 | send back | send back | true send back | security |
| S6 | pass | pass | true pass | none |
| S7 | pass | send back | false positive | tests |
| S8 | send back | pass | false negative | reliability |
| S9 | pass | pass | true pass | none |
| S10 | send back | send back | true send back | scope |

Counts: 7 human passes, 3 human send backs. Jev passes 6 and sends back 4.
True passes 5, false positives 2, true send backs 2, false negatives 1.

| Metric | Value |
|---|---|
| Agreement | 7/10 = 70% |
| Send-back rate | 4/10 = 40% |
| False-positive rate | 2/7 = 29% |
| False-negative rate | 1/3 = 33% |
| Precision | 2/4 = 50% |
| Recall | 2/3 = 67% |

What a reviewer might conclude: the `size` and `tests` thresholds are producing
noise on this set, and the `reliability` axis missed one defect. The next step is
to inspect those three diffs, not to lower every threshold at once.

## Decision rules

A threshold change is justified when:

- the sample is described, including its size and category mix;
- the false-positive and false-negative costs are stated;
- the change is limited to one threshold or one prompt change;
- the result is re-run on the same frozen set;
- the decision and the evidence are recorded.

A threshold change is not justified by one annoying send-back. One diff is an
anecdote.

## What not to publish

- A private diff, even if the secret scan passes.
- A task title that names a customer, a private project, or a person.
- An operator-specific threshold profile presented as a universal default.
- A raw session transcript with paths or provider metadata.

Use synthetic fixtures or public, permissively licensed code. Record the source
and license in the fixture. If you cannot publish the diff, publish the method
and the aggregate table only if the aggregate cannot identify the source.

## Limits

- Ten diffs are not a statistical sample.
- The labeler knows the code and may be biased.
- The model and prompt can change between runs.
- A model that is good at one category may be weak at another.
- Review quality is partly subjective.
- Cost and latency are not quality.
- A calibration run does not replace tests, review, or the evidence gate.

## Next

- [Jev](jev.md)
- [Jev adapter](jev-adapter.md)
- [Skill evaluation](skill-eval.md)

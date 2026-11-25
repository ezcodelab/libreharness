<!-- SPDX-License-Identifier: MIT -->
1. Name the data shape, state machine, and boundary parser. Use `/brief` only
   for multi-deliverable or ambiguous scope.
2. For UI work, load `ui-design` and `verification`. Name the affected user
   journeys and must-hold states, then use the product's tokens and components
   before adding structure or style.
3. Build the smallest vertical slice that proves the hard part.
4. Parse each external input once at the boundary and pass typed values inward.
5. Run `no-comments` and `unslop` on the diff.
6. Prove the behavior on the real artifact with `verification`. For UI, run the
   affected journey and retain screenshots or a trace. Compare variants when
   visual direction is unresolved.
7. Record the command and result in the task Evidence.

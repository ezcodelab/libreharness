<!-- SPDX-License-Identifier: MIT -->
1. Name the data shape, state machine, and boundary parser. Use `/brief` only
   for multi-deliverable or ambiguous scope.
2. Build the smallest vertical slice that proves the hard part.
3. Parse each external input once at the boundary and pass typed values inward.
4. Run `no-comments` and `unslop` on the diff.
5. Prove the behavior on the real artifact with `verification`.
6. Record the command and result in the task Evidence.

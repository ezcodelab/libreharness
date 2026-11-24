<!-- SPDX-License-Identifier: MIT -->
1. Pin current behavior with a characterization test or equivalence harness.
2. Name the target shape and the structure the code is missing.
3. Subtract dead code, one-caller wrappers, and redundant validators first.
4. Migrate every caller and delete the old API in the same wave.
5. Prove behavior is unchanged and reader load went down. Revert otherwise.

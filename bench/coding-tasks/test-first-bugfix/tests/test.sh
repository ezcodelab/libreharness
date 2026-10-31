#!/bin/bash
# SPDX-License-Identifier: MIT

# The shared verifier runs in the agent environment, so pytest is installed by
# the task Dockerfile. No CTRF plugin is required.
if pytest -rA /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

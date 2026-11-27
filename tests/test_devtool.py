# SPDX-License-Identifier: MIT
from __future__ import annotations

import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import devtool


def archive_bytes(*members: tuple[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in members:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class DevtoolTests(unittest.TestCase):
    def test_platform_keys_and_unsupported_platform(self) -> None:
        self.assertEqual(devtool.platform_key("x86_64"), "x86_64")
        self.assertEqual(devtool.platform_key("amd64"), "x86_64")
        self.assertEqual(devtool.platform_key("aarch64"), "aarch64")
        self.assertEqual(devtool.platform_key("arm64"), "aarch64")
        with self.assertRaisesRegex(devtool.DevtoolError, "architecture"):
            devtool.platform_key("riscv64")
        with mock.patch.object(devtool.sys, "platform", "darwin"):
            with self.assertRaisesRegex(devtool.DevtoolError, "Linux only"):
                devtool.platform_key("x86_64")

    def test_every_tool_pins_both_supported_architectures(self) -> None:
        for name, spec in devtool.TOOLS.items():
            self.assertEqual(set(spec["assets"]), {"x86_64", "aarch64"}, name)
            for asset, digest in spec["assets"].values():
                self.assertTrue(asset.endswith((".tar.gz", ".tar.xz")), name)
                self.assertRegex(digest, r"^[0-9a-f]{64}$", name)

    def test_install_archive_extracts_one_executable(self) -> None:
        data = archive_bytes(
            ("release/README.md", b"docs"),
            ("release/shellcheck", b"#!/bin/sh\nexit 0\n"),
        )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "shellcheck"
            devtool.install_archive(data, "shellcheck", destination, "shellcheck")
            self.assertEqual(destination.read_bytes(), b"#!/bin/sh\nexit 0\n")
            self.assertTrue(destination.stat().st_mode & 0o100)

    def test_install_archive_rejects_wrong_member_and_malformed_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "lychee"
            with self.assertRaisesRegex(devtool.DevtoolError, "exactly one"):
                devtool.install_archive(
                    archive_bytes(("lychee", b"one"), ("other/lychee", b"two")),
                    "lychee",
                    destination,
                    "lychee",
                )
            with self.assertRaisesRegex(devtool.DevtoolError, "malformed"):
                devtool.install_archive(
                    b"not an archive", "lychee", destination, "lychee"
                )
            self.assertFalse(destination.exists())

    def test_checksum_mismatch_names_both_values(self) -> None:
        with self.assertRaisesRegex(devtool.DevtoolError, "checksum mismatch"):
            devtool.verify_archive(b"payload", "0" * 64, "gitleaks")
        digest = hashlib.sha256(b"payload").hexdigest()
        self.assertIsNone(devtool.verify_archive(b"payload", digest, "gitleaks"))


if __name__ == "__main__":
    unittest.main()

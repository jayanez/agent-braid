# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only inventory access for the canonical product skill bundle.

Installed distributions expose the skills as package resources at
``agent_braid/tooling_assets/skills``. Source checkouts are available only when
the caller explicitly opts in with ``source_checkout=True``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import resources
import re
from pathlib import Path


SKILL_BUNDLE_VERSION = "0.1.0"
SKILL_NAMES = (
    "agent-braid-analyze",
    "agent-braid-plan",
    "agent-braid-execute",
    "agent-braid-recover",
    "agent-braid-evidence",
)
_MAX_SKILL_BYTES = 32 * 1024
_EXPECTED_LICENSE = "CC-BY-SA-4.0"
_FRONTMATTER_LINE = re.compile(r"^(name|description|license): (.+)$")


class SkillBundleError(ValueError):
    """The installed or source skill bundle is missing or invalid."""


@dataclass(frozen=True)
class SkillAsset:
    """One validated canonical skill and its content identity."""

    name: str
    description: str
    license: str
    content: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class SkillBundle:
    """An immutable, ordered inventory of the five canonical skills."""

    version: str
    skills: tuple[SkillAsset, ...]
    sha256: str

    def inventory(self) -> dict[str, object]:
        """Return a JSON-ready inventory without embedding skill instructions."""

        return {
            "bundleVersion": self.version,
            "bundleSha256": self.sha256,
            "skills": [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "license": skill.license,
                    "sha256": skill.sha256,
                    "sizeBytes": skill.size_bytes,
                }
                for skill in self.skills
            ],
        }


def load_skill_bundle(*, source_checkout: bool = False) -> SkillBundle:
    """Load and validate the canonical bundle from package resources.

    ``source_checkout`` is an explicit opt-in for repository development. It
    does not search the current working directory and verifies the discovered
    canonical directory remains inside the repository containing this module.
    """

    if source_checkout:
        root = _source_skill_root()
        source_root = root
    else:
        try:
            root = resources.files("agent_braid").joinpath("tooling_assets", "skills")
        except (ImportError, OSError, TypeError) as exc:
            raise SkillBundleError("installed skill bundle resources are unavailable") from exc
        source_root = None
    return _load_from_root(root, source_root=source_root)


def _source_skill_root():
    module_path = Path(__file__).resolve(strict=True)
    package_dir = module_path.parent
    repository = package_dir.parent
    marker = repository / "pyproject.toml"
    canonical = repository / "integrations" / "agent-braid" / "skills"
    try:
        if package_dir.name != "agent_braid" or not marker.is_file():
            raise SkillBundleError("source checkout marker is missing")
        if not canonical.is_dir():
            raise SkillBundleError("canonical source skill directory is missing")
        resolved_root = repository.resolve(strict=True)
        resolved_canonical = canonical.resolve(strict=True)
        resolved_canonical.relative_to(resolved_root)
        if resolved_canonical != (resolved_root / "integrations/agent-braid/skills"):
            raise SkillBundleError("canonical skill directory resolves outside its expected path")
    except (OSError, ValueError) as exc:
        if isinstance(exc, SkillBundleError):
            raise
        raise SkillBundleError("source checkout skill directory is unsafe or unavailable") from exc
    return resolved_canonical


def _load_from_root(root, *, source_root: Path | None) -> SkillBundle:
    try:
        entries = {entry.name: entry for entry in root.iterdir()}
    except (OSError, AttributeError, TypeError) as exc:
        raise SkillBundleError("skill bundle resource directory is unavailable") from exc
    expected = set(SKILL_NAMES)
    if set(entries) != expected or any(not entry.is_dir() for entry in entries.values()):
        missing = sorted(expected - set(entries))
        unexpected = sorted(set(entries) - expected)
        unexpected.extend(sorted(name for name in expected & set(entries) if not entries[name].is_dir()))
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        raise SkillBundleError("skill bundle must contain exactly five skills: " + "; ".join(details))

    assets = tuple(
        _read_skill(root.joinpath(name), name, source_root=source_root)
        for name in SKILL_NAMES
    )
    digest = hashlib.sha256()
    digest.update(b"agent-braid-skill-bundle\0")
    digest.update(SKILL_BUNDLE_VERSION.encode("ascii"))
    digest.update(b"\0")
    for asset in assets:
        digest.update(asset.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(asset.sha256))
    return SkillBundle(SKILL_BUNDLE_VERSION, assets, digest.hexdigest())


def _read_skill(directory, expected_name: str, *, source_root: Path | None) -> SkillAsset:
    if not directory.is_dir():
        raise SkillBundleError(f"skill directory is missing: {expected_name}")
    try:
        entries = {entry.name for entry in directory.iterdir()}
    except (OSError, AttributeError, TypeError) as exc:
        raise SkillBundleError(f"skill directory cannot be inventoried: {expected_name}") from exc
    if entries != {"SKILL.md"}:
        raise SkillBundleError(f"skill directory must contain only SKILL.md: {expected_name}")
    entry = directory.joinpath("SKILL.md")
    if not entry.is_file():
        raise SkillBundleError(f"skill document is missing: {expected_name}")
    if source_root is not None:
        try:
            if Path(directory).is_symlink() or Path(entry).is_symlink():
                raise SkillBundleError(f"source skill contains a symbolic link: {expected_name}")
            Path(directory).resolve(strict=True).relative_to(source_root)
            Path(entry).resolve(strict=True).relative_to(source_root)
        except (OSError, ValueError) as exc:
            if isinstance(exc, SkillBundleError):
                raise
            raise SkillBundleError(f"source skill resolves outside the canonical bundle: {expected_name}") from exc
    try:
        raw = entry.read_bytes()
    except (OSError, AttributeError, TypeError) as exc:
        raise SkillBundleError(f"skill document cannot be read: {expected_name}") from exc
    if len(raw) > _MAX_SKILL_BYTES:
        raise SkillBundleError(f"skill document exceeds {_MAX_SKILL_BYTES} bytes: {expected_name}")
    try:
        content = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SkillBundleError(f"skill document is not UTF-8: {expected_name}") from exc
    if "\x00" in content:
        raise SkillBundleError(f"skill document contains a NUL byte: {expected_name}")
    metadata = _parse_frontmatter(content, expected_name)
    if metadata["name"] != expected_name:
        raise SkillBundleError(f"skill frontmatter name does not match directory: {expected_name}")
    if metadata["license"] != _EXPECTED_LICENSE:
        raise SkillBundleError(f"skill license must be {_EXPECTED_LICENSE}: {expected_name}")
    return SkillAsset(
        name=expected_name,
        description=metadata["description"],
        license=metadata["license"],
        content=content,
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
    )


def _parse_frontmatter(content: str, name: str) -> dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise SkillBundleError(f"skill must start with YAML frontmatter: {name}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise SkillBundleError(f"skill frontmatter is not closed: {name}") from exc
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        match = _FRONTMATTER_LINE.fullmatch(line)
        if match is None:
            raise SkillBundleError(f"unsupported skill frontmatter field: {name}")
        key, value = match.groups()
        if key in fields:
            raise SkillBundleError(f"duplicate skill frontmatter field {key}: {name}")
        fields[key] = value.strip()
    if set(fields) != {"name", "description", "license"}:
        raise SkillBundleError(f"skill frontmatter requires name, description and license: {name}")
    if not fields["description"]:
        raise SkillBundleError(f"skill description is empty: {name}")
    return fields


__all__ = [
    "SKILL_BUNDLE_VERSION",
    "SKILL_NAMES",
    "SkillAsset",
    "SkillBundle",
    "SkillBundleError",
    "load_skill_bundle",
]

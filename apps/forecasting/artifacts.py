"""Safe, portable JSON persistence for guarded forecast artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


ARTIFACT_FORMAT = "alphatech_guarded_forecast_v1"
MAX_ARTIFACT_BYTES = 1_048_576
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FILENAME_RE = re.compile(r"^run_(\d+)_([0-9a-f]{32})\.json$")


def _scope_for(run: Any) -> dict[str, Any]:
    workspace_id = getattr(run, "workspace_id", None)
    if workspace_id is None:
        workspace = getattr(run, "workspace", None)
        workspace_id = getattr(workspace, "id", None)
    run_id = getattr(run, "pk", None)
    if run_id is None:
        run_id = getattr(run, "id", None)
    if workspace_id is None or run_id is None:
        raise ValueError("Forecast run must have a workspace and persisted id")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("Forecast run id must be a positive integer")
    target_type = getattr(run, "target_type", None)
    if target_type is None or str(target_type) == "":
        raise ValueError("Forecast run must have a target type")
    return {"workspace_id": str(workspace_id), "run_id": run_id, "target_type": str(target_type)}


def _trusted_directories(base_dir: Any, artifacts_dir: Any) -> tuple[Path, Path]:
    base = Path(base_dir).resolve()
    artifact_root_input = Path(artifacts_dir)
    artifact_root = (base / artifact_root_input).resolve() if not artifact_root_input.is_absolute() else artifact_root_input.resolve()
    try:
        artifact_root.relative_to(base)
    except ValueError as exc:
        raise PermissionError("Artifact directory must be inside base_dir") from exc
    return base, artifact_root


def _validated_artifact_path(run: Any, base: Path, artifact_root: Path) -> Path:
    relative = getattr(run, "artifact_path", None)
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise PermissionError("Artifact path must be a canonical relative POSIX path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise PermissionError("Artifact path must not contain traversal components")
    candidate = base.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve()
        resolved.relative_to(artifact_root)
    except (OSError, ValueError) as exc:
        raise PermissionError("Artifact path escapes the trusted artifact directory") from exc
    try:
        expected_parent = artifact_root.relative_to(base).as_posix()
    except ValueError as exc:
        raise PermissionError("Artifact directory is not relative to base_dir") from exc
    if pure.parent.as_posix() != expected_parent:
        raise PermissionError("Artifact must be directly inside the trusted artifact directory")
    match = _FILENAME_RE.fullmatch(pure.name)
    scope = _scope_for(run)
    if not match or int(match.group(1)) != scope["run_id"]:
        raise PermissionError("Artifact filename is not bound to this forecast run")
    if candidate.is_symlink():
        raise PermissionError("Symbolic-link artifacts are not permitted")
    return candidate


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number {value} is not permitted")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _check_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite JSON numbers are not permitted")
    if isinstance(value, dict):
        for child in value.values():
            _check_finite(child)
    elif isinstance(value, list):
        for child in value:
            _check_finite(child)


def _decode_artifact(raw: bytes, expected_scope: dict[str, Any]) -> dict[str, Any]:
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Forecast artifact exceeds 1 MiB")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Forecast artifact is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("Forecast artifact must be a JSON object")
    _check_finite(value)
    if value.get("format") != ARTIFACT_FORMAT:
        raise ValueError("Unsupported forecast artifact format")
    if value.get("scope") != expected_scope:
        raise PermissionError("Forecast artifact belongs to a different workspace or run")
    return value


def _required_sha(run: Any) -> str:
    parameters = getattr(run, "job_parameters", None)
    provenance = parameters.get("provenance") if isinstance(parameters, Mapping) else None
    digest = provenance.get("artifact_sha256") if isinstance(provenance, Mapping) else None
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ValueError("Forecast run is missing a valid artifact SHA-256 provenance value")
    return digest


def _snapshot_bytes(run: Any, expected_sha: str, scope: dict[str, Any]) -> bytes:
    parameters = getattr(run, "job_parameters", None)
    snapshot = parameters.get("artifact_snapshot") if isinstance(parameters, Mapping) else None
    if not isinstance(snapshot, Mapping):
        raise ValueError("Forecast artifact is missing on disk and has no verified snapshot")
    body = snapshot.get("body")
    length = snapshot.get("bytes")
    digest = snapshot.get("sha256")
    if not isinstance(body, str) or not isinstance(length, int) or isinstance(length, bool):
        raise ValueError("Forecast artifact snapshot has invalid body or byte length")
    if len(body) > MAX_ARTIFACT_BYTES:
        raise ValueError("Forecast artifact snapshot exceeds 1 MiB")
    if snapshot.get("format") != ARTIFACT_FORMAT or not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ValueError("Forecast artifact snapshot has invalid format or digest")
    raw = body.encode("utf-8", errors="strict")
    if len(raw) != length or len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Forecast artifact snapshot byte length is invalid")
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != digest or actual_sha != expected_sha:
        raise ValueError("Forecast artifact snapshot SHA-256 does not match provenance")
    _decode_artifact(raw, scope)
    return raw


def save_run_artifact(run: Any, payload: Mapping[str, Any], *, base_dir: Any, artifacts_dir: Any) -> None:
    """Atomically write a scoped JSON artifact and store its verified snapshot."""
    if not isinstance(payload, Mapping):
        raise ValueError("Forecast artifact payload must be a mapping")
    if payload.get("format") != ARTIFACT_FORMAT:
        raise ValueError("Unsupported forecast artifact format")
    scope = _scope_for(run)
    try:
        artifact = json.loads(json.dumps(dict(payload), ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Forecast artifact payload must contain strict finite JSON values") from exc
    artifact["scope"] = scope
    _check_finite(artifact)
    try:
        body = json.dumps(artifact, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
        raw = body.encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Forecast artifact payload cannot be encoded as strict UTF-8 JSON") from exc
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Forecast artifact exceeds 1 MiB")
    digest = hashlib.sha256(raw).hexdigest()
    base, artifact_root = _trusted_directories(base_dir, artifacts_dir)
    artifact_root.mkdir(parents=True, exist_ok=True)
    # Re-resolve after creation to ensure an existing symlink cannot redirect writes.
    artifact_root = artifact_root.resolve()
    try:
        artifact_root.relative_to(base)
    except ValueError as exc:
        raise PermissionError("Artifact directory escapes base_dir") from exc
    attempt = uuid.uuid4().hex
    filename = f"run_{scope['run_id']}_{attempt}.json"
    destination = artifact_root / filename
    descriptor, temporary_name = tempfile.mkstemp(prefix=".forecast-", suffix=".tmp", dir=artifact_root)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

    relative = destination.relative_to(base).as_posix()
    parameters = getattr(run, "job_parameters", None)
    updated = dict(parameters) if isinstance(parameters, Mapping) else {}
    provenance = updated.get("provenance")
    updated_provenance = dict(provenance) if isinstance(provenance, Mapping) else {}
    updated_provenance["artifact_sha256"] = digest
    updated["provenance"] = updated_provenance
    updated["artifact_snapshot"] = {"body": body, "bytes": len(raw), "format": ARTIFACT_FORMAT, "sha256": digest}
    run.artifact_path = relative
    run.job_parameters = updated


def load_run_artifact(run: Any, *, base_dir: Any, artifacts_dir: Any) -> dict[str, Any]:
    """Load and verify an artifact from disk or its bounded metadata snapshot."""
    base, artifact_root = _trusted_directories(base_dir, artifacts_dir)
    path = _validated_artifact_path(run, base, artifact_root)
    scope = _scope_for(run)
    expected_sha = _required_sha(run)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_ARTIFACT_BYTES + 1)
    except FileNotFoundError:
        raw = _snapshot_bytes(run, expected_sha, scope)
    else:
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("Forecast artifact exceeds 1 MiB")
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError("Forecast artifact SHA-256 does not match run provenance")
    return _decode_artifact(raw, scope)

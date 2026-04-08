# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/lib-opnsense
"""Core cross-cutting concerns — independently reusable components.

Each module in this package has ZERO imports from managers/ or client.py.
They can be used standalone in any context (CLI tools, Ansible, Terraform, CI).

Modules:
    identity        — IdentityResolver: composite match key lookup
    diff            — DiffEngine: state comparison + vendor normalization
    redaction       — Redactor: unified field redaction with configurable rules
    validation      — FieldValidator protocol + registry + built-in types
    endpoint        — EndpointResolver: URL construction from config
    logging_helpers — ManagerLogBuilder: structured log dict construction
"""

from opnsense.core.diff import DiffEngine
from opnsense.core.endpoint import EndpointConfig, EndpointResolver
from opnsense.core.identity import IdentityResolver
from opnsense.core.logging_helpers import ManagerLogBuilder
from opnsense.core.redaction import Redactor
from opnsense.core.validation import FieldValidator, ValidatorRegistry

__all__ = [
    "DiffEngine",
    "EndpointConfig",
    "EndpointResolver",
    "FieldValidator",
    "IdentityResolver",
    "ManagerLogBuilder",
    "Redactor",
    "ValidatorRegistry",
]

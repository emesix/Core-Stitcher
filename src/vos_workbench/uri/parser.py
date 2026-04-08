from __future__ import annotations

import re
from typing import Literal, cast

from pydantic import BaseModel

type SchemeType = Literal["module", "secret", "system", "capability"]

VALID_SCHEMES = {"module", "secret", "system", "capability"}
URI_PATTERN = re.compile(r"^([a-z]+)://(.+)$")
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


class VosReference(BaseModel):
    scheme: Literal["module", "secret", "system", "capability"]
    authority: str | None = None
    path: str
    raw: str

    @classmethod
    def parse(cls, uri: str) -> VosReference:
        match = URI_PATTERN.match(uri)
        if not match:
            raise ValueError(f"Invalid VOS URI: {uri!r}")

        scheme = match.group(1)
        remainder = match.group(2)

        if scheme not in VALID_SCHEMES:
            raise ValueError(f"Unknown scheme: {scheme!r} in {uri!r}")

        valid_scheme = cast("SchemeType", scheme)

        if valid_scheme == "module":
            return cls._parse_module(remainder, uri)
        elif valid_scheme == "secret":
            return cls._parse_secret(remainder, uri)
        else:
            # system:// and capability:// have no authority
            return cls(scheme=valid_scheme, authority=None, path=remainder, raw=uri)

    @classmethod
    def _parse_module(cls, remainder: str, raw: str) -> VosReference:
        if remainder.startswith("name/"):
            path = remainder[5:]
            return cls(scheme="module", authority="name", path=path, raw=raw)
        elif remainder.startswith("uuid/"):
            path = remainder[5:].lower()
            if not UUID_PATTERN.match(path):
                raise ValueError(f"Invalid UUID in module URI: {raw!r}")
            return cls(scheme="module", authority="uuid", path=path, raw=raw)
        else:
            # Shorthand: module://foo → module://name/foo
            return cls(scheme="module", authority="name", path=remainder, raw=raw)

    @classmethod
    def _parse_secret(cls, remainder: str, raw: str) -> VosReference:
        slash_idx = remainder.find("/")
        if slash_idx == -1:
            raise ValueError(f"Secret URI must have provider/key format: {raw!r}")
        authority = remainder[:slash_idx]
        path = remainder[slash_idx + 1 :]
        return cls(scheme="secret", authority=authority, path=path, raw=raw)

    @classmethod
    def validate_uri(cls, uri: str) -> bool:
        try:
            cls.parse(uri)
            return True
        except ValueError:
            return False

    def __str__(self) -> str:
        if self.scheme == "module":
            return f"module://{self.authority}/{self.path}"
        elif self.scheme == "secret":
            return f"secret://{self.authority}/{self.path}"
        else:
            return f"{self.scheme}://{self.path}"

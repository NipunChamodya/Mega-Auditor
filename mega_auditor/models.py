from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class LinkTarget:
    kind: str
    handle: str
    key: str = ""
    sub: str = ""
    sub_kind: str = ""
    sources: set[str] = field(default_factory=set)

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.handle}:{self.sub}"

    @property
    def key_state(self) -> str:
        if not self.key:
            return "none"
        expected = 22 if self.kind == "folder" else 43
        return "format_plausible" if len(self.key) == expected else "bad_format"

    @property
    def link(self) -> str:
        value = f"https://mega.nz/{self.kind}/{self.handle}"
        if self.key:
            value += "#" + self.key
        if self.sub:
            value += f"/{self.sub_kind or 'folder'}/{self.sub}"
        return value

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sources"] = sorted(self.sources)
        d.update(id=self.id, link=self.link, key_state=self.key_state)
        return d

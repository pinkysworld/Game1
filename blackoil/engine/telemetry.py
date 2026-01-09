from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EventEntry:
    day: int
    category: str
    message: str
    amount: int | None = None


@dataclass
class TelemetryLog:
    entries: list[EventEntry] = field(default_factory=list)

    def add(self, day: int, category: str, message: str, amount: int | None = None) -> None:
        self.entries.append(EventEntry(day=day, category=category, message=message, amount=amount))

    def to_csv(self, path: str | Path) -> None:
        with Path(path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["day", "category", "message", "amount"])
            for entry in self.entries:
                writer.writerow([entry.day, entry.category, entry.message, entry.amount or ""])

"""Generates the three synthetic specimen-format document images used by
the sample case (I-94, I-797, passport bio page). Run once, from repo root:

    .venv/bin/python fixtures/sample_case/generate_specimens.py

Requires Pillow (dev-only tool; not imported by agent/ at runtime — see
pyproject.toml's `dev` extra). Output PNGs are checked into
fixtures/sample_case/specimens/ so tests and the demo don't depend on
re-running this script.

All names, numbers, and dates below are invented and consistent across the
three documents only to make the discrepancy check meaningful (see
docs/architecture-spec.md §7): CBP cut the I-94 admit-until date to match
the passport expiry, producing the 55-day gap against the I-797 validity
end date that the demo flags.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).parent / "specimens"
SCENARIOS_DIR = Path(__file__).parent / "scenarios"

_FONT = ImageFont.load_default()
_FONT_LARGE = ImageFont.load_default(size=22)


def _render(title: str, lines: list[tuple[str, str]], out_name: str, out_dir: Path = OUT_DIR) -> None:
    """Draws a specimen. A value of SMUDGE renders an illegible gray block
    instead of text (used for the 'ambiguous' scenario)."""
    width, height = 1100, 140 + 60 * len(lines)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width - 1, height - 1], outline="black", width=2)
    draw.text((30, 25), title, fill="black", font=_FONT_LARGE)
    draw.line([(30, 70), (width - 30, 70)], fill="black", width=1)
    y = 100
    for label, value in lines:
        draw.text((30, y), f"{label}:", fill="black", font=_FONT)
        if value is SMUDGE:
            for i in range(6):
                draw.rectangle([320 + i * 22, y - 4 + (i % 3) * 3, 340 + i * 22, y + 14 - (i % 2) * 4], fill=(150 + i * 10, 150 + i * 10, 150 + i * 10))
            draw.line([(318, y + 6), (460, y + 4)], fill=(120, 120, 120), width=5)
        else:
            draw.text((320, y), value, fill="black", font=_FONT)
        y += 45
    out_dir.mkdir(parents=True, exist_ok=True)
    img.save(out_dir / out_name)


SMUDGE = object()


def _person_docs(admit_until: str, valid_to: str, passport_exp, out_dir: Path, serial: str = "1234567890") -> None:
    _render(
        "Form I-94 Arrival/Departure Record",
        [
            ("Family Name", "RIVERA"),
            ("Given Name", "JORDAN A"),
            ("Admission Class", "H-1B"),
            ("I-94 Record Number", serial),
            ("Admit Until Date", admit_until),
        ],
        "i94.png",
        out_dir,
    )
    _render(
        "Form I-797 Notice of Action (Approval Notice)",
        [
            ("Receipt Number", f"EAC{serial}"),
            ("Beneficiary", "RIVERA, JORDAN A"),
            ("Petitioner", "Example Corp"),
            ("Notice Type", "Approval Notice"),
            ("Valid From", "12/29/2023"),
            ("Valid To", valid_to),
        ],
        "i797.png",
        out_dir,
    )
    _render(
        "Passport",
        [
            ("Surname", "RIVERA"),
            ("Given Names", "JORDAN A"),
            ("Passport No.", f"X{serial[:7]}"),
            ("Date of Birth", "15 MAR 1990"),
            ("Date of Expiration", passport_exp),
        ],
        "passport.png",
        out_dir,
    )


def generate_scenarios() -> None:
    """The extra bundled scenarios (agent/packs/immigration/scenarios.py).
    The default 'discrepant' set in specimens/ is left untouched so its
    recorded response and hashes stay valid."""
    # matching: CBP admitted the traveler through the full petition validity.
    _person_docs("12/28/2026", "12/28/2026", "03 NOV 2027", SCENARIOS_DIR / "matching", serial="2234567891")
    # ambiguous: the passport's expiration line is illegible.
    _person_docs("11/03/2026", "12/28/2026", SMUDGE, SCENARIOS_DIR / "ambiguous", serial="3234567892")
    print(f"Wrote scenario specimens under {SCENARIOS_DIR}")


def main() -> None:
    import sys

    if "--scenarios-only" in sys.argv or "--all" not in sys.argv:
        generate_scenarios()
        if "--all" not in sys.argv:
            return
    _render(
        "Form I-94 Arrival/Departure Record",
        [
            ("Family Name", "RIVERA"),
            ("Given Name", "JORDAN A"),
            ("Admission Class", "H-1B"),
            ("I-94 Record Number", "1234567890"),
            ("Admit Until Date", "11/03/2026"),
        ],
        "i94.png",
    )
    _render(
        "Form I-797 Notice of Action (Approval Notice)",
        [
            ("Receipt Number", "EAC1234567890"),
            ("Beneficiary", "RIVERA, JORDAN A"),
            ("Petitioner", "Example Corp"),
            ("Notice Type", "Approval Notice"),
            ("Valid From", "12/29/2023"),
            ("Valid To", "12/28/2026"),
        ],
        "i797.png",
    )
    _render(
        "Passport",
        [
            ("Surname", "RIVERA"),
            ("Given Names", "JORDAN A"),
            ("Passport No.", "X1234567"),
            ("Date of Birth", "15 MAR 1990"),
            ("Date of Expiration", "03 NOV 2026"),
        ],
        "passport.png",
    )
    print(f"Wrote 3 specimen images to {OUT_DIR}")
    generate_scenarios()


if __name__ == "__main__":
    main()

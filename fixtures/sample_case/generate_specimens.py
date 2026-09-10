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

_FONT = ImageFont.load_default()
_FONT_LARGE = ImageFont.load_default(size=22)


def _render(title: str, lines: list[tuple[str, str]], out_name: str) -> None:
    width, height = 1100, 140 + 60 * len(lines)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width - 1, height - 1], outline="black", width=2)
    draw.text((30, 25), title, fill="black", font=_FONT_LARGE)
    draw.line([(30, 70), (width - 30, 70)], fill="black", width=1)
    y = 100
    for label, value in lines:
        draw.text((30, y), f"{label}:", fill="black", font=_FONT)
        draw.text((320, y), value, fill="black", font=_FONT)
        y += 45
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT_DIR / out_name)


def main() -> None:
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


if __name__ == "__main__":
    main()

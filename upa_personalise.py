#!/usr/bin/env python3
"""
UPA Arts ONE — Personalisation Script
======================================
Reads student names from your order PDF (or a simple text/CSV list),
patches the correct XCF template for each size, and saves ready-to-print
PNGs into a timestamped folder inside your print-today directory.

Requirements:
    pip install pypdf pillow

Note: No GIMP required — uses Pillow for PNG rendering.

GIMP is used for the final XCF → PNG export, so it must be installed.
(It's already on your Mac — this script calls it silently in batch mode.)

Usage:
    python3 upa_personalise.py
    python3 upa_personalise.py --names "Alice,Bob,Charlie" --size adult
    python3 upa_personalise.py --pdf path/to/order.pdf
"""

import argparse
import os
import re
import struct
import sys
from datetime import datetime
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────────────────

# Folder containing your XCF template files
TEMPLATES_DIR = Path("/Users/soul2sole/Dropbox/DTF Files/UPA/logos/gimp files")

# Output folder — a timestamped subfolder will be created here
OUTPUT_DIR = Path("/Users/soul2sole/Dropbox/DTF Files/print today")

# XCF template filenames — update these if your filenames differ
TEMPLATES = {
    "child":    "childs_FOR_personalization_190mm____85mm_combined_logo_.xcf",
    "adult":    "adult__FOR__personlalization_245mm____90mm_combined_logo_.xcf",
    "xl_adult": "xl_adult__FOR__personlalization_275mm___100_mm_combined_logo_.xcf",
}

# The regex that finds the student name markup in each XCF template.
# If your other templates use a different span format, add entries here.
NAME_MARKUP_PATTERN = rb'\(markup "<markup><span size=\\"(\d+)\\">([^<]+)</span></markup>"\)'

# ── XCF Patching ─────────────────────────────────────────────────────────────

# ── Template PNG base files ───────────────────────────────────────────────────
# The script uses your exported PNG files as a base, paints over the old name
# region with black, then draws the new name in white. No GIMP needed.
#
# These PNGs must exist in TEMPLATES_DIR alongside the XCF files.
TEMPLATE_PNGS = {
    "child":    "childs_FOR_personalization_190mm____85mm_combined_logo_.png",
    "adult":    "adult__FOR__personlalization_245mm____90mm_combined_logo_.png",
    "xl_adult": "xl_adult__FOR__personlalization_275mm___100_mm_combined_logo_.png",
}

# Name layer positions and sizes extracted from the XCF files (pixels at 300dpi)
# Format: list of (x, y, width, height) — one entry per name instance in the template
NAME_REGIONS = {
    "child":    [(2817, 1982, 389, 94), (3437, 1050, 389, 94)],
    "adult":    [(3551, 1173, 341, 111), (2852, 2057, 341, 111)],
    "xl_adult": [(3479, 1583, 541, 134)],
}

# Font sizes in pixels (derived from XCF pango units at 300dpi)
NAME_FONT_PX = {
    "child":    83,
    "adult":    99,
    "xl_adult": 119,
}

def find_font(size_px: int):
    """Find Arial Regular, with fallbacks for other systems."""
    from PIL import ImageFont

    # Arial Regular — standard on every Mac
    candidates = [
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        # Windows / cross-platform fallbacks
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        # If Arial isn't found, use Liberation Sans Regular (metric-compatible)
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in candidates:
        if Path(path).exists():
            try:
                font = ImageFont.truetype(path, size_px)
                print(f"  Using font: {path}")
                return font
            except Exception:
                continue

    print("  ⚠  Arial not found — using Pillow default font")
    return ImageFont.load_default()


def render_name_on_png(template_png: Path, new_name: str, size_key: str, output_png: Path):
    """
    Paint the new student name onto the template PNG.
    Blacks out each name region then draws white text centred in it.
    """
    from PIL import Image, ImageDraw

    img = Image.open(template_png).convert("RGB")
    draw = ImageDraw.Draw(img)

    regions = NAME_REGIONS[size_key]
    font_px = NAME_FONT_PX[size_key]
    font = find_font(font_px)
    name_upper = new_name.upper()

    for (rx, ry, rw, rh) in regions:
        # Add padding so we fully cover the old text
        pad = 10
        draw.rectangle(
            [rx - pad, ry - pad, rx + rw + pad, ry + rh + pad],
            fill=(0, 0, 0)
        )
        # Always use the same font size — centre the text, allow overflow for long names
        bbox = draw.textbbox((0, 0), name_upper, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        tx = rx + (rw - text_w) // 2
        ty = ry + (rh - text_h) // 2
        draw.text((tx, ty), name_upper, fill=(255, 255, 255), font=font)

    # Convert to pure black & white, then transparent
    # threshold=200 keeps only near-white pixels, eliminating all anti-aliasing grey
    import numpy as np
    arr = np.array(img)
    # Any pixel with brightness below 200 becomes pure black, above becomes pure white
    bright = arr.mean(axis=2)
    arr[bright < 200] = [0, 0, 0]
    arr[bright >= 200] = [255, 255, 255]
    img = Image.fromarray(arr).convert("RGBA")
    arr_a = np.array(img)
    arr_a[arr_a[:, :, 0] == 0, 3] = 0  # make black pixels transparent
    img = Image.fromarray(arr_a)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_png), "PNG", dpi=(300, 300))


def patch_xcf(template_path: Path, new_name: str, output_xcf: Path):
    """
    Read the XCF template, replace the student name text layer,
    write the patched XCF to output_xcf.
    """
    with open(template_path, "rb") as f:
        data = f.read()

    match = re.search(NAME_MARKUP_PATTERN, data)
    if not match:
        raise ValueError(
            f"Could not find name markup in {template_path.name}.\n"
            "Check that NAME_MARKUP_PATTERN matches this template."
        )

    old_name_bytes = match.group(2)  # group(1) is the font size, group(2) is the name
    old_markup = match.group(0)
    new_name_bytes = new_name.upper().encode("utf-8")
    new_markup = old_markup.replace(old_name_bytes, new_name_bytes)

    name_delta = len(new_name_bytes) - len(old_name_bytes)

    # Find PROP_TEXT (type 21) just before the markup
    prop_offset = None
    for offset in range(match.start(), max(0, match.start() - 300), -1):
        if struct.unpack(">I", data[offset : offset + 4])[0] == 21:
            prop_offset = offset
            break

    if prop_offset is None:
        raise ValueError("Could not find PROP_TEXT header in XCF.")

    old_payload_len = struct.unpack(">I", data[prop_offset + 4 : prop_offset + 8])[0]
    new_payload_len = old_payload_len + name_delta

    # Find the inner payload string length (just after the property name "gimp-text-layer\0")
    # Pattern: prop_type(4) + prop_len(4) + name_len(4) + "gimp-text-layer\0" + unknown(4) + inner_len(4)
    inner_search_start = prop_offset + 8
    inner_search_end = match.start()
    inner_len_offset = None
    # The inner length is the largest 4-byte big-endian value in this region
    # that's close to the actual payload size (around 900–1100 bytes)
    for i in range(inner_search_start, inner_search_end - 4):
        val = struct.unpack(">I", data[i : i + 4])[0]
        if 500 < val < 2000:
            inner_len_offset = i

    # Find ALL occurrences of the name markup (some templates have it twice)
    all_matches = list(re.finditer(re.escape(old_markup), data))
    n_replacements = len(all_matches)

    # Build the patched binary — replace all occurrences
    result = data.replace(old_markup, new_markup)  # replaces all

    # Update outer PROP_TEXT length for each occurrence
    # Each replacement shifts subsequent offsets by name_delta, so track cumulative shift
    cumulative_shift = 0
    for match_inst in all_matches:
        adjusted_offset = prop_offset + cumulative_shift
        old_payload_len_i = struct.unpack(">I", result[adjusted_offset + 4 : adjusted_offset + 8])[0]
        result = (
            result[: adjusted_offset + 4]
            + struct.pack(">I", old_payload_len_i + name_delta)
            + result[adjusted_offset + 8 :]
        )
        # Update inner string length if found
        if inner_len_offset is not None:
            adjusted_inner = inner_len_offset + cumulative_shift
            old_inner = struct.unpack(">I", result[adjusted_inner : adjusted_inner + 4])[0]
            result = (
                result[:adjusted_inner]
                + struct.pack(">I", old_inner + name_delta)
                + result[adjusted_inner + 4 :]
            )
        cumulative_shift += name_delta
        # For subsequent occurrences, find the next PROP_TEXT and inner_len
        # by re-scanning from the next match position
        if match_inst != all_matches[-1]:
            next_match_pos = all_matches[all_matches.index(match_inst) + 1].start() + cumulative_shift
            prop_offset = None
            for offset in range(next_match_pos, max(0, next_match_pos - 300), -1):
                if struct.unpack(">I", result[offset : offset + 4])[0] == 21:
                    prop_offset = offset
                    break
            inner_len_offset = None
            if prop_offset is not None:
                for i in range(prop_offset + 8, next_match_pos - 4):
                    val = struct.unpack(">I", result[i : i + 4])[0]
                    if 500 < val < 2000:
                        inner_len_offset = i

    output_xcf.parent.mkdir(parents=True, exist_ok=True)
    with open(output_xcf, "wb") as f:
        f.write(result)





# ── PDF Name Extraction ───────────────────────────────────────────────────────

def names_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract personalisation names and garment sizes from a Soul2sole invoice PDF.

    Looks for:
      - "Personalisation: Ariana"  → name = "Ariana"
      - "Arts1 T Shirt (Child)"    → size = "child"
      - "Arts1 T Shirt (Adult)"    → size = "adult"
      - Size line "Size: XL" etc   → used to distinguish xl_adult from adult

    Returns a list of dicts: [{"name": "Ariana", "size": "child"}, ...]
    One entry per personalisation line found in the PDF.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        print("  pypdf not installed — run: pip install pypdf")
        sys.exit(1)

    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    print(f"\n  — PDF text extracted ({len(text)} chars) —")

    entries = []

    # Find every personalisation name: "Personalisation: Firstname"
    # The invoice puts this on its own line in the buyer notes block
    name_matches = re.findall(
        r"Personalisation:\s*([A-Za-z][A-Za-z\s'\-]{0,40}?)(?:\s*\n|\s*$|\s{2,})",
        text,
        re.IGNORECASE,
    )

    # Find garment lines: "Arts1 T Shirt (Child)" / "(Adult)" / "(XL Adult)" etc
    # These appear in the items table; order matches personalisation order
    garment_matches = re.findall(
        r"Arts1[^(\n]*\(\s*((?:XL\s+)?(?:Adult|Child))\s*\)",
        text,
        re.IGNORECASE,
    )

    # Also look for size lines to catch XL within Adult garments
    # "Size: XL" appearing near an Adult garment upgrades it to xl_adult
    size_lines = re.findall(r"Size:\s*([^\n]+)", text, re.IGNORECASE)

    def classify_size(garment_str: str, size_hint: str = "") -> str:
        g = garment_str.lower()
        s = size_hint.lower()
        if "xl" in g or "xl" in s:
            return "xl_adult"
        if "child" in g or "junior" in g or "kid" in g:
            return "child"
        return "adult"

    if name_matches and garment_matches:
        # Pair each name with its corresponding garment size
        for i, name in enumerate(name_matches):
            name = name.strip().title()
            garment = garment_matches[i] if i < len(garment_matches) else "Adult"
            size_hint = size_lines[i] if i < len(size_lines) else ""
            size = classify_size(garment, size_hint)
            entries.append({"name": name, "size": size})
            print(f"    Found: {name!r}  →  {size}")

    elif name_matches:
        # Names found but couldn't parse garment — ask user for size
        print(f"\n  Found {len(name_matches)} name(s) but couldn't detect sizes.")
        print("  Enter size for all (child / adult / xl): ", end="")
        size = parse_size(input().strip() or "adult")
        for name in name_matches:
            entries.append({"name": name.strip().title(), "size": size})

    else:
        print("\n  ⚠  Could not find 'Personalisation: <name>' in this PDF.")
        print("  Check the PDF is a Soul2sole invoice, or use --names instead.\n")

    return entries


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_size(raw: str) -> str:
    raw = raw.lower().strip()
    if "xl" in raw:
        return "xl_adult"
    if "adult" in raw or "a" == raw:
        return "adult"
    if "child" in raw or "c" == raw or "junior" in raw or "kid" in raw:
        return "child"
    return "adult"


def main():
    parser = argparse.ArgumentParser(
        description="Generate personalised Arts ONE print files."
    )
    parser.add_argument("--pdf", help="Path to the order PDF")
    parser.add_argument("--names", help='Comma-separated names, e.g. "Alice,Bob"')
    parser.add_argument(
        "--size",
        default="adult",
        help="Size for all names when using --names: child | adult | xl_adult",
    )
    parser.add_argument(
        "--list",
        help=(
            'Path to a CSV or text file with one entry per line: '
            '"Name,size"  e.g. "Alice,adult"'
        ),
    )
    args = parser.parse_args()

    print("\n" + "═" * 55)
    print("  UPA Arts ONE — Personalisation")
    print("═" * 55 + "\n")

    # ── Collect entries ───────────────────────────────────────────────
    entries = []

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"ERROR: PDF not found: {pdf_path}")
            sys.exit(1)
        print(f"  Reading PDF: {pdf_path.name}")
        entries = names_from_pdf(pdf_path)

    elif args.list:
        list_path = Path(args.list)
        if not list_path.exists():
            print(f"ERROR: List file not found: {list_path}")
            sys.exit(1)
        for line in list_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            name = parts[0].title()
            size = parse_size(parts[1]) if len(parts) > 1 else parse_size(args.size)
            entries.append({"name": name, "size": size})

    elif args.names:
        size = parse_size(args.size)
        for n in args.names.split(","):
            n = n.strip().title()
            if n:
                entries.append({"name": n, "size": size})

    else:
        # Interactive mode
        print("  No input specified — entering interactive mode.\n")
        size = parse_size(
            input("  Size for this batch (child / adult / xl): ").strip() or "adult"
        )
        raw_names = input("  Student names (comma-separated): ").strip()
        for n in raw_names.split(","):
            n = n.strip().title()
            if n:
                entries.append({"name": n, "size": size})

    if not entries:
        print("  No entries to process. Exiting.")
        sys.exit(0)

    print(f"\n  {len(entries)} student(s) to process:\n")
    for e in entries:
        print(f"    {e['name']}  ({e['size']})")

    # ── Set up output folder ──────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    job_dir = OUTPUT_DIR / f"ArtsONE_personalised_{timestamp}"
    job_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  Output folder: {job_dir}\n")

    # ── Process each student ──────────────────────────────────────────
    errors = []
    done = 0

    for entry in entries:
        name = entry["name"]
        size = entry["size"]

        template_png_name = TEMPLATE_PNGS.get(size)
        if not template_png_name:
            errors.append(f"{name}: unknown size '{size}'")
            continue

        template_png = TEMPLATES_DIR / template_png_name
        if not template_png.exists():
            errors.append(f"{name}: template PNG not found — {template_png}")
            continue

        safe_name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
        png_out = job_dir / f"ArtsONE_{safe_name}_{size}.png"

        try:
            render_name_on_png(template_png, name, size, png_out)
            print(f"  ✓  {name}  ({size})  →  {png_out.name}")
            done += 1

        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"  ✗  {name}  —  {e}")

    # ── Summary ───────────────────────────────────────────────────────
    print("\n" + "═" * 55)
    print(f"  Done — {done} file{'s' if done != 1 else ''} saved.")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    ⚠  {e}")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    main()

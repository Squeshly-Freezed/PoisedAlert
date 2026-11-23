"""Draws Poised Alert's banner, laid out like Earshot's.

The logo on the left, the name and two lines of text on the right, on a dark background in
the logo's purple. The tagline uses the yellow of Poised Alert's name in chat (|cfffff468),
as Earshot's uses its own chat colour.

    python3 -I dev/make_banner.py

Reads media/logo.svg and writes media/banner.png (1280 x 640), for the top of the README,
the CurseForge description and GitHub's social preview.
Needs rsvg-convert (from librsvg) and the Inter fonts.
"""
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YELLOW = "#fff468"  # Poised Alert's name in chat


def logo_inner(svg_text):
    """The logo's contents without its outer <svg> tag, so it can sit inside the banner."""
    inner = re.sub(r"^\s*<svg[^>]*>", "", svg_text.strip(), count=1)
    return re.sub(r"</svg>\s*$", "", inner)


def banner_svg(logo_svg_text):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640">
  <rect width="1280" height="640" fill="#120d20"/>
  <g transform="translate(96 130) scale(0.74)">{logo_inner(logo_svg_text)}
  </g>
  <text x="560" y="300" font-family="Inter Display" font-weight="800" font-size="108" fill="#f7f3ff"
    letter-spacing="-2">Poised Alert</text>
  <text x="566" y="372" font-family="Inter" font-weight="500" font-size="38" fill="{YELLOW}">Hear the moment Poised is ready</text>
  <text x="566" y="424" font-family="Inter" font-weight="400" font-size="28" fill="#b7aacd">A rogue addon for WoW Forever</text>
</svg>
"""


def main():
    media = ROOT / "media"
    svg = banner_svg((media / "logo.svg").read_text(encoding="utf-8"))
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as f:
        f.write(svg)
    subprocess.run(["rsvg-convert", "-w", "1280", "-h", "640", "-o", str(media / "banner.png"), f.name],
                   check=True)
    Path(f.name).unlink()
    print("Wrote media/banner.png")


if __name__ == "__main__":
    main()

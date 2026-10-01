from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
BACKGROUND = ROOT / "launch-background-16x9.png"
USDC = ROOT.parents[2] / "static" / "images" / "usdc.png"
FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

INK = "#101712"
FOREST = "#104734"
CREAM = "#F4F0E6"
ORANGE = "#D95536"
LIME = "#B7F34A"
BLUE = "#1456C8"
MUTED = "#5C655F"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def rounded_label(draw: ImageDraw.ImageDraw, xy, text, fill, text_fill, size=22, outline=None):
    x, y = xy
    f = font(size, True)
    box = draw.textbbox((0, 0), text, font=f)
    width = box[2] + 42
    height = box[3] - box[1] + 28
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill=fill, outline=outline, width=2)
    draw.text((x + 21, y + 13 - box[1]), text, font=f, fill=text_fill)
    return width, height


def push_mark(draw: ImageDraw.ImageDraw, x: int, y: int, size: int):
    draw.rounded_rectangle((x, y, x + size, y + size), radius=size // 5, fill=CREAM, outline="#CCD2CB", width=2)
    s = size / 64
    pts = [(18, 49), (18, 15), (35, 15)]
    # A compact, deterministic rendering of the existing Push P mark.
    draw.line([(x + px*s, y + py*s) for px, py in pts], fill=FOREST, width=max(5, int(10*s)), joint="curve")
    draw.arc((x + 25*s, y + 14*s, x + 52*s, y + 43*s), -90, 90, fill=FOREST, width=max(5, int(9*s)))
    draw.rectangle((x + 46*s, y + 44*s, x + 54*s, y + 52*s), fill=ORANGE)


def stellar_mark(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, color: str):
    width = max(4, radius // 10)
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=color, width=width)
    for offset in (-radius // 3, radius // 3):
        draw.line((cx-radius-radius//3, cy+offset+radius//2, cx+radius+radius//3, cy+offset-radius//2), fill=color, width=width)


def paste_usdc(canvas: Image.Image, center: tuple[int, int], size: int):
    coin = Image.open(USDC).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, size - 2, size - 2), fill=255)
    coin.putalpha(mask)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    x = center[0] - size // 2
    y = center[1] - size // 2
    sd.ellipse((x + 12, y + 20, x + size + 12, y + size + 20), fill=(16, 23, 18, 45))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(coin, (x, y))


def master_png():
    canvas = Image.open(BACKGROUND).convert("RGBA").resize((1600, 900), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas)
    push_mark(draw, 72, 65, 58)
    draw.text((146, 70), "PUSH", font=font(32, True), fill=INK)
    draw.text((146, 107), "WORK RECORD", font=font(13, True), fill=MUTED)
    rounded_label(draw, (72, 180), "MVP / STELLAR TESTNET", FOREST, CREAM, 17)
    draw.text((68, 253), "PUSH IS", font=font(104, True), fill=INK, stroke_width=1)
    draw.text((68, 350), "LIVE.", font=font(154, True), fill=FOREST, stroke_width=1)
    draw.text((75, 535), "Brief. Deliver. Settle with a clear record.", font=font(29), fill=INK)
    draw.text((75, 582), "Now open for invite-only MVP testing on Stellar testnet.", font=font(21), fill=MUTED)
    rounded_label(draw, (72, 659), "EXPLORE  pushearn.xyz", LIME, INK, 20)
    draw.text((75, 817), "@PushN_", font=font(18, True), fill=FOREST)
    draw.text((185, 818), "Independent project · not affiliated with SDF", font=font(15), fill=MUTED)

    # Apply official asset imagery and a clean Stellar network symbol to the blank render.
    paste_usdc(canvas, (1012, 528), 142)
    stellar_mark(draw, 1422, 174, 58, CREAM)
    draw.text((1357, 248), "STELLAR", font=font(17, True), fill=CREAM)
    canvas.convert("RGB").save(ROOT / "push-live-x-1600x900.png", quality=96)


def square_png():
    bg = Image.open(BACKGROUND).convert("RGBA").resize((1080, 608), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (1080, 1080), CREAM)
    canvas.alpha_composite(bg, (0, 472))
    draw = ImageDraw.Draw(canvas)
    push_mark(draw, 62, 56, 56)
    draw.text((132, 60), "PUSH", font=font(31, True), fill=INK)
    rounded_label(draw, (62, 154), "MVP / STELLAR TESTNET", FOREST, CREAM, 16)
    draw.text((58, 224), "PUSH IS LIVE.", font=font(86, True), fill=INK)
    draw.text((62, 330), "Brief. Deliver. Settle with a clear record.", font=font(27), fill=FOREST)
    draw.text((62, 381), "Invite-only testing is now open.", font=font(20), fill=MUTED)
    rounded_label(draw, (62, 430), "pushearn.xyz", LIME, INK, 19)
    paste_usdc(canvas, (687, 803), 130)
    stellar_mark(draw, 927, 610, 48, CREAM)
    draw.text((62, 1027), "@PushN_   ·   Independent project · not affiliated with SDF", font=font(15), fill=MUTED)
    canvas.convert("RGB").save(ROOT / "push-live-square-1080x1080.png", quality=96)


def data_uri(path: Path) -> str:
    mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def svg_master():
    bg = data_uri(BACKGROUND)
    usdc = data_uri(USDC)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
<title>Push is live on Stellar testnet</title>
<image href="{bg}" width="1600" height="900" preserveAspectRatio="xMidYMid slice"/>
<g id="push-brand"><rect x="72" y="65" width="58" height="58" rx="12" fill="{CREAM}" stroke="#CCD2CB"/><text x="88" y="106" font-family="Arial" font-size="36" font-weight="700" fill="{FOREST}">P</text><rect x="116" y="106" width="8" height="8" fill="{ORANGE}"/><text x="146" y="96" font-family="Arial" font-size="32" font-weight="700" fill="{INK}">PUSH</text><text x="146" y="119" font-family="Arial" font-size="13" font-weight="700" fill="{MUTED}">WORK RECORD</text></g>
<g id="copy"><rect x="72" y="180" width="274" height="48" rx="24" fill="{FOREST}"/><text x="93" y="211" font-family="Arial" font-size="17" font-weight="700" fill="{CREAM}">MVP / STELLAR TESTNET</text><text x="68" y="337" font-family="Arial" font-size="104" font-weight="700" fill="{INK}">PUSH IS</text><text x="68" y="480" font-family="Arial" font-size="154" font-weight="700" fill="{FOREST}">LIVE.</text><text x="75" y="566" font-family="Arial" font-size="29" fill="{INK}">Brief. Deliver. Settle with a clear record.</text><text x="75" y="608" font-family="Arial" font-size="21" fill="{MUTED}">Now open for invite-only MVP testing on Stellar testnet.</text><rect x="72" y="659" width="278" height="53" rx="27" fill="{LIME}"/><text x="94" y="693" font-family="Arial" font-size="20" font-weight="700" fill="{INK}">EXPLORE  pushearn.xyz</text></g>
<defs><clipPath id="usdc-circle"><circle cx="1012" cy="528" r="71"/></clipPath></defs><g id="network-assets"><image href="{usdc}" x="941" y="457" width="142" height="142" clip-path="url(#usdc-circle)"/><g stroke="{CREAM}" fill="none" stroke-width="10"><circle cx="1422" cy="174" r="58"/><path d="M1345 214L1499 134M1345 178L1499 98"/></g><text x="1357" y="258" font-family="Arial" font-size="17" font-weight="700" fill="{CREAM}">STELLAR</text></g>
<g id="footer"><text x="75" y="837" font-family="Arial" font-size="18" font-weight="700" fill="{FOREST}">@PushN_</text><text x="185" y="837" font-family="Arial" font-size="15" fill="{MUTED}">Independent project · not affiliated with SDF</text></g>
</svg>'''
    (ROOT / "push-live-x-editable.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    master_png()
    square_png()
    svg_master()

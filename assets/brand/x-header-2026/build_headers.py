from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
LOGO = PROJECT / "static" / "images" / "push-logo.png"
BACKGROUND = PROJECT / "assets" / "campaigns" / "push-live-2026" / "launch-background-16x9.png"

W, H = 1500, 500
INK = "#101612"
FOREST = "#113D31"
CREAM = "#F3F0E8"
SHEET = "#FBFAF6"
LIME = "#BAF45A"
BLUE = "#2775CA"
ORANGE = "#D95536"
MUTED = "#667068"

FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, fill: str, bold: bool = False):
    draw.text(xy, value, font=font(size, bold), fill=fill)


def pixel_mark(size: int, colour: str) -> Image.Image:
    source = Image.open(LOGO).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    alpha = source.getchannel("A")
    mark = Image.new("RGBA", source.size, colour)
    mark.putalpha(alpha)
    return mark


def label(draw: ImageDraw.ImageDraw, x: int, y: int, value: str, fill: str, colour: str):
    f = font(17, True)
    box = draw.textbbox((0, 0), value, font=f)
    width = box[2] + 36
    draw.rounded_rectangle((x, y, x + width, y + 38), radius=19, fill=fill)
    draw.text((x + 18, y + 9), value, font=f, fill=colour)


def save(canvas: Image.Image, name: str):
    canvas.convert("RGB").save(ROOT / name, quality=96)


def dark_header():
    canvas = Image.new("RGBA", (W, H), INK)
    draw = ImageDraw.Draw(canvas)

    # Quiet drafting grid and a single signal rule keep the product language visible.
    for x in range(0, W, 72):
        draw.line((x, 0, x, H), fill="#17211B", width=1)
    for y in range(0, H, 72):
        draw.line((0, y, W, y), fill="#17211B", width=1)
    draw.rectangle((0, 0, 18, H), fill=ORANGE)

    mark = pixel_mark(64, SHEET)
    canvas.alpha_composite(mark, (356, 55))
    text(draw, (435, 66), "PUSH", 30, SHEET, True)
    label(draw, 570, 64, "STELLAR TESTNET MVP", FOREST, SHEET)

    text(draw, (355, 157), "BRIEF. DELIVER.", 68, SHEET, True)
    text(draw, (355, 227), "SETTLE.", 86, LIME, True)
    text(draw, (360, 340), "One clear record from agreement to payment.", 25, "#C8D1CB")
    text(draw, (360, 395), "pushearn.xyz", 24, SHEET, True)

    # The right-hand record is deliberately product-specific rather than generic crypto decoration.
    rx, ry, rw, rh = 1110, 95, 300, 315
    draw.rounded_rectangle((rx, ry, rx + rw, ry + rh), radius=28, fill="#18241E", outline="#34463B", width=2)
    text(draw, (rx + 28, ry + 26), "WORK RECORD", 15, "#AAB7AE", True)
    stages = [("01", "Brief locked", ORANGE), ("02", "Delivery attached", BLUE), ("03", "Payment verified", LIME)]
    for index, (number, copy, colour) in enumerate(stages):
        y = ry + 79 + index * 76
        draw.ellipse((rx + 28, y, rx + 58, y + 30), fill=colour)
        text(draw, (rx + 35, y + 7), number, 11, INK, True)
        text(draw, (rx + 76, y + 3), copy, 19, SHEET, True)
        if index < 2:
            draw.line((rx + 43, y + 31, rx + 43, y + 75), fill="#42564A", width=2)
    save(canvas, "push-x-header-dark-1500x500.png")


def cream_header():
    canvas = Image.open(BACKGROUND).convert("RGBA")
    # Crop the source to 3:1 while keeping the useful right-side physical objects.
    source_w, source_h = canvas.size
    crop_h = int(source_w / 3)
    top = max(0, (source_h - crop_h) // 2)
    canvas = canvas.crop((0, top, source_w, top + crop_h)).resize((W, H), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas)
    veil = Image.new("RGBA", (W, H), (243, 240, 232, 0))
    vd = ImageDraw.Draw(veil)
    vd.rectangle((0, 0, 860, H), fill=(243, 240, 232, 238))
    canvas.alpha_composite(veil)
    draw = ImageDraw.Draw(canvas)

    mark = pixel_mark(58, FOREST)
    canvas.alpha_composite(mark, (350, 58))
    text(draw, (422, 71), "PUSH", 28, INK, True)
    text(draw, (350, 153), "GOOD WORK", 65, INK, True)
    text(draw, (350, 218), "NEEDS A RECORD.", 62, FOREST, True)
    text(draw, (355, 316), "Briefs, delivery and settlement evidence—together.", 24, INK)
    label(draw, 350, 379, "INVITE-ONLY TESTING", FOREST, CREAM)
    text(draw, (585, 387), "pushearn.xyz", 20, INK, True)
    save(canvas, "push-x-header-cream-1500x500.png")


def product_header():
    canvas = Image.new("RGBA", (W, H), "#EAF1F5")
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((1070, -250, 1580, 260), fill="#D7E8F4")
    draw.ellipse((1240, 275, 1540, 575), fill="#DDF2C2")

    mark = pixel_mark(58, FOREST)
    canvas.alpha_composite(mark, (355, 55))
    text(draw, (428, 67), "PUSH", 29, INK, True)
    text(draw, (355, 153), "WORK MOVES", 68, INK, True)
    text(draw, (355, 223), "FORWARD.", 82, BLUE, True)
    text(draw, (360, 331), "Scope, delivery and payment in one accountable flow.", 24, "#33433A")
    text(draw, (360, 397), "pushearn.xyz", 23, FOREST, True)

    cards = [
        (1050, 79, "01", "BRIEF", "Terms recorded", ORANGE),
        (1110, 187, "02", "DELIVER", "Evidence attached", BLUE),
        (1170, 295, "03", "SETTLE", "Payment verified", FOREST),
    ]
    for x, y, number, title, copy, colour in cards:
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((x + 7, y + 10, x + 307, y + 102), radius=18, fill=(31, 61, 79, 30))
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        canvas.alpha_composite(shadow)
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((x, y, x + 300, y + 92), radius=18, fill=SHEET, outline="#C9D5DC", width=2)
        draw.rounded_rectangle((x + 18, y + 19, x + 70, y + 71), radius=13, fill=colour)
        text(draw, (x + 33, y + 36), number, 15, "#FFFFFF", True)
        text(draw, (x + 88, y + 19), title, 16, INK, True)
        text(draw, (x + 88, y + 48), copy, 16, MUTED)
    save(canvas, "push-x-header-product-1500x500.png")


def profile_avatar():
    size = 800
    canvas = Image.new("RGBA", (size, size), FOREST)
    draw = ImageDraw.Draw(canvas)
    # A restrained drafting grid keeps the avatar connected to the product system.
    for position in range(0, size, 100):
        draw.line((position, 0, position, size), fill="#194D3D", width=2)
        draw.line((0, position, size, position), fill="#194D3D", width=2)
    draw.rounded_rectangle((116, 116, 684, 684), radius=142, fill=CREAM)
    mark = pixel_mark(408, FOREST)
    canvas.alpha_composite(mark, (196, 176))
    draw.rectangle((557, 547, 617, 607), fill=ORANGE)
    save(canvas, "push-x-avatar-800x800.png")


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    dark_header()
    cream_header()
    product_header()
    profile_avatar()

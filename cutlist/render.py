from PIL import Image, ImageDraw, ImageFont

def render(sheet_w, sheet_h, layout, filename):
    SCALE = 4  # 1 sm = 4 px

    img_w = int(sheet_w * SCALE)
    img_h = int(sheet_h * SCALE)

    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)

    # ===== KATTA OYNA CHEGARASI =====
    draw.rectangle(
        [(0, 0), (img_w - 1, img_h - 1)],
        outline="black",
        width=3
    )

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    COLORS = [
        "#ff9999", "#99ff99", "#9999ff",
        "#ffff99", "#ff99ff", "#99ffff",
        "#ffc299", "#c299ff"
    ]

    # ===== BO‘LAKLARNI JOYLASHTIRISH =====
    for i, piece in enumerate(layout):
        x = piece["x"] * SCALE
        y = piece["y"] * SCALE
        w = piece["w"] * SCALE
        h = piece["h"] * SCALE

        color = COLORS[i % len(COLORS)]

        draw.rectangle(
            [(x, y), (x + w, y + h)],
            fill=color,
            outline="black",
            width=1
        )

        text = f"{piece['w']} x {piece['h']} sm"

        # ✅ PILLOW 10+ UCHUN TO‘G‘RI
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        draw.text(
            (x + (w - text_w) / 2, y + (h - text_h) / 2),
            text,
            fill="black",
            font=font
        )

    img.save(filename)

def optimize(sheet_w, sheet_h, parts):
    # 1. qty ni yoyib chiqamiz
    items = []
    for p in parts:
        for _ in range(p.get("qty", 1)):
            items.append({
                "w": p["w"],
                "h": p["h"]
            })

    # 2. Eng kattalaridan boshlaymiz
    items.sort(key=lambda x: x["w"] * x["h"], reverse=True)

    sheets = []
    current = []
    cursor_x = 0
    cursor_y = 0
    row_height = 0

    for item in items:
        placed = False

        for rotate in [False, True]:
            w = item["h"] if rotate else item["w"]
            h = item["w"] if rotate else item["h"]

            if cursor_x + w <= sheet_w and cursor_y + h <= sheet_h:
                current.append({
                    "x": cursor_x,
                    "y": cursor_y,
                    "w": w,
                    "h": h,
                    "label": f"{item['w']}x{item['h']}"
                })
                cursor_x += w
                row_height = max(row_height, h)
                placed = True
                break

        if not placed:
            cursor_x = 0
            cursor_y += row_height
            row_height = 0

            if cursor_y + item["h"] > sheet_h:
                sheets.append(current)
                current = []
                cursor_x = 0
                cursor_y = 0

            current.append({
                "x": cursor_x,
                "y": cursor_y,
                "w": item["w"],
                "h": item["h"],
                "label": f"{item['w']}x{item['h']}"
            })
            cursor_x += item["w"]
            row_height = item["h"]

    if current:
        sheets.append(current)

    return sheets

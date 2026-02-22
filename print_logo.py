def print_logo():
    with open("logo.txt", "r") as f:
        art = f.read().splitlines()

    # Define start and end colors (DeepskyBlue to Fuchsia)
    start_rgb = (0, 191, 255)  # DeepskyBlue
    end_rgb = (255, 0, 255)  # Fuchsia

    # Flatten the art into a single list of characters (excluding newlines) to compute gradient positions
    flat_chars = [c for line in art for c in line]
    total = len(flat_chars) - 1 if flat_chars else 0

    def lerp(start, end, t):
        return int(start + (end - start) * t)

    # Helper to generate ANSI true‑color escape sequence
    def rgb_escape(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    # Print the art with a smooth gradient
    idx = 0
    for line in art:
        line_out = []
        for ch in line:
            t = idx / total if total else 0
            r = lerp(start_rgb[0], end_rgb[0], t)
            g = lerp(start_rgb[1], end_rgb[1], t)
            b = lerp(start_rgb[2], end_rgb[2], t)
            line_out.append(f"{rgb_escape(r, g, b)}{ch}\033[0m")
            idx += 1
        print("".join(line_out))

import os
import io
import re
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

def get_font(size, bold=False, weight=None):
    font_candidates = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_fonts = os.path.join(base_dir, 'assets', 'fonts')

    if weight == 'medium':
        cand_names = ['Inter-Medium.ttf', 'Inter-SemiBold.ttf', 'Inter-Regular.ttf']
    elif weight == 'semibold' or (bold and weight != 'bold'):
        cand_names = ['Inter-SemiBold.ttf', 'Inter-Bold.ttf', 'Inter-Medium.ttf']
    elif bold:
        cand_names = ['Inter-Bold.ttf', 'Inter-SemiBold.ttf']
    else:
        cand_names = ['Inter-Regular.ttf', 'Inter-Medium.ttf']

    for name in cand_names:
        font_candidates.append(os.path.join(assets_fonts, name))

    if os.name == 'nt':
        win_dir = os.environ.get('WINDIR', 'C:\\Windows')
        fonts_dir = os.path.join(win_dir, 'Fonts')
        for name in cand_names:
            font_candidates.append(os.path.join(fonts_dir, name))
        font_candidates.extend([
            os.path.join(fonts_dir, 'segoeuib.ttf' if bold else 'segoeui.ttf'),
            os.path.join(fonts_dir, 'arialbd.ttf' if bold else 'arial.ttf'),
            os.path.join(fonts_dir, 'calibrib.ttf' if bold else 'calibri.ttf')
        ])
    else:
        # Linux / Vercel serverless environment
        font_candidates.extend([
            f'/usr/share/fonts/truetype/inter/Inter-{"Bold" if bold else ("Medium" if weight == "medium" else "Regular")}.ttf',
            f'/usr/share/fonts/truetype/dejavu/DejaVuSans{"-Bold" if bold else ""}.ttf',
            f'/usr/share/fonts/truetype/liberation/LiberationSans-{"Bold" if bold else "Regular"}.ttf',
            f'/usr/share/fonts/truetype/freefont/FreeSans{"Bold" if bold else ""}.ttf',
            f'/usr/share/fonts/dejavu/DejaVuSans{"-Bold" if bold else ""}.ttf'
        ])
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, int(size))
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=int(size))
    except Exception:
        return ImageFont.load_default()

def get_emoji_font(size):
    candidates = []
    if os.name == 'nt':
        win_dir = os.environ.get('WINDIR', 'C:\\Windows')
        candidates.append(os.path.join(win_dir, 'Fonts', 'seguiemj.ttf'))
    else:
        candidates.extend([
            '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',
            '/usr/share/fonts/truetype/noto-emoji/NotoColorEmoji.ttf',
            '/usr/share/fonts/google-noto-color-emoji-fonts/NotoColorEmoji.ttf'
        ])
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, int(size))
            except Exception:
                continue
    return get_font(size)

def is_emoji_char(char):
    cp = ord(char)
    return (
        0x1F000 <= cp <= 0x1FFFF or
        0x2600 <= cp <= 0x27BF or
        0x2300 <= cp <= 0x23FF or
        0x2B50 <= cp <= 0x2B55 or
        0xFE00 <= cp <= 0xFE0F
    )

def measure_text_with_emojis(draw, text, font_reg, font_emj):
    w = 0
    max_h = 0
    spans = []
    curr_emj = None
    curr_str = ''
    for ch in text:
        emj = is_emoji_char(ch)
        if emj == curr_emj:
            curr_str += ch
        else:
            if curr_str:
                spans.append((curr_str, curr_emj))
            curr_str = ch
            curr_emj = emj
    if curr_str:
        spans.append((curr_str, curr_emj))
    for s, emj in spans:
        f = font_emj if emj else font_reg
        bbox = draw.textbbox((0, 0), s, font=f)
        w += (bbox[2] - bbox[0])
        max_h = max(max_h, bbox[3] - bbox[1])
    return w, max_h

def draw_text_with_emojis(draw, xy, text, font_reg, font_emj, fill):
    x, y = xy
    spans = []
    curr_emj = None
    curr_str = ''
    for ch in text:
        emj = is_emoji_char(ch)
        if emj == curr_emj:
            curr_str += ch
        else:
            if curr_str:
                spans.append((curr_str, curr_emj))
            curr_str = ch
            curr_emj = emj
    if curr_str:
        spans.append((curr_str, curr_emj))
        
    for s, emj in spans:
        f = font_emj if emj else font_reg
        draw.text((x, y), s, font=f, fill=fill)
        bbox = draw.textbbox((x, y), s, font=f)
        x += (bbox[2] - bbox[0])
    return x

def parse_script(text):
    if not text:
        return "Contact", [], []

    raw_lines = text.splitlines()
    messages = []
    contact_name = "Contact"
    contacts_seen = []
    
    first_non_msg = True
    last_side = 1
    last_name = ""
    skip_next = False
    section_idx = 0

    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith('---'):
            section_idx += 1
            continue

        lower = line.lower()
        if lower in ('wing', 'rizz', 'plug', 'wing (bot)'):
            skip_next = True
            continue

        if skip_next:
            skip_next = False
            # If this line was just a keyword/voice name like 'alex', skip it
            if not re.match(r'^\[?[12]\]?[:\.\-\>]', line) and ':' not in line and '>' not in line:
                continue

        # 1. Image message check: e.g. "1: img: photo1.jpg" or "img: photo1.jpg"
        img_match = re.match(r'^(?:\[?([12])\]?[:\.\-\>]\s*)?img:\s*(.+)$', line, re.IGNORECASE)
        if img_match:
            side = int(img_match.group(1) or last_side or 1)
            img_name = img_match.group(2).strip()
            messages.append({
                'side': side,
                'name': '',
                'text': img_name,
                'audio_text': '',
                'is_img': True,
                'contact_name': contact_name,
                'section_idx': section_idx
            })
            last_side = side
            first_non_msg = False
            continue

        # 2. Actual conversation message: must start with side number (1 or 2)
        # e.g. "1: Natasha > Hello", "2: Adam > Yeah", "1: Natasha: Hello", "1. Natasha > Hello", "[1] Natasha > Hello", "1: Hello"
        side_prefix_m = re.match(r'^\[?([12])\]?[:\.\-\>]\s*(.*)$', line)
        if side_prefix_m:
            side = int(side_prefix_m.group(1))
            remainder = side_prefix_m.group(2).strip()
            if not remainder:
                continue
            first_non_msg = False

            # Check if remainder contains "Name > Text" or "Name: Text" or "Name - Text"
            sep_m = re.match(r'^([^:\>\-]+?)\s*[:\>\-]\s*(.+)$', remainder)
            if sep_m:
                name = sep_m.group(1).strip()
                content = sep_m.group(2).strip()
            else:
                # No name separator, remainder is the message text directly
                content = remainder
                name = last_name if (side == last_side and last_name) else (contact_name if side == 1 else "Character 2")

            # Check for display text vs spoken text: "Display == Spoken"
            if "==" in content:
                parts = content.split("==", 1)
                disp_text = parts[0].strip()
                aud_text = parts[1].strip()
            else:
                disp_text = content
                aud_text = content

            messages.append({
                'side': side,
                'name': name,
                'text': disp_text,
                'audio_text': aud_text,
                'is_img': False,
                'contact_name': contact_name,
                'section_idx': section_idx
            })
            last_side = side
            last_name = name
            if name and name not in contacts_seen:
                contacts_seen.append(name)
            continue

        # 3. Non-message lines (e.g. "mystique", contact names, screenshot/image break headers):
        # These are used purely for chat headers and screenshot image breaks.
        # THEY ARE NEVER ADDED TO MESSAGES AND NEVER SPOKEN BY ELEVENLABS!
        contact_name = line
        section_idx += 1
        first_non_msg = False
        if line not in contacts_seen:
            contacts_seen.append(line)

    return contact_name, messages, contacts_seen

def render_sf_back_chevron(w, h, color=(10, 132, 255), stroke_w=2.6):
    ss = 8
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lw = max(1, int(stroke_w * ss))

    pad_x = int(1.2 * ss)
    pad_y = int(1.5 * ss)

    p_top = (sw - pad_x - lw // 2, pad_y + lw // 2)
    p_mid = (pad_x + lw // 2, sh // 2)
    p_bot = (sw - pad_x - lw // 2, sh - pad_y - lw // 2)

    draw.line([p_top, p_mid, p_bot], fill=color + (255,), width=lw, joint='round')
    rcap = lw / 2.0
    for p in [p_top, p_mid, p_bot]:
        draw.ellipse([p[0] - rcap, p[1] - rcap, p[0] + rcap, p[1] + rcap], fill=color + (255,))

    return img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def render_sf_camera_icon(w, h, color=(10, 132, 255), stroke_w=1.9):
    ss = 8
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lw = max(1, int(stroke_w * ss))

    pad = int(1.0 * ss)
    bw = int((sw - pad * 2) * 0.60)
    bh = int(sh - pad * 2)
    bx = pad + lw // 2
    by = pad + (sh - pad * 2 - bh) // 2
    brad = int(bh * 0.28)
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=brad, outline=color + (255,), width=lw)

    lx0 = bx + bw + int(1.0 * ss)
    lx1 = sw - pad - lw // 2
    mid_y = sh // 2
    lh_in = int(bh * 0.40)
    lh_out = int(bh * 0.85)

    p0 = (lx0, mid_y - lh_in // 2)
    p1 = (lx1, mid_y - lh_out // 2)
    p2 = (lx1, mid_y + lh_out // 2)
    p3 = (lx0, mid_y + lh_in // 2)

    draw.line([p0, p1, p2, p3, p0], fill=color + (255,), width=lw, joint='round')
    rcap = lw / 2.0
    for p in [p0, p1, p2, p3]:
        draw.ellipse([p[0] - rcap, p[1] - rcap, p[0] + rcap, p[1] + rcap], fill=color + (255,))

    return img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def render_sf_right_chevron(w, h, color=(142, 142, 147), stroke_w=1.3):
    ss = 8
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lw = max(1, int(stroke_w * ss))

    pad_x = int(1.0 * ss)
    pad_y = int(1.2 * ss)

    p_top = (pad_x + lw // 2, pad_y + lw // 2)
    p_mid = (sw - pad_x - lw // 2, sh // 2)
    p_bot = (pad_x + lw // 2, sh - pad_y - lw // 2)

    draw.line([p_top, p_mid, p_bot], fill=color + (255,), width=lw, joint='round')
    rcap = lw / 2.0
    for p in [p_top, p_mid, p_bot]:
        draw.ellipse([p[0] - rcap, p[1] - rcap, p[0] + rcap, p[1] + rcap], fill=color + (255,))

    return img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def render_avatar_circle(av_d, contact_name, custom_img=None, bg_color=None):
    """
    Renders an authentic, ultra-smooth Apple iOS Monogram Circle or photo avatar
    with 8x supersampled Lanczos anti-aliasing.
    """
    ss = 8
    mask_hi = Image.new('L', (av_d * ss, av_d * ss), 0)
    d_hi = ImageDraw.Draw(mask_hi)
    d_hi.ellipse([0, 0, av_d * ss - 1, av_d * ss - 1], fill=255)
    mask = mask_hi.resize((av_d, av_d), Image.Resampling.LANCZOS)

    if custom_img is not None:
        try:
            p_img = custom_img.convert('RGBA')
            min_dim = min(p_img.size)
            left = (p_img.width - min_dim) // 2
            top = (p_img.height - min_dim) // 2
            p_sq = p_img.crop((left, top, left + min_dim, top + min_dim))
            p_sq = p_sq.resize((av_d, av_d), Image.Resampling.LANCZOS)
            p_sq.putalpha(mask)
            return p_sq
        except Exception:
            pass

    grad = Image.new('RGBA', (av_d, av_d))
    if bg_color is not None:
        grad_fill = bg_color if len(bg_color) == 4 else (bg_color[0], bg_color[1], bg_color[2], 255)
        grad = Image.new('RGBA', (av_d, av_d), grad_fill)
    else:
        for y in range(av_d):
            t = y / float(max(1, av_d - 1))
            r_c = int(160 * (1 - t) + 120 * t)
            g_c = int(164 * (1 - t) + 124 * t)
            b_c = int(172 * (1 - t) + 134 * t)
            for x in range(av_d):
                grad.putpixel((x, y), (r_c, g_c, b_c, 255))
    grad.putalpha(mask)

    init_letter = contact_name[0].upper() if contact_name else 'C'
    font_sz = int(av_d * 0.48)
    f_hi = get_font(font_sz * 4, bold=True)
    letter_canvas = Image.new('RGBA', (av_d * 4, av_d * 4), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(letter_canvas)
    bbox = ldraw.textbbox((0, 0), init_letter, font=f_hi)
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    lx = (av_d * 4 - lw) // 2 - bbox[0]
    ly = (av_d * 4 - lh) // 2 - bbox[1]
    ldraw.text((lx, ly), init_letter, fill=(255, 255, 255, 255), font=f_hi)
    letter_down = letter_canvas.resize((av_d, av_d), Image.Resampling.LANCZOS)

    grad.alpha_composite(letter_down)
    return grad

def render_wa_back_arrow(w, h, color=(255, 255, 255), stroke_w=2.2):
    ss = 8
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(1, int(stroke_w * ss))
    mid_y = sh // 2
    d.line([(int(sw * 0.42), int(sh * 0.18)), (lw // 2 + int(1 * ss), mid_y), (int(sw * 0.42), sh - int(sh * 0.18))], fill=color + (255,), width=lw, joint='round')
    d.line([(lw // 2 + int(1 * ss), mid_y), (sw - int(2 * ss), mid_y)], fill=color + (255,), width=lw)
    rcap = lw / 2.0
    for p in [(int(sw * 0.42), int(sh * 0.18)), (int(sw * 0.42), sh - int(sh * 0.18)), (sw - int(2 * ss), mid_y)]:
        d.ellipse([p[0] - rcap, p[1] - rcap, p[0] + rcap, p[1] + rcap], fill=color + (255,))
    return img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def render_wa_camera_icon(w, h, color=(255, 255, 255)):
    ss = 8
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(1 * ss)
    bw = int((sw - pad * 2) * 0.64)
    bh = sh - pad * 2
    d.rounded_rectangle([pad, pad, pad + bw, pad + bh], radius=int(bh * 0.25), fill=color + (255,))
    lx0 = pad + bw + int(1.5 * ss)
    lx1 = sw - pad
    mid_y = sh // 2
    lh_in = int(bh * 0.35)
    lh_out = int(bh * 0.85)
    d.polygon([(lx0, mid_y - lh_in // 2), (lx1, mid_y - lh_out // 2), (lx1, mid_y + lh_out // 2), (lx0, mid_y + lh_in // 2)], fill=color + (255,))
    return img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def render_wa_phone_icon(w, h, color=(255, 255, 255)):
    ss = 8
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(1 * ss)
    pts = [
        (pad + int((sw - pad * 2) * 0.72), pad + int((sh - pad * 2) * 0.15)),
        (pad + int((sw - pad * 2) * 0.88), pad + int((sh - pad * 2) * 0.30)),
        (pad + int((sw - pad * 2) * 0.78), pad + int((sh - pad * 2) * 0.45)),
        (pad + int((sw - pad * 2) * 0.65), pad + int((sh - pad * 2) * 0.40)),
        (pad + int((sw - pad * 2) * 0.40), pad + int((sh - pad * 2) * 0.65)),
        (pad + int((sw - pad * 2) * 0.45), pad + int((sh - pad * 2) * 0.78)),
        (pad + int((sw - pad * 2) * 0.30), pad + int((sh - pad * 2) * 0.88)),
        (pad + int((sw - pad * 2) * 0.15), pad + int((sh - pad * 2) * 0.72)),
        (pad + int((sw - pad * 2) * 0.30), pad + int((sh - pad * 2) * 0.45)),
        (pad + int((sw - pad * 2) * 0.45), pad + int((sh - pad * 2) * 0.30)),
    ]
    d.polygon(pts, fill=color + (255,))
    return img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def render_imessage_bubble_mask(w, h, is_outgoing=False, has_tail=True):
    """
    Renders an authentic, pixel-perfect Apple iMessage bubble mask.
    - When has_tail=False: Smooth continuous rounded rectangle (radius ~17.5px),
      matching intermediate clustered bubbles in reference Image 2.
    - When has_tail=True: Authentic Apple curved beak tail, matching the
      cluster-ending bubble in reference Image 2.
    Uses 4x supersampling with Lanczos downsampling for flawless anti-aliasing.
    """
    ss = 4
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    mask = Image.new('L', (sw, sh), 0)
    draw = ImageDraw.Draw(mask)

    r = min(int(17.5 * ss), sh // 2)

    if not has_tail:
        draw.rounded_rectangle([0, 0, sw, sh], radius=r, fill=255)
        return mask.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

    tail_w = int(7 * ss)
    pts = []

    if is_outgoing:
        body_w = sw - tail_w
        for deg in range(180, 271, 3):
            rad = math.radians(deg)
            pts.append((r + r * math.cos(rad), r + r * math.sin(rad)))
        pts.append((body_w - r, 0))
        for deg in range(270, 361, 3):
            rad = math.radians(deg)
            pts.append((body_w - r + r * math.cos(rad), r + r * math.sin(rad)))

        tail_y0 = sh - int(14.5 * ss)
        pts.append((body_w, tail_y0))
        p0 = (body_w, tail_y0)
        p1 = (body_w + int(1.2 * ss), tail_y0 + int(6.0 * ss))
        p2 = (body_w + int(4.0 * ss), sh - int(1.5 * ss))
        p3 = (sw, sh - int(0.5 * ss))
        for i in range(1, 21):
            t = i / 20.0
            u = 1.0 - t
            bx = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
            by = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
            pts.append((bx, by))

        q0 = (sw, sh - int(0.5 * ss))
        q1 = (sw - int(4.0 * ss), sh)
        q2 = (body_w - int(6.0 * ss), sh)
        q3 = (body_w - int(16.0 * ss), sh)
        for i in range(1, 21):
            t = i / 20.0
            u = 1.0 - t
            bx = u*u*u*q0[0] + 3*u*u*t*q1[0] + 3*u*t*t*q2[0] + t*t*t*q3[0]
            by = u*u*u*q0[1] + 3*u*u*t*q1[1] + 3*u*t*t*q2[1] + t*t*t*q3[1]
            pts.append((bx, by))

        pts.append((r, sh))
        for deg in range(90, 181, 3):
            rad = math.radians(deg)
            pts.append((r + r * math.cos(rad), sh - r + r * math.sin(rad)))

    else:
        body_x0 = tail_w
        body_x1 = sw
        for deg in range(180, 271, 3):
            rad = math.radians(deg)
            pts.append((body_x0 + r + r * math.cos(rad), r + r * math.sin(rad)))
        pts.append((body_x1 - r, 0))
        for deg in range(270, 361, 3):
            rad = math.radians(deg)
            pts.append((body_x1 - r + r * math.cos(rad), r + r * math.sin(rad)))
        pts.append((body_x1, sh - r))
        for deg in range(0, 91, 3):
            rad = math.radians(deg)
            pts.append((body_x1 - r + r * math.cos(rad), sh - r + r * math.sin(rad)))

        pts.append((body_x0 + int(16.0 * ss), sh))
        q0 = (body_x0 + int(16.0 * ss), sh)
        q1 = (body_x0 + int(6.0 * ss), sh)
        q2 = (int(4.0 * ss), sh)
        q3 = (0, sh - int(0.5 * ss))
        for i in range(1, 21):
            t = i / 20.0
            u = 1.0 - t
            bx = u*u*u*q0[0] + 3*u*u*t*q1[0] + 3*u*t*t*q2[0] + t*t*t*q3[0]
            by = u*u*u*q0[1] + 3*u*u*t*q1[1] + 3*u*t*t*q2[1] + t*t*t*q3[1]
            pts.append((bx, by))

        tail_y0 = sh - int(14.5 * ss)
        p0 = (0, sh - int(0.5 * ss))
        p1 = (int(4.0 * ss), sh - int(1.5 * ss))
        p2 = (body_x0 - int(1.2 * ss), tail_y0 + int(6.0 * ss))
        p3 = (body_x0, tail_y0)
        for i in range(1, 21):
            t = i / 20.0
            u = 1.0 - t
            bx = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
            by = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
            pts.append((bx, by))

    draw.polygon(pts, fill=255)
    return mask.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def draw_ios_bubble(surf, x, y, w, h, radius, fill, is_outgoing=False, has_tail=True):
    """Draws an authentic Apple iMessage bubble with curved beak tail or smooth clustered rounding."""
    target_img = surf._image if hasattr(surf, '_image') else surf
    mask = render_imessage_bubble_mask(w, h, is_outgoing=is_outgoing, has_tail=has_tail)
    rgba_fill = fill if len(fill) == 4 else (fill[0], fill[1], fill[2], 255)
    b_surf = Image.new('RGBA', (max(1, int(w)), max(1, int(h))), rgba_fill)
    b_surf.putalpha(mask)
    target_img.alpha_composite(b_surf, (int(x), int(y)))

def draw_wa_bubble(draw, x, y, w, h, radius, fill, is_outgoing=False):
    """Draws a WhatsApp rounded bubble with corner tail."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill)
    if is_outgoing:
        draw.polygon([(x + w - 4, y + h - 10), (x + w + 6, y + h), (x + w - 4, y + h)], fill=fill)
    else:
        draw.polygon([(x + 4, y + h - 10), (x - 6, y + h), (x + 4, y + h)], fill=fill)

def partition_messages_into_pages(messages, msgs_per_page=5):
    """
    Groups messages into discrete pages based on msgs_per_page capacity,
    script section breaks (non-message headers), or contact switches.
    Returns a list of page dicts.
    """
    if not messages:
        return []

    pages = []
    current_msgs = []
    current_contact = None
    current_section = None

    for idx, msg in enumerate(messages):
        c_name = msg.get('contact_name') or 'Contact'
        s_idx = msg.get('section_idx', 0)

        should_split = False
        if current_msgs:
            if len(current_msgs) >= msgs_per_page:
                should_split = True
            elif s_idx != current_section:
                should_split = True
            elif c_name != current_contact:
                should_split = True

        if should_split and current_msgs:
            is_cont = (bool(pages) and pages[-1]['contact_name'] == current_contact and pages[-1]['section_idx'] == current_section)
            pages.append({
                'page_index': len(pages),
                'messages': current_msgs,
                'contact_name': current_contact,
                'section_idx': current_section,
                'show_header': not is_cont,
                'is_continuation': is_cont
            })
            current_msgs = []

        current_msgs.append((idx, msg))
        current_contact = c_name
        current_section = s_idx

    if current_msgs:
        is_cont = (bool(pages) and pages[-1]['contact_name'] == current_contact and pages[-1]['section_idx'] == current_section)
        pages.append({
            'page_index': len(pages),
            'messages': current_msgs,
            'contact_name': current_contact,
            'section_idx': current_section,
            'show_header': not is_cont,
            'is_continuation': is_cont
        })

    return pages

def render_chat_frame(
    messages,
    visible_count,
    contact_name="Contact",
    badge_count=0,
    style='ios',
    theme='light',
    width=1080,
    height=1920,
    chat_y_pct=None,
    chat_y=None,
    container_scale=1.0,
    corner_radius_val=35,
    font_size_override=None,
    contact_avatar_img=None,
    container_shadow=False,
    show_header=True,
    bubble_scale=None,
    bubble_max_pct=None,
    min_bubble_w=None,
    header_name_size=None,
):
    """
    Renders an authentic, floating iOS or WhatsApp chat card onto a transparent RGBA canvas.
    - True soft Gaussian drop shadow (optional, clean crisp edges for green screen).
    - Dynamic card height: hugs content up to max_card_h.
    - Support for show_header=False on continuation pages to hug bubbles cleanly without re-drawing header.
    - Smooth auto-scrolling when content exceeds card bounds.
    - Fully supports Bubble Scale, Max Bubble Width, Min Bubble Width, and Header Name Size.
    """
    scale = width / 540.0
    scale_1080 = width / 1080.0
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    is_dark = (theme == 'dark')
    card_w = int(404 * scale * container_scale)
    corner_radius = int(corner_radius_val * (scale / 2.0)) if corner_radius_val else 0
    card_x = (width - card_w) // 2

    # Header name font size calculation
    if header_name_size is not None:
        try:
            name_sz = max(10, int(float(header_name_size) * scale_1080))
        except (ValueError, TypeError):
            name_sz = max(10, int(27 * scale_1080))
    else:
        name_sz = max(10, int(27 * scale_1080))

    # Bubble Scale factor (relative to 115 baseline)
    b_scale_factor = (float(bubble_scale) / 115.0) if bubble_scale else 1.0

    # Bubble and font settings
    if font_size_override:
        f_val = float(font_size_override)
        if f_val > 30:
            f_size = max(10, int(f_val * scale_1080))
        else:
            f_size = max(10, int(f_val * (scale / 2.0)))
    else:
        base_sz = 21 if style == 'ios' else 18
        f_size = max(10, int(base_sz * scale * b_scale_factor))

    font_reg = get_font(f_size, bold=False, weight='regular')
    font_emj = get_emoji_font(f_size)

    # Max bubble width percentage
    if bubble_max_pct is not None:
        max_pct = float(bubble_max_pct)
    else:
        max_pct = 74.0 if style == 'ios' else 82.0
    max_bubble_w = max(int(card_w * 0.25), min(card_w, int(card_w * (max_pct / 100.0))))

    # Padding and radii scale with bubble_scale
    pad_h = int(14 * scale * b_scale_factor)
    pad_v = int(11 * scale * b_scale_factor)
    b_radius = int(18 * scale * b_scale_factor) if style == 'ios' else int(10 * scale * b_scale_factor)
    gap = int(7 * scale)

    # 1. Compute layout of all visible bubbles with iMessage grouping & tail logic
    dummy_img = Image.new('RGBA', (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)

    visible_msgs = messages[:visible_count]
    rendered_bubbles = []
    total_content_h = 0

    for i, msg in enumerate(visible_msgs):
        side = msg.get('side', 1)
        text = msg.get('text', '')
        is_img = msg.get('is_img', False)

        is_last_of_cluster = (
            (i == len(visible_msgs) - 1) or
            (visible_msgs[i + 1].get('side', 1) != side) or
            visible_msgs[i + 1].get('is_img')
        )
        has_tail = is_last_of_cluster
        gap_after = (int(7.5 * scale) if is_last_of_cluster else int(3.2 * scale)) if style == 'ios' else int(7 * scale)

        if is_img:
            img_w = int(card_w * 0.62)
            img_h = int(160 * scale)
            rendered_bubbles.append({
                'side': side,
                'is_img': True,
                'img_path': text,
                'bw': img_w,
                'bh': img_h,
                'lines': [],
                'has_tail': False,
                'gap_after': gap_after
            })
            total_content_h += img_h + gap_after
            continue

        words = text.split(' ')
        lines = []
        cur = []
        wrap_limit = max_bubble_w - pad_h * 2 - int(8 * scale)
        for w in words:
            test_line = ' '.join(cur + [w])
            lw, _ = measure_text_with_emojis(dummy_draw, test_line, font_reg, font_emj)
            if lw <= wrap_limit:
                cur.append(w)
            else:
                if cur:
                    lines.append(' '.join(cur))
                    cur = [w]
                else:
                    lines.append(w)
                    cur = []
        if cur:
            lines.append(' '.join(cur))
        if not lines:
            lines = [text]

        line_dims = [measure_text_with_emojis(dummy_draw, l, font_reg, font_emj) for l in lines]
        tail_w = int(6.5 * scale) if has_tail else 0
        calculated_bw = max(d[0] for d in line_dims) + pad_h * 2 + (tail_w if style == 'ios' else 0)

        # Apply min_bubble_w
        min_w = int(float(min_bubble_w) * scale_1080) if min_bubble_w else 0
        bw = max(calculated_bw, min_w)
        bw = min(bw, max_bubble_w)

        bh = max(int(43 * scale * b_scale_factor), sum(d[1] for d in line_dims) + (len(lines) - 1) * int(4 * scale) + pad_v * 2)

        rendered_bubbles.append({
            'side': side,
            'is_img': False,
            'lines': lines,
            'line_dims': line_dims,
            'bw': bw,
            'bh': bh,
            'has_tail': has_tail,
            'gap_after': gap_after
        })
        total_content_h += bh + gap_after

    # 2. Dimensions & Positioning
    if show_header:
        if style == 'ios':
            name_font_reg = get_font(name_sz, weight='medium')
            name_font_emj = get_emoji_font(name_sz)
            nw, nh = measure_text_with_emojis(dummy_draw, contact_name, name_font_reg, name_font_emj)
            av_d = int(40 * scale)
            av_y = int(8 * scale)
            gap_av_name = int(4 * scale)
            name_y = av_y + av_d + gap_av_name
            bottom_pad = max(int(10 * scale), int(nh * 0.35))
            base_hdr_h = int(74 * scale)
            hdr_h = max(base_hdr_h, name_y + nh + bottom_pad)
        else:
            hdr_h = int(60 * scale)
    else:
        hdr_h = 0
    min_card_h = (hdr_h + int(60 * scale)) if show_header else int(45 * scale)
    max_card_h = int(height * 0.85)
    content_area_pad = int(14 * scale) if show_header else int(10 * scale)

    needed_card_h = hdr_h + total_content_h + content_area_pad
    card_h = max(min_card_h, min(needed_card_h, max_card_h))

    if chat_y is not None:
        card_y = int(chat_y * (scale / 2.0))
    elif chat_y_pct is not None:
        card_y = int(height * chat_y_pct)
    else:
        card_y = int(175 * scale)

    # Auto-scroll calculation
    max_visible_content_h = card_h - hdr_h - content_area_pad
    scroll_y = 0
    if total_content_h > max_visible_content_h:
        scroll_y = total_content_h - max_visible_content_h

    # 3. Drop Shadow (optional)
    if container_shadow:
        shadow_pad = int(45 * scale)
        shadow_img = Image.new('RGBA', (card_w + shadow_pad * 2, card_h + shadow_pad * 2), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        shadow_draw.rounded_rectangle(
            [shadow_pad, shadow_pad + int(8 * scale), shadow_pad + card_w, shadow_pad + card_h + int(8 * scale)],
            radius=corner_radius,
            fill=(0, 0, 0, 95)
        )
        shadow_blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=int(18 * scale)))
        canvas.alpha_composite(shadow_blurred, (card_x - shadow_pad, card_y - shadow_pad))

    # 4. Solid Card Body
    card_img = Image.new('RGBA', (card_w, card_h), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_img)

    if style == 'whatsapp':
        bg_col = (11, 20, 26, 255) if is_dark else (239, 234, 226, 255)
        if corner_radius > 0:
            card_draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=bg_col)
        else:
            card_draw.rectangle([0, 0, card_w, card_h], fill=bg_col)
        if show_header:
            hdr_col = (32, 44, 51, 255) if is_dark else (0, 128, 105, 255)
            text_col = (233, 237, 239) if is_dark else (255, 255, 255)
            sub_text_col = (134, 150, 160) if is_dark else (220, 240, 235)
            if corner_radius > 0:
                card_draw.rounded_rectangle([0, 0, card_w, hdr_h], radius=corner_radius, fill=hdr_col)
                card_draw.rectangle([0, hdr_h - corner_radius, card_w, hdr_h], fill=hdr_col)
            else:
                card_draw.rectangle([0, 0, card_w, hdr_h], fill=hdr_col)

            # Back arrow (8x supersampled)
            back_w, back_h = int(14 * scale), int(14 * scale)
            back_img = render_wa_back_arrow(back_w, back_h, color=text_col, stroke_w=2.2 * scale)
            card_img.alpha_composite(back_img, (int(14 * scale), (hdr_h - back_h) // 2))

            # Avatar (8x supersampled)
            av_d = int(38 * scale)
            av_x = int(36 * scale)
            av_y = (hdr_h - av_d) // 2
            av_img = render_avatar_circle(av_d, contact_name, contact_avatar_img, bg_color=(120, 140, 150))
            card_img.alpha_composite(av_img, (av_x, av_y))

            # Name and Status
            n_font = get_font(name_sz if header_name_size else int(14 * scale), bold=True)
            s_font = get_font(int(11 * scale), bold=False)
            nb = card_draw.textbbox((0, 0), contact_name, font=n_font)
            nh_wa = nb[3] - nb[1]
            card_draw.text((av_x + av_d + int(10 * scale), av_y + int(2 * scale)), contact_name, fill=text_col, font=n_font)
            card_draw.text((av_x + av_d + int(10 * scale), av_y + int(2 * scale) + nh_wa + int(3 * scale)), "online", fill=sub_text_col, font=s_font)

            # Video and Phone Call icons (8x supersampled)
            cam_w, cam_h = int(18 * scale), int(13 * scale)
            cam_img = render_wa_camera_icon(cam_w, cam_h, color=text_col)
            card_img.alpha_composite(cam_img, (card_w - int(62 * scale), (hdr_h - cam_h) // 2))

            ph_w, ph_h = int(15 * scale), int(15 * scale)
            ph_img = render_wa_phone_icon(ph_w, ph_h, color=text_col)
            card_img.alpha_composite(ph_img, (card_w - int(30 * scale), (hdr_h - ph_h) // 2))

    else:
        # iOS iMessage Card (Exact Image 2 Pure Black #000000 Theme)
        card_bg_col = (0, 0, 0, 255) if is_dark else (255, 255, 255, 255)
        if corner_radius > 0:
            card_draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=card_bg_col)
        else:
            card_draw.rectangle([0, 0, card_w, card_h], fill=card_bg_col)

        if show_header:
            hdr_bg_col = (30, 30, 32, 255) if is_dark else (244, 244, 244, 255)
            card_draw.rectangle([0, 0, card_w, hdr_h], fill=hdr_bg_col)

            av_d = int(40 * scale)
            av_x = (card_w - av_d) // 2
            av_y = int(8 * scale)
            cy = av_y + av_d // 2
            blue = (10, 132, 255)

            # Back Chevron < (Apple SF Symbol geometry, 8x supersampled)
            ch_w = max(2, int(10 * scale))
            ch_h = max(4, int(21 * scale))
            ch_img = render_sf_back_chevron(ch_w, ch_h, color=blue, stroke_w=2.6 * scale)
            cx0 = int(18 * scale)
            card_img.alpha_composite(ch_img, (cx0, cy - ch_h // 2))

            # Unread badge (if enabled)
            if badge_count > 0:
                b_font = get_font(int(13 * scale), bold=True)
                b_text = str(badge_count)
                bbox = card_draw.textbbox((0, 0), b_text, font=b_font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                badge_w = max(int(22 * scale), tw + int(12 * scale))
                badge_h = int(22 * scale)
                badge_x = cx0 + ch_w + int(6 * scale)
                badge_y = cy - badge_h // 2
                card_draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=badge_h // 2, fill=blue)
                card_draw.text((badge_x + (badge_w - tw) // 2, badge_y + (badge_h - th) // 2 - int(2 * scale)), b_text, fill=(255, 255, 255), font=b_font)

            # Center Avatar (PFP) with authentic iOS gradient and monogram (8x supersampled)
            av_img = render_avatar_circle(av_d, contact_name, contact_avatar_img)
            card_img.alpha_composite(av_img, (av_x, av_y))

            # FaceTime Camera Icon (right-aligned, vertically centered at cy, 8x supersampled)
            cam_w = max(4, int(23 * scale))
            cam_h = max(3, int(15 * scale))
            cam_img = render_sf_camera_icon(cam_w, cam_h, color=blue, stroke_w=1.9 * scale)
            cam_x = card_w - int(20 * scale) - cam_w
            cam_y = cy - cam_h // 2
            card_img.alpha_composite(cam_img, (cam_x, cam_y))

            # Contact Name + Small Chevron > (centered below avatar circle)
            name_font_reg = get_font(name_sz, weight='medium')
            name_font_emj = get_emoji_font(name_sz)
            nw, nh = measure_text_with_emojis(card_draw, contact_name, name_font_reg, name_font_emj)

            rchev_w = max(3, int(name_sz * 0.35))
            rchev_h = max(5, int(name_sz * 0.58))
            rchev_img = render_sf_right_chevron(rchev_w, rchev_h, color=(142, 142, 147), stroke_w=max(1.0, name_sz * 0.09))

            gap_name_chev = int(3.5 * scale)
            total_name_w = nw + gap_name_chev + rchev_w
            name_x = (card_w - total_name_w) // 2
            name_y = av_y + av_d + int(4 * scale)
            text_color = (255, 255, 255) if is_dark else (0, 0, 0)
            draw_text_with_emojis(card_draw, (name_x, name_y), contact_name, name_font_reg, name_font_emj, text_color)
            card_img.alpha_composite(rchev_img, (name_x + nw + gap_name_chev, name_y + (nh - rchev_h) // 2))

            # Hairline Divider (subtle dark line in dark mode matching Image 2 reference; light gray in light mode)
            div_col = (44, 44, 46, 255) if is_dark else (229, 229, 234, 255)
            card_draw.line([(0, hdr_h - 1), (card_w, hdr_h - 1)], fill=div_col, width=max(1, int(1 * scale)))

    # 5. Message Bubbles
    bubbles_surf = Image.new('RGBA', (card_w, card_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(bubbles_surf)

    curr_y = (hdr_h + int(8 * scale) if show_header else int(8 * scale)) - scroll_y
    for b in rendered_bubbles:
        side = b['side']
        bw = b['bw']
        bh = b['bh']
        lines = b.get('lines', [])

        if b.get('is_img'):
            bx = int(16 * scale) if side == 1 else (card_w - bw - int(16 * scale))
            img_card = Image.new('RGBA', (bw, bh), (0, 0, 0, 255))
            ic_draw = ImageDraw.Draw(img_card)
            ic_draw.rounded_rectangle([0, 0, bw, bh], radius=b_radius, fill=(20, 20, 22))
            ic_draw.text((int(14 * scale), int(14 * scale)), "Attachment", fill=(255, 255, 255), font=font_reg)
            bubbles_surf.alpha_composite(img_card, (bx, curr_y))
            curr_y += bh + b.get('gap_after', gap)
            continue

        if style == 'whatsapp':
            if side == 2:
                bx = card_w - bw - int(16 * scale)
                b_fill = (0, 92, 75) if is_dark else (217, 253, 211)
                t_fill = (233, 237, 239) if is_dark else (17, 27, 33)
                draw_wa_bubble(b_draw, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=True)
                tx = bx + pad_h
            else:
                bx = int(16 * scale)
                b_fill = (32, 44, 51) if is_dark else (255, 255, 255)
                t_fill = (233, 237, 239) if is_dark else (17, 27, 33)
                draw_wa_bubble(b_draw, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=False)
                tx = bx + pad_h
        else:
            has_tail = b.get('has_tail', True)
            if side == 2:
                # Outgoing blue bubble (Apple Electric Blue #008CFF)
                bx = card_w - bw - (int(16 * scale) if has_tail else int(22.5 * scale))
                b_fill = (0, 140, 255, 255)
                t_fill = (255, 255, 255)
                draw_ios_bubble(bubbles_surf, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=True, has_tail=has_tail)
                tx = bx + pad_h
            else:
                # Incoming grey bubble (Deeper graphite grey #282828 matching reference Image 2)
                bx = int(16 * scale) if has_tail else int(22.5 * scale)
                b_fill = (40, 40, 40, 255) if is_dark else (232, 232, 232, 255)
                t_fill = (255, 255, 255) if is_dark else (0, 0, 0)
                draw_ios_bubble(bubbles_surf, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=False, has_tail=has_tail)
                tx = bx + (pad_h + int(6.5 * scale) if has_tail else pad_h)

        # Draw lines of text
        if len(lines) == 1:
            ty = curr_y + (bh - b['line_dims'][0][1]) // 2 - int(2 * scale)
        else:
            ty = curr_y + pad_v
        for li, line in enumerate(lines):
            draw_text_with_emojis(b_draw, (tx, ty), line, font_reg, font_emj, t_fill)
            ty += b['line_dims'][li][1] + int(4 * scale)

        curr_y += bh + b.get('gap_after', gap)

    # Clip bubbles cleanly to card body below header
    if corner_radius > 0:
        mask = Image.new('L', (card_w, card_h), 0)
        m_draw = ImageDraw.Draw(mask)
        m_draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=255)
        m_draw.rectangle([0, 0, card_w, hdr_h], fill=0)

        r, g, b, a = bubbles_surf.split()
        a = ImageChops.multiply(a, mask)
        bubbles_surf.putalpha(a)
    else:
        # Fast rectangular clip below header
        mask = Image.new('L', (card_w, card_h), 255)
        m_draw = ImageDraw.Draw(mask)
        m_draw.rectangle([0, 0, card_w, hdr_h], fill=0)
        r, g, b, a = bubbles_surf.split()
        a = ImageChops.multiply(a, mask)
        bubbles_surf.putalpha(a)

    card_img.alpha_composite(bubbles_surf, (0, 0))
    canvas.alpha_composite(card_img, (card_x, card_y))
    return canvas

def render_preview_image(body):
    settings = body.get('settings', {}) if isinstance(body.get('settings'), dict) else {}
    style = body.get('style') or settings.get('app_type') or settings.get('style') or 'ios'
    script_text = body.get('script', '')
    contact_name, messages, contacts = parse_script(script_text)

    W, H = 540, 960
    msgs_per_page = int(body.get('msgs_per_page') or settings.get('msgs_per_page') or 6)
    if msgs_per_page < 1:
        msgs_per_page = 6

    pages = partition_messages_into_pages(messages, msgs_per_page=msgs_per_page)
    total_pages = max(1, len(pages))
    page = int(body.get('page', 0))
    page = max(0, min(page, total_pages - 1))

    if pages and page < len(pages):
        cur_p = pages[page]
        page_msgs = [m for _, m in cur_p['messages']]
        page_contact = cur_p['contact_name']
        show_header = cur_p['show_header']
    else:
        page_msgs = []
        page_contact = contact_name
        show_header = True

    theme = (body.get('theme') or settings.get('theme') or 'light') if style == 'ios' else (body.get('wa_theme') or settings.get('wa_theme') or 'light')
    badge_count = int(body.get('badge_count') or settings.get('badge_count') or 0)
    chat_y = body.get('chat_y') or settings.get('chat_y')
    container_shadow = bool(body.get('container_shadow') or settings.get('container_shadow', False))

    bubble_scale = body.get('bubble_scale') or settings.get('bubble_scale')
    bubble_max_pct = body.get('bubble_max_pct') or settings.get('bubble_max_pct')
    min_bubble_w = body.get('min_bubble_w') or settings.get('min_bubble_w')
    font_size_override = body.get('font_size') or settings.get('font_size')
    header_name_size = (
        body.get('header_name_size') or settings.get('header_name_size') or
        body.get('name_font_size') or settings.get('name_font_size')
    )

    canvas = render_chat_frame(
        page_msgs,
        visible_count=len(page_msgs),
        contact_name=page_contact,
        badge_count=badge_count,
        style=style,
        theme=theme,
        width=W,
        height=H,
        chat_y=chat_y,
        container_scale=float(body.get('container_scale', 1.0)),
        corner_radius_val=int(body.get('corner_radius', 35)),
        container_shadow=container_shadow,
        show_header=show_header,
        bubble_scale=bubble_scale,
        bubble_max_pct=bubble_max_pct,
        min_bubble_w=min_bubble_w,
        font_size_override=font_size_override,
        header_name_size=header_name_size
    )

    # For web preview JPEG, composite over green chroma or background
    bg = Image.new('RGB', (W, H), (0, 255, 0))
    bg.paste(canvas, (0, 0), mask=canvas.split()[3])

    buf = io.BytesIO()
    bg.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return buf.getvalue(), total_pages


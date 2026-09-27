import os
import io
import re
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

def get_font(size, bold=False):
    font_candidates = []
    if os.name == 'nt':
        win_dir = os.environ.get('WINDIR', 'C:\\Windows')
        fonts_dir = os.path.join(win_dir, 'Fonts')
        font_candidates.extend([
            os.path.join(fonts_dir, 'segoeuib.ttf' if bold else 'segoeui.ttf'),
            os.path.join(fonts_dir, 'arialbd.ttf' if bold else 'arial.ttf'),
            os.path.join(fonts_dir, 'calibrib.ttf' if bold else 'calibri.ttf')
        ])
    else:
        # Linux / Vercel serverless environment
        font_candidates.extend([
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

def draw_video_icon(draw, x, y, size=18, color=(0, 122, 255), outline=True):
    if outline:
        # Apple FaceTime outline video icon matching sample video
        vw = int(size * 1.0)
        vh = int(size * 1.05)
        rad = max(2, int(size * 0.25))
        lw = max(1, int(size * 0.11))
        draw.rounded_rectangle([x, y, x + vw, y + vh], radius=rad, outline=color, width=lw)
        tw = int(size * 0.42)
        draw.line([
            (x + vw + 2, y + int(vh * 0.24)),
            (x + vw + 2 + tw, y + int(vh * 0.08)),
            (x + vw + 2 + tw, y + vh - int(vh * 0.08)),
            (x + vw + 2, y + vh - int(vh * 0.24)),
            (x + vw + 2, y + int(vh * 0.24))
        ], fill=color, width=lw, joint='round')
    else:
        bw = int(size * 0.65)
        bh = int(size * 0.5)
        draw.rounded_rectangle([x, y, x + bw, y + bh], radius=max(2, int(size * 0.12)), fill=color)
        lw = int(size * 0.28)
        draw.polygon([
            (x + bw + 2, y + int(bh * 0.2)),
            (x + bw + 2 + lw, y),
            (x + bw + 2 + lw, y + bh),
            (x + bw + 2, y + int(bh * 0.8))
        ], fill=color)

def draw_phone_icon(draw, x, y, size=16, color=(0, 122, 255)):
    draw.rounded_rectangle([x, y, x + size, y + size], radius=3, fill=color)

def render_imessage_bubble_mask(w, h, is_outgoing=False):
    """
    Renders an authentic, pixel-perfect Apple iMessage bubble mask
    with the characteristic curved beak/tail hook matching the sample video.
    Uses 4x supersampling with Lanczos downsampling for flawless anti-aliasing.
    """
    ss = 4
    sw, sh = max(1, int(w * ss)), max(1, int(h * ss))
    mask = Image.new('L', (sw, sh), 0)
    draw = ImageDraw.Draw(mask)

    r = min(int(36 * ss), sh // 2)
    pts = []

    if is_outgoing:
        tail_w = int(14 * ss)
        body_w = sw - tail_w
        for deg in range(180, 271, 3):
            rad = math.radians(deg)
            pts.append((r + r * math.cos(rad), r + r * math.sin(rad)))
        pts.append((body_w - r, 0))
        for deg in range(270, 361, 3):
            rad = math.radians(deg)
            pts.append((body_w - r + r * math.cos(rad), r + r * math.sin(rad)))
        tail_y0 = sh - int(24 * ss)
        pts.append((body_w, tail_y0))
        p0 = (body_w, tail_y0)
        p1 = (body_w + int(2 * ss), tail_y0 + int(10 * ss))
        p2 = (body_w + int(7 * ss), sh - int(4 * ss))
        p3 = (sw, sh)
        for i in range(1, 21):
            t = i / 20.0
            u = 1.0 - t
            bx = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
            by = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
            pts.append((bx, by))
        q0 = (sw, sh)
        q1 = (sw - int(10 * ss), sh)
        q2 = (body_w - int(14 * ss), sh - int(13 * ss))
        q3 = (body_w - int(34 * ss), sh)
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
        tail_w = int(14 * ss)
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
        pts.append((body_x0 + int(34 * ss), sh))
        q0 = (body_x0 + int(34 * ss), sh)
        q1 = (body_x0 - int(14 * ss), sh - int(13 * ss))
        q2 = (int(10 * ss), sh)
        q3 = (0, sh)
        for i in range(1, 21):
            t = i / 20.0
            u = 1.0 - t
            bx = u*u*u*q0[0] + 3*u*u*t*q1[0] + 3*u*t*t*q2[0] + t*t*t*q3[0]
            by = u*u*u*q0[1] + 3*u*u*t*q1[1] + 3*u*t*t*q2[1] + t*t*t*q3[1]
            pts.append((bx, by))
        tail_y0 = sh - int(24 * ss)
        p0 = (0, sh)
        p1 = (int(7 * ss), sh - int(4 * ss))
        p2 = (body_x0 - int(2 * ss), tail_y0 + int(10 * ss))
        p3 = (body_x0, tail_y0)
        for i in range(1, 21):
            t = i / 20.0
            u = 1.0 - t
            bx = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
            by = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
            pts.append((bx, by))

    draw.polygon(pts, fill=255)
    return mask.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)

def draw_ios_bubble(surf, x, y, w, h, radius, fill, is_outgoing=False):
    """Draws an authentic Apple iMessage bubble with the smooth curved beak tail."""
    target_img = surf._image if hasattr(surf, '_image') else surf
    mask = render_imessage_bubble_mask(w, h, is_outgoing=is_outgoing)
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
    show_header=True
):
    """
    Renders an authentic, floating iOS or WhatsApp chat card onto a transparent RGBA canvas.
    - True soft Gaussian drop shadow (optional, clean crisp edges for green screen).
    - Dynamic card height: hugs content up to max_card_h.
    - Support for show_header=False on continuation pages to hug bubbles cleanly without re-drawing header.
    - Smooth auto-scrolling when content exceeds card bounds.
    """
    scale = width / 540.0
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    is_dark = (theme == 'dark')
    card_w = int(404 * scale * container_scale)
    corner_radius = int(corner_radius_val * (scale / 2.0)) if corner_radius_val else 0
    card_x = (width - card_w) // 2

    # Bubble and font settings
    f_size = font_size_override or int(18 * scale)
    font_reg = get_font(f_size, bold=False)
    font_emj = get_emoji_font(f_size)
    max_bubble_w = int(card_w * 0.74)
    pad_h = int(14 * scale)
    pad_v = int(11 * scale)
    b_radius = int(18 * scale) if style == 'ios' else int(10 * scale)
    gap = int(7 * scale)

    # 1. Compute layout of all visible bubbles
    dummy_img = Image.new('RGBA', (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)

    visible_msgs = messages[:visible_count]
    rendered_bubbles = []
    total_content_h = 0

    for msg in visible_msgs:
        side = msg.get('side', 1)
        text = msg.get('text', '')
        is_img = msg.get('is_img', False)

        if is_img:
            img_w = int(card_w * 0.62)
            img_h = int(160 * scale)
            rendered_bubbles.append({
                'side': side,
                'is_img': True,
                'img_path': text,
                'bw': img_w,
                'bh': img_h,
                'lines': []
            })
            total_content_h += img_h + gap
            continue

        words = text.split(' ')
        lines = []
        cur = []
        for w in words:
            test_line = ' '.join(cur + [w])
            lw, _ = measure_text_with_emojis(dummy_draw, test_line, font_reg, font_emj)
            if lw <= (max_bubble_w - pad_h * 2 - int(8 * scale)):
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
        bw = max(d[0] for d in line_dims) + pad_h * 2 + (int(7 * scale) if style == 'ios' else 0)
        bh = max(int(43 * scale), sum(d[1] for d in line_dims) + (len(lines) - 1) * int(4 * scale) + pad_v * 2)

        rendered_bubbles.append({
            'side': side,
            'is_img': False,
            'lines': lines,
            'line_dims': line_dims,
            'bw': bw,
            'bh': bh
        })
        total_content_h += bh + gap

    # 2. Dimensions & Positioning
    hdr_h = (int(72.5 * scale) if style == 'ios' else int(65 * scale)) if show_header else 0
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

            # Back <
            card_draw.text((int(14 * scale), int(16 * scale)), "<", fill=text_col, font=get_font(int(24 * scale), True))

            # Avatar
            av_d = int(42 * scale)
            av_x = int(44 * scale)
            av_y = (hdr_h - av_d) // 2
            card_draw.ellipse([av_x, av_y, av_x + av_d, av_y + av_d], fill=(120, 140, 150))
            init_letter = contact_name[0].upper() if contact_name else "C"
            av_font = get_font(int(18 * scale), bold=True)
            abox = card_draw.textbbox((0, 0), init_letter, font=av_font)
            card_draw.text((av_x + (av_d - (abox[2] - abox[0])) // 2, av_y + (av_d - (abox[3] - abox[1])) // 2 - int(2 * scale)), init_letter, fill=(255, 255, 255), font=av_font)

            # Name and Status
            n_font = get_font(int(14 * scale), bold=True)
            s_font = get_font(int(11 * scale), bold=False)
            card_draw.text((av_x + av_d + int(10 * scale), av_y + int(2 * scale)), contact_name, fill=text_col, font=n_font)
            card_draw.text((av_x + av_d + int(10 * scale), av_y + int(22 * scale)), "online", fill=sub_text_col, font=s_font)

            # Call icons
            draw_video_icon(card_draw, card_w - int(60 * scale), int(22 * scale), size=int(16 * scale), color=text_col, outline=False)
            draw_phone_icon(card_draw, card_w - int(30 * scale), int(22 * scale), size=int(15 * scale), color=text_col)

    else:
        # iOS iMessage Card
        card_bg_col = (28, 28, 30, 255) if is_dark else (255, 255, 255, 255)
        if corner_radius > 0:
            card_draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=card_bg_col)
        else:
            card_draw.rectangle([0, 0, card_w, card_h], fill=card_bg_col)

        if show_header:
            hdr_bg_col = (30, 30, 32, 255) if is_dark else (244, 244, 244, 255)
            card_draw.rectangle([0, 0, card_w, hdr_h], fill=hdr_bg_col)

            # Back Chevron < (sleek geometric stroke)
            cx0, cy0 = int(18 * scale), int(25 * scale)
            card_draw.line([
                (cx0 + int(11 * scale), cy0),
                (cx0 + int(1 * scale), cy0 + int(10 * scale)),
                (cx0 + int(11 * scale), cy0 + int(20 * scale))
            ], fill=(0, 122, 255, 255), width=max(2, int(2.5 * scale)), joint='round')

            # Unread badge
            if badge_count > 0:
                b_font = get_font(int(13 * scale), bold=True)
                b_text = str(badge_count)
                bbox = card_draw.textbbox((0, 0), b_text, font=b_font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                badge_w = max(int(22 * scale), tw + int(12 * scale))
                badge_h = int(22 * scale)
                badge_x = int(36 * scale)
                badge_y = int(22 * scale)
                card_draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=badge_h // 2, fill=(0, 122, 255))
                card_draw.text((badge_x + (badge_w - tw) // 2, badge_y + (badge_h - th) // 2 - int(2 * scale)), b_text, fill=(255, 255, 255), font=b_font)

            # Center Avatar with Apple vertical subtle gradient
            av_d = int(44 * scale)
            av_x = (card_w - av_d) // 2
            av_y = int(6 * scale)

            av_mask = Image.new('L', (av_d, av_d), 0)
            av_mdraw = ImageDraw.Draw(av_mask)
            av_mdraw.ellipse([0, 0, av_d, av_d], fill=255)
            av_grad = Image.new('RGBA', (av_d, av_d))
            for y in range(av_d):
                t = y / float(av_d)
                r_c = int(160 * (1 - t) + 113 * t)
                g_c = int(165 * (1 - t) + 116 * t)
                b_c = int(176 * (1 - t) + 127 * t)
                for x in range(av_d):
                    av_grad.putpixel((x, y), (r_c, g_c, b_c, 255))
            av_grad.putalpha(av_mask)
            card_img.alpha_composite(av_grad, (av_x, av_y))

            init_letter = contact_name[0].upper() if contact_name else "C"
            av_font = get_font(int(22 * scale), bold=True)
            abox = card_draw.textbbox((0, 0), init_letter, font=av_font)
            card_draw.text((av_x + (av_d - (abox[2] - abox[0])) // 2, av_y + (av_d - (abox[3] - abox[1])) // 2 - int(2 * scale)), init_letter, fill=(255, 255, 255), font=av_font)

            # Contact Name
            name_font_reg = get_font(int(12 * scale), bold=False)
            name_font_emj = get_emoji_font(int(12 * scale))
            nw, nh = measure_text_with_emojis(card_draw, contact_name, name_font_reg, name_font_emj)
            name_total_w = nw + int(8 * scale)
            name_x = (card_w - name_total_w) // 2
            name_y = av_y + av_d + int(4 * scale)
            text_color = (255, 255, 255) if is_dark else (0, 0, 0)
            draw_text_with_emojis(card_draw, (name_x, name_y), contact_name, name_font_reg, name_font_emj, text_color)

            # Small Chevron >
            sx = name_x + nw + int(3 * scale)
            sy = name_y + int(2.5 * scale)
            card_draw.line([
                (sx, sy),
                (sx + int(2.5 * scale), sy + int(3 * scale)),
                (sx, sy + int(6 * scale))
            ], fill=(142, 142, 147, 255), width=max(1, int(1 * scale)), joint='round')

            # FaceTime Camera Icon
            draw_video_icon(card_draw, card_w - int(48 * scale), int(26 * scale), size=int(18 * scale), color=(0, 122, 255), outline=True)

            # Divider line
            div_col = (56, 56, 58) if is_dark else (229, 229, 229)
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
            curr_y += bh + gap
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
            if side == 2:
                bx = card_w - bw - int(16 * scale)
                b_fill = (0, 138, 254, 255)
                t_fill = (255, 255, 255)
                draw_ios_bubble(bubbles_surf, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=True)
                tx = bx + pad_h - int(1 * scale)
            else:
                bx = int(16 * scale)
                b_fill = (44, 44, 46, 255) if is_dark else (232, 232, 232, 255)
                t_fill = (255, 255, 255) if is_dark else (0, 0, 0)
                draw_ios_bubble(bubbles_surf, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=False)
                tx = bx + pad_h + int(5 * scale)

        # Draw lines of text
        if len(lines) == 1:
            ty = curr_y + (bh - b['line_dims'][0][1]) // 2 - int(2 * scale)
        else:
            ty = curr_y + pad_v
        for li, line in enumerate(lines):
            draw_text_with_emojis(b_draw, (tx, ty), line, font_reg, font_emj, t_fill)
            ty += b['line_dims'][li][1] + int(4 * scale)

        curr_y += bh + gap

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
        show_header=show_header
    )

    # For web preview JPEG, composite over green chroma or background
    bg = Image.new('RGB', (W, H), (0, 255, 0))
    bg.paste(canvas, (0, 0), mask=canvas.split()[3])

    buf = io.BytesIO()
    bg.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return buf.getvalue(), total_pages


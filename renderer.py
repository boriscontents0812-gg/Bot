import os
import io
import re
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

FONTS_DIR = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')

def get_font(size, bold=False):
    font_file = 'segoeuib.ttf' if bold else 'segoeui.ttf'
    path = os.path.join(FONTS_DIR, font_file)
    if not os.path.exists(path):
        font_file = 'arialbd.ttf' if bold else 'arial.ttf'
        path = os.path.join(FONTS_DIR, font_file)
    try:
        return ImageFont.truetype(path, int(size))
    except Exception:
        return ImageFont.load_default()

def get_emoji_font(size):
    path = os.path.join(FONTS_DIR, 'seguiemj.ttf')
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, int(size))
        except Exception:
            pass
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
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    messages = []
    contact_name = "Contact"
    contacts_seen = []
    
    first_non_msg = True
    for line in lines:
        if line.startswith('---'):
            continue
        is_msg = re.match(r'^[12]:\s*', line, re.IGNORECASE)
        if is_msg:
            img_m = re.match(r'^(1|2):\s*img:\s*(.+)$', line, re.IGNORECASE)
            if img_m:
                side = int(img_m.group(1))
                img_name = img_m.group(2).strip()
                messages.append({'side': side, 'name': '', 'text': img_name, 'is_img': True})
            else:
                m = re.match(r'^(1|2):\s*([^>]+?)\s*>\s*(.+)$', line)
                if m:
                    side = int(m.group(1))
                    name = m.group(2).strip()
                    msg_text = m.group(3).strip()
                    messages.append({'side': side, 'name': name, 'text': msg_text, 'is_img': False})
                    if name not in contacts_seen:
                        contacts_seen.append(name)
        else:
            clean = re.sub(r'[^\w\s\u0080-\uffff]', '', line).strip()
            if first_non_msg and not any(kw in line.lower() for kw in ['wing', 'rizz', 'plug']):
                contact_name = line
                first_non_msg = False
            if line not in contacts_seen and not any(kw in line.lower() for kw in ['wing', 'rizz', 'plug']):
                contacts_seen.append(line)
                
    return contact_name, messages, contacts_seen

def draw_video_icon(draw, x, y, size=18, color=(0, 122, 255)):
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

def draw_ios_bubble(draw, x, y, w, h, radius, fill, is_outgoing=False):
    """Draws an iOS rounded bubble with an authentic subtle corner tail."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill)
    if is_outgoing:
        draw.polygon([(x + w - 6, y + h), (x + w + 4, y + h), (x + w, y + h - 8)], fill=fill)
    else:
        draw.polygon([(x + 6, y + h), (x - 4, y + h), (x, y + h - 8)], fill=fill)

def draw_wa_bubble(draw, x, y, w, h, radius, fill, is_outgoing=False):
    """Draws a WhatsApp rounded bubble with corner tail."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill)
    if is_outgoing:
        draw.polygon([(x + w - 4, y + h - 10), (x + w + 6, y + h), (x + w - 4, y + h)], fill=fill)
    else:
        draw.polygon([(x + 4, y + h - 10), (x - 6, y + h), (x + 4, y + h)], fill=fill)

def render_chat_frame(messages, visible_count, contact_name="Contact", badge_count=0, style='ios', theme='light', width=1080, height=1920, chat_y_pct=None, container_scale=1.0, corner_radius_val=35, font_size_override=None, contact_avatar_img=None):
    """
    Renders an authentic, floating iOS or WhatsApp chat card onto a transparent RGBA canvas.
    - True soft Gaussian drop shadow (no green chroma keying).
    - Dynamic card height: hugs content up to max_card_h.
    - Smooth auto-scrolling when content exceeds card bounds.
    """
    scale = width / 540.0
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))

    is_dark = (theme == 'dark')
    card_w = int(430 * scale * container_scale)
    corner_radius = int(corner_radius_val * (scale / 2.0)) if corner_radius_val else int(35 * scale)
    card_x = (width - card_w) // 2

    # Bubble and font settings
    f_size = font_size_override or int(16 * scale)
    font_reg = get_font(f_size, bold=False)
    font_emj = get_emoji_font(f_size)
    max_bubble_w = int(card_w * 0.72)
    pad_h = int(14 * scale)
    pad_v = int(10 * scale)
    b_radius = int(18 * scale) if style == 'ios' else int(10 * scale)
    gap = int(10 * scale)

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
            if lw <= (max_bubble_w - pad_h * 2):
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
        bw = max(d[0] for d in line_dims) + pad_h * 2
        bh = sum(d[1] for d in line_dims) + (len(lines) - 1) * int(4 * scale) + pad_v * 2

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
    hdr_h = int(82 * scale) if style == 'ios' else int(65 * scale)
    min_card_h = hdr_h + int(80 * scale)
    max_card_h = int(height * 0.52)
    content_area_pad = int(16 * scale)

    needed_card_h = hdr_h + total_content_h + content_area_pad
    card_h = max(min_card_h, min(needed_card_h, max_card_h))

    if chat_y_pct is not None:
        card_y = int(height * chat_y_pct)
    else:
        card_y = int(145 * scale)

    # Auto-scroll calculation
    max_visible_content_h = card_h - hdr_h - content_area_pad
    scroll_y = 0
    if total_content_h > max_visible_content_h:
        scroll_y = total_content_h - max_visible_content_h

    # 3. Soft Drop Shadow
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
        hdr_col = (32, 44, 51, 255) if is_dark else (0, 128, 105, 255)
        text_col = (233, 237, 239) if is_dark else (255, 255, 255)
        sub_text_col = (134, 150, 160) if is_dark else (220, 240, 235)
        card_draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=bg_col)
        # WhatsApp Header
        card_draw.rounded_rectangle([0, 0, card_w, hdr_h], radius=corner_radius, fill=hdr_col)
        card_draw.rectangle([0, hdr_h - corner_radius, card_w, hdr_h], fill=hdr_col)
        
        # Back <
        card_draw.text((int(14 * scale), int(16 * scale)), "<", fill=text_col, font=get_font(24 * scale, True))
        
        # Avatar
        av_d = int(42 * scale)
        av_x = int(44 * scale)
        av_y = (hdr_h - av_d) // 2
        card_draw.ellipse([av_x, av_y, av_x + av_d, av_y + av_d], fill=(120, 140, 150))
        init_letter = contact_name[0].upper() if contact_name else "C"
        av_font = get_font(18 * scale, bold=True)
        abox = card_draw.textbbox((0, 0), init_letter, font=av_font)
        card_draw.text((av_x + (av_d - (abox[2] - abox[0])) // 2, av_y + (av_d - (abox[3] - abox[1])) // 2 - int(2 * scale)), init_letter, fill=(255, 255, 255), font=av_font)

        # Name and Status
        n_font = get_font(14 * scale, bold=True)
        s_font = get_font(11 * scale, bold=False)
        card_draw.text((av_x + av_d + int(10 * scale), av_y + int(2 * scale)), contact_name, fill=text_col, font=n_font)
        card_draw.text((av_x + av_d + int(10 * scale), av_y + int(22 * scale)), "online", fill=sub_text_col, font=s_font)

        # Call icons
        draw_video_icon(card_draw, card_w - int(60 * scale), int(22 * scale), size=int(16 * scale), color=text_col)
        draw_phone_icon(card_draw, card_w - int(30 * scale), int(22 * scale), size=int(15 * scale), color=text_col)

    else:
        # iOS iMessage Card
        card_bg_col = (28, 28, 30, 255) if is_dark else (255, 255, 255, 255)
        card_draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=card_bg_col)

        # Chevron <
        chev_font = get_font(26 * scale, bold=True)
        card_draw.text((int(14 * scale), int(18 * scale)), "<", fill=(0, 122, 255), font=chev_font)

        # Unread badge
        if badge_count > 0:
            b_font = get_font(13 * scale, bold=True)
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

        # Center Avatar
        av_d = int(46 * scale)
        av_x = (card_w - av_d) // 2
        av_y = int(10 * scale)
        card_draw.ellipse([av_x, av_y, av_x + av_d, av_y + av_d], fill=(142, 142, 147))
        init_letter = contact_name[0].upper() if contact_name else "C"
        av_font = get_font(21 * scale, bold=True)
        abox = card_draw.textbbox((0, 0), init_letter, font=av_font)
        card_draw.text((av_x + (av_d - (abox[2] - abox[0])) // 2, av_y + (av_d - (abox[3] - abox[1])) // 2 - int(2 * scale)), init_letter, fill=(255, 255, 255), font=av_font)

        # Contact Name
        name_font_reg = get_font(12 * scale, bold=False)
        name_font_emj = get_emoji_font(12 * scale)
        name_text = f"{contact_name} ›"
        nw, _ = measure_text_with_emojis(card_draw, name_text, name_font_reg, name_font_emj)
        name_x = (card_w - nw) // 2
        name_y = av_y + av_d + int(4 * scale)
        text_color = (255, 255, 255) if is_dark else (0, 0, 0)
        draw_text_with_emojis(card_draw, (name_x, name_y), name_text, name_font_reg, name_font_emj, text_color)

        # FaceTime Camera Icon
        v_icon_x = card_w - int(48 * scale)
        v_icon_y = int(22 * scale)
        draw_video_icon(card_draw, v_icon_x, v_icon_y, size=int(22 * scale), color=(0, 122, 255))

        # Divider line
        div_col = (56, 56, 58) if is_dark else (229, 229, 234)
        card_draw.line([(0, hdr_h), (card_w, hdr_h)], fill=div_col, width=int(1 * scale))

    # 5. Message Bubbles
    bubbles_surf = Image.new('RGBA', (card_w, card_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(bubbles_surf)

    curr_y = hdr_h + int(12 * scale) - scroll_y
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
            else:
                bx = int(16 * scale)
                b_fill = (32, 44, 51) if is_dark else (255, 255, 255)
                t_fill = (233, 237, 239) if is_dark else (17, 27, 33)
                draw_wa_bubble(b_draw, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=False)
        else:
            if side == 2:
                bx = card_w - bw - int(16 * scale)
                b_fill = (0, 122, 255)
                t_fill = (255, 255, 255)
                draw_ios_bubble(b_draw, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=True)
            else:
                bx = int(16 * scale)
                b_fill = (44, 44, 46) if is_dark else (233, 233, 235)
                t_fill = (255, 255, 255) if is_dark else (0, 0, 0)
                draw_ios_bubble(b_draw, bx, curr_y, bw, bh, b_radius, b_fill, is_outgoing=False)

        # Draw lines of text
        ty = curr_y + pad_v
        for li, line in enumerate(lines):
            draw_text_with_emojis(b_draw, (bx + pad_h, ty), line, font_reg, font_emj, t_fill)
            ty += b['line_dims'][li][1] + int(4 * scale)

        curr_y += bh + gap

    # Clip bubbles cleanly to card body below header
    mask = Image.new('L', (card_w, card_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=255)
    m_draw.rectangle([0, 0, card_w, hdr_h], fill=0)

    r, g, b, a = bubbles_surf.split()
    a = ImageChops.multiply(a, mask)
    bubbles_surf.putalpha(a)

    card_img.alpha_composite(bubbles_surf, (0, 0))
    canvas.alpha_composite(card_img, (card_x, card_y))
    return canvas

def render_preview_image(body):
    style = body.get('style', 'ios')
    script_text = body.get('script', '')
    page = int(body.get('page', 0))
    contact_name, messages, contacts = parse_script(script_text)

    W, H = 540, 960
    msgs_per_page = int(body.get('msgs_per_page', 6))
    if msgs_per_page < 1:
        msgs_per_page = 6
    total_pages = max(1, math.ceil(len(messages) / msgs_per_page))
    page = max(0, min(page, total_pages - 1))
    
    page_msgs = messages[page * msgs_per_page : (page + 1) * msgs_per_page]
    theme = body.get('theme', 'light') if style == 'ios' else body.get('wa_theme', 'light')
    badge_count = int(body.get('badge_count', 0))

    canvas = render_chat_frame(
        page_msgs,
        visible_count=len(page_msgs),
        contact_name=contact_name,
        badge_count=badge_count,
        style=style,
        theme=theme,
        width=W,
        height=H,
        chat_y_pct=None,
        container_scale=float(body.get('container_scale', 1.0)),
        corner_radius_val=int(body.get('corner_radius', 35))
    )

    # For web preview JPEG, composite over green chroma or background
    bg = Image.new('RGB', (W, H), (0, 255, 0))
    bg.paste(canvas, (0, 0), mask=canvas.split()[3])

    buf = io.BytesIO()
    bg.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return buf.getvalue(), total_pages

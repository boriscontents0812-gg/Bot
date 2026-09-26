import os
import io
import re
import math
from PIL import Image, ImageDraw, ImageFont

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

def wrap_text(text, font, max_width, draw):
    lines = []
    words = text.split(' ')
    curr_line = []
    
    for word in words:
        test_line = ' '.join(curr_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            curr_line.append(word)
        else:
            if curr_line:
                lines.append(' '.join(curr_line))
                curr_line = [word]
            else:
                lines.append(word)
                curr_line = []
    if curr_line:
        lines.append(' '.join(curr_line))
    return lines or [text]

def draw_video_icon(draw, x, y, size=18, color=(0, 122, 255)):
    # Camera body
    bw = int(size * 0.95)
    bh = int(size * 0.7)
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=4, fill=color)
    # Camera lens triangle
    tx1 = x + bw + 2
    ty1 = y + bh // 2 - int(size * 0.35)
    tx2 = x + bw + int(size * 0.4)
    ty2 = y + bh // 2
    tx3 = x + bw + 2
    ty3 = y + bh // 2 + int(size * 0.35)
    draw.polygon([(tx1, ty1), (tx2, ty2), (tx3, ty3)], fill=color)

def draw_phone_icon(draw, x, y, size=16, color=(0, 122, 255)):
    draw.rounded_rectangle([x, y, x + size, y + size], radius=3, fill=color)

def render_preview_image(body):
    style = body.get('style', 'ios')
    script_text = body.get('script', '')
    page = int(body.get('page', 0))
    contact_name, messages, contacts = parse_script(script_text)

    # Resolution: 540x960
    W, H = 540, 960
    scale = 0.5

    img = Image.new('RGB', (W, H), (0, 255, 0)) # Chroma Green
    draw = ImageDraw.Draw(img)

    msgs_per_page = int(body.get('msgs_per_page', 6))
    if msgs_per_page < 1:
        msgs_per_page = 6
    total_pages = max(1, math.ceil(len(messages) / msgs_per_page))
    page = max(0, min(page, total_pages - 1))
    
    page_msgs = messages[page * msgs_per_page : (page + 1) * msgs_per_page]

    container_scale = float(body.get('container_scale', 1.0))
    c_w = int(W * 0.85 * container_scale)
    c_x = (W - c_w) // 2
    chat_y = int(body.get('chat_y', 350 if style == 'ios' else 280) * scale)

    rounded_corners = int(body.get('rounded_corners', 0))
    corner_radius = int(body.get('corner_radius', 35) * scale) if rounded_corners else 0

    if style == 'whatsapp':
        is_dark = body.get('wa_theme', 'dark') == 'dark'
        bg_col = (11, 20, 26) if is_dark else (239, 234, 226)
        hdr_col = (32, 44, 51) if is_dark else (240, 242, 245)
        text_col = (233, 237, 239) if is_dark else (17, 27, 33)
        sub_text_col = (134, 150, 160) if is_dark else (102, 119, 129)
        c_h = int(H * (float(body.get('chat_height_pct', 100)) / 100.0) * 0.44)

        if corner_radius > 0:
            draw.rounded_rectangle([c_x, chat_y, c_x + c_w, chat_y + c_h], radius=corner_radius, fill=bg_col)
        else:
            draw.rectangle([c_x, chat_y, c_x + c_w, chat_y + c_h], fill=bg_col)

        # Header
        hdr_h = 60
        if corner_radius > 0:
            draw.rounded_rectangle([c_x, chat_y, c_x + c_w, chat_y + hdr_h], radius=corner_radius, fill=hdr_col)
            draw.rectangle([c_x, chat_y + hdr_h - corner_radius, c_x + c_w, chat_y + hdr_h], fill=hdr_col)
        else:
            draw.rectangle([c_x, chat_y, c_x + c_w, chat_y + hdr_h], fill=hdr_col)

        # Chevron <
        draw.text((c_x + 14, chat_y + 14), "<", fill=(0, 122, 255), font=get_font(24, True))

        # Avatar
        av_r = 18
        av_cx, av_cy = c_x + 52, chat_y + hdr_h // 2
        draw.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(210, 215, 220))
        draw.text((av_cx - 6, av_cy - 10), contact_name[0].upper(), fill=(100, 110, 120), font=get_font(16, True))

        # Name and Status
        draw.text((c_x + 80, chat_y + 10), contact_name, fill=text_col, font=get_font(16, True))
        draw.text((c_x + 80, chat_y + 32), "Online", fill=sub_text_col, font=get_font(12, False))

        # Icons
        draw_video_icon(draw, c_x + c_w - 65, chat_y + 20, size=16, color=(0, 122, 255))
        draw_phone_icon(draw, c_x + c_w - 30, chat_y + 20, size=15, color=(0, 122, 255))

        # Messages
        curr_y = chat_y + hdr_h + 16
        font_size = max(11, int(body.get('font_size', 50) * scale * 0.7))
        msg_font = get_font(font_size)
        pad_x, pad_y = 14, 8
        bubble_max_w = int(c_w * (float(body.get('bubble_max_pct', 82)) / 100.0))

        for msg in page_msgs:
            side = msg['side']
            text = msg['text']
            lines = wrap_text(text, msg_font, bubble_max_w - pad_x * 2, draw)
            
            line_heights = [draw.textbbox((0, 0), l, font=msg_font)[3] - draw.textbbox((0, 0), l, font=msg_font)[1] for l in lines]
            line_widths = [draw.textbbox((0, 0), l, font=msg_font)[2] - draw.textbbox((0, 0), l, font=msg_font)[0] for l in lines]
            
            b_w = max(line_widths) + pad_x * 2
            b_h = sum(line_heights) + (len(lines) - 1) * 4 + pad_y * 2

            if side == 2:
                b_x = c_x + c_w - b_w - 14
                b_col = (0, 92, 75) if is_dark else (217, 253, 211)
                t_col = (233, 237, 239) if is_dark else (17, 27, 33)
                draw.rounded_rectangle([b_x, curr_y, b_x + b_w, curr_y + b_h], radius=10, fill=b_col)
                # Outgoing tail
                draw.polygon([(b_x + b_w - 4, curr_y + b_h - 10), (b_x + b_w + 6, curr_y + b_h), (b_x + b_w - 4, curr_y + b_h)], fill=b_col)
            else:
                b_x = c_x + 14
                b_col = (32, 44, 51) if is_dark else (255, 255, 255)
                t_col = (233, 237, 239) if is_dark else (17, 27, 33)
                draw.rounded_rectangle([b_x, curr_y, b_x + b_w, curr_y + b_h], radius=10, fill=b_col)
                # Incoming tail
                draw.polygon([(b_x + 4, curr_y + b_h - 10), (b_x - 6, curr_y + b_h), (b_x + 4, curr_y + b_h)], fill=b_col)

            ty = curr_y + pad_y
            for i, l in enumerate(lines):
                draw.text((b_x + pad_x, ty), l, fill=t_col, font=msg_font)
                ty += line_heights[i] + 4

            curr_y += b_h + 10
            if curr_y > chat_y + c_h - 20:
                break

    else:  # iOS iMessage
        is_dark = body.get('theme', 'dark') == 'dark'
        bg_col = (0, 0, 0) if is_dark else (255, 255, 255)
        hdr_col = (20, 20, 20) if is_dark else (245, 245, 247)
        c_h = int(H * 0.42)

        if corner_radius > 0:
            draw.rounded_rectangle([c_x, chat_y, c_x + c_w, chat_y + c_h], radius=corner_radius, fill=bg_col)
        else:
            draw.rectangle([c_x, chat_y, c_x + c_w, chat_y + c_h], fill=bg_col)

        # Header
        hdr_h = 70
        if corner_radius > 0:
            draw.rounded_rectangle([c_x, chat_y, c_x + c_w, chat_y + hdr_h], radius=corner_radius, fill=hdr_col)
            draw.rectangle([c_x, chat_y + hdr_h - corner_radius, c_x + c_w, chat_y + hdr_h], fill=hdr_col)
        else:
            draw.rectangle([c_x, chat_y, c_x + c_w, chat_y + hdr_h], fill=hdr_col)

        # Back chevron
        draw.text((c_x + 14, chat_y + 16), "<", fill=(0, 122, 255), font=get_font(24, True))

        # Avatar in center
        av_r = 18
        av_cx, av_cy = c_x + c_w // 2, chat_y + 24
        draw.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(120, 120, 128))
        draw.text((av_cx - 6, av_cy - 10), contact_name[0].upper(), fill=(255, 255, 255), font=get_font(15, True))

        # Contact Name
        name_font = get_font(12, False)
        bbox = draw.textbbox((0, 0), contact_name + " >", font=name_font)
        name_w = bbox[2] - bbox[0]
        draw.text((c_x + (c_w - name_w) // 2, chat_y + 46), contact_name + " >", fill=(142, 142, 147), font=name_font)

        # Camera icon
        draw_video_icon(draw, c_x + c_w - 40, chat_y + 22, size=18, color=(0, 122, 255))

        # Messages area
        curr_y = chat_y + hdr_h + 14
        font_size = max(11, int(body.get('font_size', 48) * scale * 0.7))
        msg_font = get_font(font_size)
        pad_x, pad_y = 14, 8
        bubble_max_w = int(c_w * (float(body.get('bubble_max_pct', 58)) / 100.0))

        for msg in page_msgs:
            side = msg['side']
            text = msg['text']
            lines = wrap_text(text, msg_font, bubble_max_w - pad_x * 2, draw)

            line_heights = [draw.textbbox((0, 0), l, font=msg_font)[3] - draw.textbbox((0, 0), l, font=msg_font)[1] for l in lines]
            line_widths = [draw.textbbox((0, 0), l, font=msg_font)[2] - draw.textbbox((0, 0), l, font=msg_font)[0] for l in lines]

            b_w = max(line_widths) + pad_x * 2
            b_h = sum(line_heights) + (len(lines) - 1) * 4 + pad_y * 2

            if side == 2:
                b_x = c_x + c_w - b_w - 14
                b_col = (0, 122, 255)
                t_col = (255, 255, 255)
                draw.rounded_rectangle([b_x, curr_y, b_x + b_w, curr_y + b_h], radius=16, fill=b_col)
                # Tail
                draw.polygon([(b_x + b_w - 4, curr_y + b_h - 10), (b_x + b_w + 6, curr_y + b_h), (b_x + b_w - 4, curr_y + b_h)], fill=b_col)
            else:
                b_x = c_x + 14
                b_col = (38, 37, 42) if is_dark else (233, 233, 235)
                t_col = (255, 255, 255) if is_dark else (0, 0, 0)
                draw.rounded_rectangle([b_x, curr_y, b_x + b_w, curr_y + b_h], radius=16, fill=b_col)
                # Tail
                draw.polygon([(b_x + 4, curr_y + b_h - 10), (b_x - 6, curr_y + b_h), (b_x + 4, curr_y + b_h)], fill=b_col)

            ty = curr_y + pad_y
            for i, l in enumerate(lines):
                draw.text((b_x + pad_x, ty), l, fill=t_col, font=msg_font)
                ty += line_heights[i] + 4

            curr_y += b_h + 10
            if curr_y > chat_y + c_h - 20:
                break

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return buf.getvalue(), total_pages

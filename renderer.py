import os
import io
import re
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS_DIR = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

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

def get_gameplay_frame(gameplay_filename, start_time="0:00"):
    if not gameplay_filename or gameplay_filename == 'none':
        return None
    
    p = os.path.join(DATA_DIR, "gameplay", gameplay_filename)
    if not os.path.exists(p):
        return None

    cache_dir = os.path.join(DATA_DIR, "gameplay_cache")
    os.makedirs(cache_dir, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', gameplay_filename)
    safe_time = re.sub(r'[^0-9]', '_', str(start_time))
    cache_path = os.path.join(cache_dir, f"{safe_name}_{safe_time}.jpg")

    if not os.path.exists(cache_path) or os.path.getsize(cache_path) < 100:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            ss = f"00:{start_time}" if len(str(start_time).split(':')) == 2 else str(start_time)
            cmd = [ffmpeg, '-y', '-ss', ss, '-i', p, '-vframes', '1', cache_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        except Exception:
            return None

    if os.path.exists(cache_path):
        try:
            im = Image.open(cache_path).convert('RGBA')
            # Scale and crop to 1080x1920
            target_w, target_h = 1080, 1920
            scale = max(target_w / im.width, target_h / im.height)
            nw, nh = int(im.width * scale), int(im.height * scale)
            im_resized = im.resize((nw, nh), Image.Resampling.BILINEAR)
            left = (nw - target_w) // 2
            top = (nh - target_h) // 2
            return im_resized.crop((left, top, left + target_w, top + target_h))
        except Exception:
            return None
    return None

def render_preview_image(body, visible_count=None, return_rgba=False):
    style = body.get('style', 'ios')
    script_text = body.get('script', '')
    page = int(body.get('page', 0))
    contact_name, messages, contacts = parse_script(script_text)

    W, H = 1080, 1920

    # Determine background
    gameplay_on = body.get('gameplay_on', False)
    if isinstance(gameplay_on, str):
        gameplay_on = gameplay_on.lower() in ('1', 'true', 'yes')
    gameplay_file = body.get('gameplay_file', '')
    gameplay_start = body.get('gameplay_start', '0:00')

    if return_rgba:
        base_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    elif gameplay_on and gameplay_file and gameplay_file != 'none':
        gp_frame = get_gameplay_frame(gameplay_file, gameplay_start)
        if gp_frame:
            base_img = gp_frame
        else:
            base_img = Image.new('RGBA', (W, H), (0, 255, 0, 255))
    else:
        # Green screen background (or dark canvas)
        base_img = Image.new('RGBA', (W, H), (0, 255, 0, 255))

    msgs_per_page = int(body.get('msgs_per_page', 6))
    if msgs_per_page < 1:
        msgs_per_page = 6

    if visible_count is not None:
        count = min(len(messages), max(1, int(visible_count)))
        if count <= msgs_per_page:
            page_msgs = messages[0:count]
        else:
            page_msgs = messages[count - msgs_per_page : count]
        total_pages = 1
    else:
        total_pages = max(1, math.ceil(len(messages) / msgs_per_page))
        page = max(0, min(page, total_pages - 1))
        page_msgs = messages[page * msgs_per_page : (page + 1) * msgs_per_page]

    container_scale = float(body.get('container_scale', 1.0))
    c_w = int(820 * container_scale)
    c_x = (W - c_w) // 2
    chat_y = int(body.get('chat_y', 350 if style == 'ios' else 280))

    corner_radius = int(body.get('corner_radius', 32))
    show_shadow = bool(body.get('container_shadow', 1))

    # Fonts
    f_large_b = get_font(42, bold=True)
    f_med = get_font(26, bold=False)
    f_bubble = get_font(int(body.get('font_size', 44)), bold=False)
    f_av = get_font(34, bold=True)

    pad_x, pad_y = 26, 18
    gap = 18
    hdr_h = 145 if style == 'ios' else 130
    bubble_max_w = int(c_w * (float(body.get('bubble_max_pct', 65 if style == 'ios' else 82)) / 100.0))

    # Pre-measure bubbles to dynamically size card height
    dummy_draw = ImageDraw.Draw(base_img)
    bubble_data = []
    for m in page_msgs:
        words = m['text'].split(' ')
        lines = []
        cur = []
        for w in words:
            test = ' '.join(cur + [w])
            bb = dummy_draw.textbbox((0, 0), test, font=f_bubble)
            if (bb[2] - bb[0]) <= bubble_max_w - pad_x * 2:
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
        
        lw = max((dummy_draw.textbbox((0, 0), l, font=f_bubble)[2] - dummy_draw.textbbox((0, 0), l, font=f_bubble)[0] for l in lines), default=40)
        lh = sum(dummy_draw.textbbox((0, 0), l, font=f_bubble)[3] - dummy_draw.textbbox((0, 0), l, font=f_bubble)[1] + 6 for l in lines) - 6
        bw = lw + pad_x * 2
        bh = max(lh + pad_y * 2, 60)
        bubble_data.append((m, bw, bh, lines))

    total_bh = sum(b[2] + gap for b in bubble_data)
    # Dynamic card height tightly wrapped around content
    c_h = hdr_h + total_bh + 20

    # Draw Drop Shadow
    if show_shadow:
        s_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(s_layer)
        s_draw.rounded_rectangle([c_x, chat_y + 12, c_x + c_w, chat_y + c_h + 12], radius=corner_radius, fill=(0, 0, 0, 140))
        s_layer = s_layer.filter(ImageFilter.GaussianBlur(radius=26))
        base_img.alpha_composite(s_layer)

    draw = ImageDraw.Draw(base_img)

    if style == 'whatsapp':
        is_dark = body.get('wa_theme', 'dark') == 'dark'
        card_bg = (17, 27, 33, 255) if is_dark else (239, 234, 226, 255)
        hdr_bg = (32, 44, 51, 255) if is_dark else (240, 242, 245, 255)
        text_col = (233, 237, 239, 255) if is_dark else (17, 27, 33, 255)
        sub_text_col = (134, 150, 160, 255) if is_dark else (102, 119, 129, 255)

        draw.rounded_rectangle([c_x, chat_y, c_x + c_w, chat_y + c_h], radius=corner_radius, fill=card_bg)
        draw.rounded_rectangle([c_x, chat_y, c_x + c_w, chat_y + hdr_h], radius=corner_radius, fill=hdr_bg)
        draw.rectangle([c_x, chat_y + hdr_h - corner_radius, c_x + c_w, chat_y + hdr_h], fill=hdr_bg)

        # Chevron
        draw.text((c_x + 30, chat_y + 32), '<', fill=(0, 122, 255, 255), font=f_large_b)

        # Avatar
        av_cx = c_x + 110
        av_cy = chat_y + hdr_h // 2
        av_r = 34
        draw.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(120, 120, 128, 255))
        draw.text((av_cx - 12, av_cy - 20), contact_name[0].upper(), fill=(255, 255, 255, 255), font=f_av)

        # Name & status
        draw.text((c_x + 165, chat_y + 24), contact_name, fill=text_col, font=get_font(30, bold=True))
        draw.text((c_x + 165, chat_y + 68), "Online", fill=sub_text_col, font=get_font(22, bold=False))

        # Video & Call icons
        cam_x = c_x + c_w - 120
        cam_y = chat_y + 45
        draw.rounded_rectangle([cam_x, cam_y, cam_x + 32, cam_y + 24], radius=6, fill=(0, 122, 255, 255))
        draw.polygon([(cam_x + 35, cam_y + 4), (cam_x + 46, cam_y + 12), (cam_x + 35, cam_y + 20)], fill=(0, 122, 255, 255))

        cy = chat_y + hdr_h + 12
        for m, bw, bh, lines in bubble_data:
            side = m['side']
            if side == 2:
                bx = c_x + c_w - bw - 28
                bcol = (0, 92, 75, 255) if is_dark else (217, 253, 211, 255)
                tcol = (233, 237, 239, 255) if is_dark else (17, 27, 33, 255)
                draw.rounded_rectangle([bx, cy, bx + bw, cy + bh], radius=22, fill=bcol)
                draw.polygon([(bx + bw - 8, cy + bh - 14), (bx + bw + 10, cy + bh), (bx + bw - 8, cy + bh)], fill=bcol)
            else:
                bx = c_x + 28
                bcol = (32, 44, 51, 255) if is_dark else (255, 255, 255, 255)
                tcol = (233, 237, 239, 255) if is_dark else (17, 27, 33, 255)
                draw.rounded_rectangle([bx, cy, bx + bw, cy + bh], radius=22, fill=bcol)
                draw.polygon([(bx + 8, cy + bh - 14), (bx - 10, cy + bh), (bx + 8, cy + bh)], fill=bcol)

            ty = cy + pad_y
            for l in lines:
                draw.text((bx + pad_x, ty), l, fill=tcol, font=f_bubble)
                ty += dummy_draw.textbbox((0, 0), l, font=f_bubble)[3] - dummy_draw.textbbox((0, 0), l, font=f_bubble)[1] + 6
            cy += bh + gap

    else:  # iOS iMessage (Native iOS style matching sample_preview.png)
        is_dark = body.get('theme', 'dark') == 'dark'
        card_bg = (26, 26, 26, 255) if is_dark else (255, 255, 255, 255)
        
        draw.rounded_rectangle([c_x, chat_y, c_x + c_w, chat_y + c_h], radius=corner_radius, fill=card_bg)

        # Chevron <
        draw.text((c_x + 32, chat_y + 36), '<', fill=(0, 122, 255, 255), font=f_large_b)

        # Center Avatar
        av_cx = c_x + c_w // 2
        av_cy = chat_y + 46
        av_r = 34
        
        # Check custom contact photo
        photo_drawn = False
        safe_cname = re.sub(r'[^a-zA-Z0-9_-]', '_', contact_name)
        photo_path = os.path.join(DATA_DIR, "contact_photos", f"{safe_cname}_ios.jpg")
        if os.path.exists(photo_path):
            try:
                cp_img = Image.open(photo_path).convert('RGBA').resize((av_r * 2, av_r * 2))
                mask = Image.new('L', (av_r * 2, av_r * 2), 0)
                m_draw = ImageDraw.Draw(mask)
                m_draw.ellipse([0, 0, av_r * 2, av_r * 2], fill=255)
                base_img.paste(cp_img, (av_cx - av_r, av_cy - av_r), mask)
                photo_drawn = True
            except Exception:
                pass

        if not photo_drawn:
            draw.ellipse([av_cx - av_r, av_cy - av_r, av_cx + av_r, av_cy + av_r], fill=(120, 120, 128, 255))
            draw.text((av_cx - 12, av_cy - 20), contact_name[0].upper(), fill=(255, 255, 255, 255), font=f_av)

        # Contact Name
        name_text = f"{contact_name} >"
        nbb = draw.textbbox((0, 0), name_text, font=f_med)
        nw = nbb[2] - nbb[0]
        draw.text((av_cx - nw // 2, chat_y + 92), name_text, fill=(142, 142, 147, 255), font=f_med)

        # Camera icon
        cam_x = c_x + c_w - 76
        cam_y = chat_y + 44
        draw.rounded_rectangle([cam_x, cam_y, cam_x + 32, cam_y + 24], radius=6, fill=(0, 122, 255, 255))
        draw.polygon([(cam_x + 35, cam_y + 4), (cam_x + 46, cam_y + 12), (cam_x + 35, cam_y + 20)], fill=(0, 122, 255, 255))

        # Draw bubbles
        cy = chat_y + hdr_h + 10
        for m, bw, bh, lines in bubble_data:
            side = m['side']
            if side == 2:
                bx = c_x + c_w - bw - 28
                bcol = (0, 122, 255, 255)
                tcol = (255, 255, 255, 255)
                draw.rounded_rectangle([bx, cy, bx + bw, cy + bh], radius=28, fill=bcol)
                # Tail
                draw.polygon([(bx + bw - 10, cy + bh - 16), (bx + bw + 12, cy + bh), (bx + bw - 10, cy + bh)], fill=bcol)
            else:
                bx = c_x + 28
                bcol = (38, 37, 42, 255) if is_dark else (233, 233, 235, 255)
                tcol = (255, 255, 255, 255) if is_dark else (0, 0, 0, 255)
                draw.rounded_rectangle([bx, cy, bx + bw, cy + bh], radius=28, fill=bcol)
                # Tail
                draw.polygon([(bx + 10, cy + bh - 16), (bx - 12, cy + bh), (bx + 10, cy + bh)], fill=bcol)
                
            ty = cy + pad_y
            for l in lines:
                draw.text((bx + pad_x, ty), l, fill=tcol, font=f_bubble)
                ty += dummy_draw.textbbox((0, 0), l, font=f_bubble)[3] - dummy_draw.textbbox((0, 0), l, font=f_bubble)[1] + 6
                
            cy += bh + gap

    buf = io.BytesIO()
    if return_rgba:
        base_img.save(buf, format='PNG')
    else:
        base_img.convert('RGB').save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return buf.getvalue(), total_pages

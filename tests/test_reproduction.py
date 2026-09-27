import math, os
from PIL import Image, ImageDraw, ImageFont

def get_font_test(size, bold=False):
    for f in ['C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf']:
        if os.path.exists(f):
            return ImageFont.truetype(f, int(size))
    return ImageFont.load_default()

def render_imessage_bubble_mask(w, h, is_outgoing=False):
    ss = 4
    sw, sh = int(w * ss), int(h * ss)
    mask = Image.new('L', (sw, sh), 0)
    draw = ImageDraw.Draw(mask)
    
    r = min(int(36 * ss), sh // 2)
    pts = []
    
    if is_outgoing:
        tail_w = int(14 * ss)
        body_w = sw - tail_w
        
        # 1. Top-left arc (center at (r, r), 180 to 270 deg)
        for deg in range(180, 271, 3):
            rad = math.radians(deg)
            pts.append((r + r * math.cos(rad), r + r * math.sin(rad)))
            
        # 2. Top edge
        pts.append((body_w - r, 0))
        
        # 3. Top-right arc (center at (body_w - r, r), 270 to 360 deg)
        for deg in range(270, 361, 3):
            rad = math.radians(deg)
            pts.append((body_w - r + r * math.cos(rad), r + r * math.sin(rad)))
            
        # 4. Right edge down to tail inflection: y = sh - 24*ss
        tail_y0 = sh - int(24 * ss)
        pts.append((body_w, tail_y0))
        
        # 5. Tail outer sweep to tip at (sw, sh)
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
            
        # 6. Tail underside scoop: sweeps in to baseline
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
            
        # 7. Bottom edge to bottom-left arc
        pts.append((r, sh))
        for deg in range(90, 181, 3):
            rad = math.radians(deg)
            pts.append((r + r * math.cos(rad), sh - r + r * math.sin(rad)))
            
    else:
        # Incoming: tail on bottom-left (mirrored)
        tail_w = int(14 * ss)
        body_x0 = tail_w
        body_x1 = sw
        
        # 1. Top-left arc (center at (body_x0 + r, r), 180 to 270 deg)
        for deg in range(180, 271, 3):
            rad = math.radians(deg)
            pts.append((body_x0 + r + r * math.cos(rad), r + r * math.sin(rad)))
            
        # 2. Top edge
        pts.append((body_x1 - r, 0))
        
        # 3. Top-right arc (center at (body_x1 - r, r), 270 to 360 deg)
        for deg in range(270, 361, 3):
            rad = math.radians(deg)
            pts.append((body_x1 - r + r * math.cos(rad), r + r * math.sin(rad)))
            
        # 4. Right edge and bottom-right arc
        pts.append((body_x1, sh - r))
        for deg in range(0, 91, 3):
            rad = math.radians(deg)
            pts.append((body_x1 - r + r * math.cos(rad), sh - r + r * math.sin(rad)))
            
        # 5. Bottom edge to tail scoop start
        pts.append((body_x0 + int(34 * ss), sh))
        
        # 6. Underside scoop to tip at (0, sh)
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
            
        # 7. Outer tail curve to left vertical edge
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
    return mask.resize((w, h), Image.Resampling.LANCZOS)

def run():
    width, height = 1080, 1920
    card_w = 808
    scale = 2.0
    hdr_h = 145
    
    msgs = [
        {'side': 1, 'text': 'hey'},
        {'side': 2, 'text': 'hey you'},
        {'side': 1, 'text': "I know it's late"},
        {'side': 2, 'text': "it's never too late for you"}
    ]
    
    font = get_font_test(36)
    dummy_img = Image.new('RGBA', (10, 10))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    gap = 14
    pad_h = 28
    pad_v = 24
    
    bubbles_info = []
    total_h = 0
    for m in msgs:
        bbox = dummy_draw.textbbox((0, 0), m['text'], font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        bw = tw + pad_h * 2 + 14
        bh = max(86, th + pad_v * 2)
        bubbles_info.append({'side': m['side'], 'text': m['text'], 'bw': bw, 'bh': bh, 'tw': tw, 'th': th})
        total_h += bh + gap
        
    card_h = hdr_h + 16 + total_h + 10
    
    card = Image.new('RGBA', (card_w, card_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)
    
    # Header background
    draw.rectangle([0, 0, card_w, hdr_h], fill=(244, 244, 244, 255))
    draw.line([(0, hdr_h - 1), (card_w, hdr_h - 1)], fill=(229, 229, 229, 255), width=1)
    
    # Chevron <
    cx0, cy0 = 36, 50
    draw.line([(cx0 + 22, cy0), (cx0 + 2, cy0 + 20), (cx0 + 22, cy0 + 40)], fill=(0, 122, 255, 255), width=5, joint='round')
    
    # Avatar gradient
    av_x, av_y, av_d = (card_w - 96) // 2, 20, 96
    av_mask = Image.new('L', (av_d, av_d), 0)
    av_mdraw = ImageDraw.Draw(av_mask)
    av_mdraw.ellipse([0, 0, av_d, av_d], fill=255)
    av_grad = Image.new('RGBA', (av_d, av_d))
    for y in range(av_d):
        t = y / float(av_d)
        r = int(160 * (1 - t) + 113 * t)
        g = int(165 * (1 - t) + 116 * t)
        b = int(176 * (1 - t) + 127 * t)
        for x in range(av_d):
            av_grad.putpixel((x, y), (r, g, b, 255))
    av_grad.putalpha(av_mask)
    card.alpha_composite(av_grad, (av_x, av_y))
    
    # Avatar Initial letter
    av_font = get_font_test(46, bold=True)
    abox = draw.textbbox((0, 0), 'B', font=av_font)
    atw, ath = abox[2] - abox[0], abox[3] - abox[1]
    draw.text((av_x + (av_d - atw) // 2, av_y + (av_d - ath) // 2 - 4), 'B', fill=(255, 255, 255, 255), font=av_font)
    
    # Name 'Brandon >'
    name_font = get_font_test(24)
    nbox = draw.textbbox((0, 0), 'Brandon', font=name_font)
    ntw, nth = nbox[2] - nbox[0], nbox[3] - nbox[1]
    total_name_w = ntw + 16
    nx = (card_w - total_name_w) // 2
    ny = av_y + av_d + 6
    draw.text((nx, ny), 'Brandon', fill=(0, 0, 0, 255), font=name_font)
    sx = nx + ntw + 6
    sy = ny + 5
    draw.line([(sx, sy), (sx + 5, sy + 6), (sx, sy + 12)], fill=(142, 142, 147, 255), width=2, joint='round')
    
    # Video camera outline icon
    vx0, vy0 = card_w - 95, 52
    vw, vh = 36, 38
    draw.rounded_rectangle([vx0, vy0, vx0 + vw, vy0 + vh], radius=9, outline=(0, 122, 255, 255), width=4)
    tw = 15
    draw.line([
        (vx0 + vw + 2, vy0 + 9),
        (vx0 + vw + 2 + tw, vy0 + 3),
        (vx0 + vw + 2 + tw, vy0 + vh - 3),
        (vx0 + vw + 2, vy0 + vh - 9),
        (vx0 + vw + 2, vy0 + 9)
    ], fill=(0, 122, 255, 255), width=4, joint='round')
    
    curr_y = hdr_h + 16
    for b in bubbles_info:
        side = b['side']
        bw = b['bw']
        bh = b['bh']
        is_out = (side == 2)
        if is_out:
            bx = card_w - 32 - bw
            fill_col = (0, 138, 254, 255)
            text_col = (255, 255, 255, 255)
            tx = bx + 24
        else:
            bx = 32
            fill_col = (232, 232, 232, 255)
            text_col = (0, 0, 0, 255)
            tx = bx + 34
            
        mask = render_imessage_bubble_mask(bw, bh, is_outgoing=is_out)
        b_surf = Image.new('RGBA', (bw, bh), fill_col)
        b_surf.putalpha(mask)
        card.alpha_composite(b_surf, (bx, curr_y))
        
        ty = curr_y + (bh - b['th']) // 2 - 4
        draw.text((tx, ty), b['text'], fill=text_col, font=font)
        curr_y += bh + gap
        
    bg = Image.new('RGB', (1080, 1920), (0, 255, 0))
    bg.paste(card, (136, 350))
    os.makedirs('data', exist_ok=True)
    bg.crop((130, 340, 950, 990)).save('data/new_reproduction.png')
    print('Successfully generated data/new_reproduction.png')

if __name__ == '__main__':
    run()

import unittest
import io
import re
from PIL import Image
import renderer

class TestHeaderNameSize(unittest.TestCase):
    def test_app_html_slider_attributes(self):
        with open('templates/app.html', 'r', encoding='utf-8') as f:
            html = f.read()

        # Check slider exists with correct id, data-settings-key, and refreshPreview
        pattern = r'<input[^>]+id=["\']slider-name-size["\'][^>]*>'
        match = re.search(pattern, html)
        self.assertIsNotNone(match, "Slider with id='slider-name-size' not found in app.html")
        tag = match.group(0)
        self.assertIn('refreshPreview()', tag, "slider-name-size oninput must call refreshPreview()")
        self.assertIn('data-settings-key="header_name_size"', tag, "slider-name-size must have data-settings-key='header_name_size'")

        # Check getPreviewBody reads header_name_size
        self.assertIn("slider-name-size", html)
        self.assertIn("header_name_size", html)

    def test_render_chat_frame_name_size_scaling(self):
        # Size 28 vs 42 vs 50
        def get_name_bbox(size):
            img = renderer.render_chat_frame(
                [],
                0,
                contact_name="Amanda",
                style='ios',
                theme='dark',
                width=1080,
                height=1920,
                header_name_size=size
            )
            card_x = (1080 - 808) // 2
            ys = []
            xs = []
            for y in range(440, 530):
                for x in range(card_x, card_x + 808):
                    r, g, b, a = img.getpixel((x, y))
                    if a > 200 and r > 240 and g > 240 and b > 240:
                        ys.append(y)
                        xs.append(x)
            return (max(ys) - min(ys) + 1, max(xs) - min(xs) + 1) if ys else (0, 0)

        h28, w28 = get_name_bbox(28)
        h42, w42 = get_name_bbox(42)
        h50, w50 = get_name_bbox(50)

        self.assertGreater(h42, h28, f"Height at 42 ({h42}) should be > at 28 ({h28})")
        self.assertGreater(w42, w28, f"Width at 42 ({w42}) should be > at 28 ({w28})")
        self.assertGreater(h50, h42, f"Height at 50 ({h50}) should be > at 42 ({h42})")
        self.assertGreater(w50, w42, f"Width at 50 ({w50}) should be > at 42 ({w42})")

    def test_render_preview_image_with_name_size(self):
        body_default = {
            'script': 'Amanda\n1:Amanda> Hello\n2:Me> Hi',
            'style': 'ios',
            'theme': 'dark',
            'header_name_size': 42
        }
        img_bytes, total_pages = renderer.render_preview_image(body_default)
        self.assertGreater(len(img_bytes), 1000)
        self.assertEqual(total_pages, 1)

        # Test WhatsApp style
        body_wa = {
            'script': 'Amanda\n1:Amanda> Hello WhatsApp\n2:Me> Hi',
            'style': 'whatsapp',
            'theme': 'dark',
            'name_font_size': 42
        }
        wa_bytes, wa_pages = renderer.render_preview_image(body_wa)
        self.assertGreater(len(wa_bytes), 1000)
        self.assertEqual(wa_pages, 1)

if __name__ == '__main__':
    unittest.main()

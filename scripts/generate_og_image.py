"""
Generate Open Graph image for Qunex Trade
Creates 1200x630px image for social media previews
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_og_image():
    """Create Open Graph preview image"""

    # Open Graph recommended size
    width, height = 1200, 630

    # Create image with dark background
    background_color = (10, 14, 39)  # #0a0e27
    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)

    # Add gradient overlay effect
    for i in range(height):
        alpha = int(30 * (i / height))
        gradient_color = (0, 217, 255, alpha)  # cyan fade
        # Note: RGB mode doesn't support alpha, so we'll skip this for simplicity

    # Draw large "Q" logo
    logo_size = 200
    logo_x = 100
    logo_y = (height - logo_size) // 2

    # Draw rounded rectangle for logo background
    draw.rounded_rectangle(
        [(logo_x, logo_y), (logo_x + logo_size, logo_y + logo_size)],
        radius=40,
        fill=(19, 24, 41),  # slightly lighter than background
    )

    # Draw 'Q' letter
    try:
        font_logo = ImageFont.truetype("arial.ttf", 120)
    except:
        font_logo = ImageFont.load_default()

    text_color = (0, 217, 255)  # cyan
    draw.text((logo_x + 50, logo_y + 35), "Q", font=font_logo, fill=text_color)

    # Draw text content
    try:
        font_title = ImageFont.truetype("arial.ttf", 72)
        font_subtitle = ImageFont.truetype("arial.ttf", 36)
        font_features = ImageFont.truetype("arial.ttf", 28)
    except:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_features = ImageFont.load_default()

    text_x = 350

    # Title
    title = "Qunex Trade"
    draw.text((text_x, 120), title, font=font_title, fill=(255, 255, 255))

    # Subtitle
    subtitle = "Professional Trading Intelligence Platform"
    draw.text((text_x, 210), subtitle, font=font_subtitle, fill=(139, 146, 176))

    # Features
    features = [
        "Real-Time Market Data",
        "AI-Powered News Analysis",
        "Advanced Stock Screener",
        "Economic Calendar",
    ]

    feature_y = 300
    for feature in features:
        # Bullet point
        draw.ellipse([(text_x, feature_y + 10), (text_x + 8, feature_y + 18)], fill=(0, 217, 255))
        # Feature text
        draw.text((text_x + 20, feature_y), feature, font=font_features, fill=(200, 200, 200))
        feature_y += 50

    # Bottom branding
    try:
        font_small = ImageFont.truetype("arial.ttf", 24)
    except:
        font_small = ImageFont.load_default()

    draw.text((text_x, 550), "qunextrade.com", font=font_small, fill=(0, 217, 255))

    # Save the image
    output_path = "web/static/og-image.png"
    img.save(output_path, "PNG")
    print(f"[OK] Created: {output_path} (1200x630)")
    print(f"Location: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    print("Generating Open Graph image...")
    print("=" * 50)
    create_og_image()
    print("=" * 50)
    print("[SUCCESS] Open Graph image generated!")

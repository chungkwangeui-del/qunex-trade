"""
Generate favicon files for Qunex Trade
Creates PNG favicon files in multiple sizes
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_favicon(size, output_path):
    """Create a favicon with 'Q' letter and gradient background"""

    # Create image with transparency
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background (dark blue)
    background_color = (10, 14, 39, 255)  # #0a0e27
    corner_radius = size // 5
    draw.rounded_rectangle(
        [(0, 0), (size, size)],
        radius=corner_radius,
        fill=background_color
    )

    # Add gradient effect by drawing multiple rectangles with varying opacity
    gradient_start = (0, 217, 255, 100)  # cyan with transparency
    gradient_end = (124, 58, 237, 100)   # purple with transparency

    # Draw 'Q' letter in white/cyan
    text_color = (0, 217, 255, 255)  # cyan #00d9ff

    # Try to use a nice font, fallback to default if not available
    try:
        # Try to load a bold font
        font_size = int(size * 0.6)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        try:
            font = ImageFont.truetype("Arial Bold.ttf", int(size * 0.6))
        except:
            # Use default
            font = ImageFont.load_default()

    # Draw the 'Q' letter centered
    text = "Q"

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]

    # Draw text with slight shadow for depth
    shadow_color = (0, 0, 0, 128)
    draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=text_color)

    # Save the image
    img.save(output_path, 'PNG')
    print(f"[OK] Created: {output_path} ({size}x{size})")

def main():
    """Generate all required favicon sizes"""

    # Create output directory
    output_dir = "web/static"
    os.makedirs(output_dir, exist_ok=True)

    print("Generating Qunex Trade favicons...")
    print("=" * 50)

    # Generate all required sizes
    sizes = {
        'favicon-16x16.png': 16,
        'favicon-32x32.png': 32,
        'favicon-192x192.png': 192,
        'favicon-512x512.png': 512,
        'apple-touch-icon.png': 180
    }

    for filename, size in sizes.items():
        output_path = os.path.join(output_dir, filename)
        create_favicon(size, output_path)

    print("=" * 50)
    print("[SUCCESS] All favicon files generated successfully!")
    print(f"Location: {os.path.abspath(output_dir)}")
    print("\nNext steps:")
    print("1. Commit and push these files to GitHub")
    print("2. Wait for Render to deploy (~5 minutes)")
    print("3. Clear browser cache and reload to see new favicon")

if __name__ == '__main__':
    main()

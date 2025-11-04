# Favicon Files Needed

To complete the SEO setup, please add these favicon files to `/web/static/`:

## Required Files:

1. **favicon-16x16.png** (16x16 pixels)
2. **favicon-32x32.png** (32x32 pixels)
3. **favicon-192x192.png** (192x192 pixels) - For Android
4. **favicon-512x512.png** (512x512 pixels) - For Android
5. **apple-touch-icon.png** (180x180 pixels) - For iOS
6. **og-image.png** (1200x630 pixels) - For Open Graph social sharing

## Design Specifications:

- **Logo**: "Q" letter on gradient background (cyan #00d9ff to purple #7c3aed)
- **Background**: Dark blue #0a0e27 or transparent
- **Style**: Modern, professional, clean

## How to Create:

### Option 1: Use Canva (Free)
1. Go to Canva.com
2. Create custom size canvas for each dimension
3. Add text "Q" with gradient fill
4. Add rounded square background
5. Download as PNG

### Option 2: Use Figma (Free)
1. Create frames with specified dimensions
2. Design logo with gradient
3. Export as PNG

### Option 3: Use Online Favicon Generator
1. Upload the existing `favicon.svg` to https://realfavicongenerator.net/
2. Generate all sizes automatically
3. Download and extract to `/web/static/`

## Current Status:

- [x] SEO meta tags added
- [x] site.webmanifest created
- [ ] PNG favicon files (need to be created)
- [ ] Open Graph image (need to be created)

## Note:

The website will still work with just `favicon.svg`, but having all PNG versions ensures:
- Better browser compatibility
- Proper display on mobile devices (iOS, Android)
- Beautiful social media previews when shared
- Professional appearance in Google search results

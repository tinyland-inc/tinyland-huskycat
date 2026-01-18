# HuskyCat Icon Assets

## Source Files

- `huskycat.svg` - Full color vector icon (512x512 viewBox)
- `huskycat-symbolic.svg` - Symbolic/monochrome icon for system tray (16x16)

## Generating Raster Formats

### From SVG to PNG (multiple sizes)

Using Inkscape (recommended):
```bash
for size in 16 32 48 64 128 256 512; do
    inkscape huskycat.svg -w $size -h $size -o huskycat-${size}.png
done
```

Using ImageMagick:
```bash
for size in 16 32 48 64 128 256 512; do
    convert -background none huskycat.svg -resize ${size}x${size} huskycat-${size}.png
done
```

Using rsvg-convert (librsvg):
```bash
for size in 16 32 48 64 128 256 512; do
    rsvg-convert huskycat.svg -w $size -h $size -o huskycat-${size}.png
done
```

### macOS .icns Bundle

Requires iconutil (built into macOS):
```bash
# Create iconset directory
mkdir huskycat.iconset

# Generate all required sizes
for size in 16 32 128 256 512; do
    sips -z $size $size huskycat-512.png --out huskycat.iconset/icon_${size}x${size}.png
    sips -z $((size*2)) $((size*2)) huskycat-512.png --out huskycat.iconset/icon_${size}x${size}@2x.png
done

# Create .icns
iconutil -c icns huskycat.iconset -o huskycat.icns

# Cleanup
rm -rf huskycat.iconset
```

### Windows .ico

Using ImageMagick:
```bash
convert huskycat.svg \
    \( -clone 0 -resize 16x16 \) \
    \( -clone 0 -resize 32x32 \) \
    \( -clone 0 -resize 48x48 \) \
    \( -clone 0 -resize 256x256 \) \
    -delete 0 huskycat.ico
```

## CI/CD Generation

The GitLab CI pipeline automatically generates raster icons during the build process.
See `.gitlab/ci/assets.yml` for the automated icon generation job.

## Icon Design

The HuskyCat logo features:
- Purple/indigo gradient background (brand colors: #6366f1 to #8b5cf6)
- White code brackets { } representing code/development
- Green checkmark representing validation success
- Subtle cat ear silhouettes at the top

The symbolic icon is a simplified monochrome version suitable for:
- System tray indicators
- Taskbar icons
- Monochrome UI contexts

#!/usr/bin/env python3
import os
import sys
import gi
gi.require_version('Rsvg', '2.0')
import cairo
from gi.repository import Rsvg

def render_icon(svg_path, output_path, size):
    if not os.path.exists(svg_path):
        print(f"Error: SVG file not found at {svg_path}")
        return False

    handle = Rsvg.Handle.new_from_file(svg_path)
    
    # Create main surface with transparency (ARGB32)
    surface = cairo.ImageSurface(cairo.Format.ARGB32, size, size)
    context = cairo.Context(surface)
    
    # Scale SVG to fit the target size
    dimensions = handle.get_dimensions()
    scale_x = size / dimensions.width
    scale_y = size / dimensions.height
    scale = min(scale_x, scale_y)
    
    # Center the icon if aspect ratio differs
    translate_x = (size - (dimensions.width * scale)) / 2
    translate_y = (size - (dimensions.height * scale)) / 2
    
    context.translate(translate_x, translate_y)
    context.scale(scale, scale)
    
    # Render
    handle.render_cairo(context)
    
    # Save to PNG
    surface.write_to_png(output_path)
    print(f"Generated {size}x{size} icon at {output_path}")
    return True

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    svg_path = os.path.join(base_dir, "icons/hicolor/scalable/apps/io.github.gkdevelopers.GKHealter.svg")
    
    sizes = [64, 128, 256]
    
    for size in sizes:
        out_dir = os.path.join(base_dir, f"icons/hicolor/{size}x{size}/apps")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "io.github.gkdevelopers.GKHealter.png")
        
        render_icon(svg_path, out_path, size)

if __name__ == "__main__":
    main()

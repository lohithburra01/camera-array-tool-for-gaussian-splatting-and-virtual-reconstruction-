# Camera Array & Batch Renderer

A Blender addon for creating camera arrays around objects and batch rendering for 3D reconstruction workflows like Gaussian splatting.
<img width="1289" height="994" alt="image" src="https://github.com/user-attachments/assets/85d1c34f-2275-4bf6-a553-439dfe2cddb5" />

## Overview

This addon automates the tedious process of manually placing dozens of cameras around objects for photogrammetry and 3D reconstruction. Instead of spending hours positioning cameras, you can generate mathematically precise arrays in seconds.

## Features

### Camera Array Generation
- **Multiple array types**: Sphere, hemisphere, cylinder, grid, and mesh-face placement
- **Smart positioning**: Automatically calculates optimal distance based on object bounds
- **Elevation control**: Set minimum/maximum angles to avoid problematic viewpoints
- **Height levels**: Distribute cameras across multiple vertical layers

<img width="326" height="805" alt="image" src="https://github.com/user-attachments/assets/9d739a94-8af8-4422-be06-64721467d5f7" />


### Batch Rendering
- **Automated rendering**: Render all cameras with proper file naming
- **Resume capability**: Skip existing files to resume interrupted renders
- **Format flexibility**: PNG, JPEG, TIFF, or OpenEXR output
- **Resolution scaling**: Render at different resolutions without changing scene settings

## Installation

1. Download the addon file
2. In Blender: Edit > Preferences > Add-ons > Install
3. Select the downloaded file and enable the addon
4. Find the panel in 3D Viewport > N-Panel > "Camera Array"

## Usage

### Creating a Camera Array

1. **Select target object**: Choose the mesh object you want to capture
2. **Choose array type**: 
   - **Sphere**: Full 360° coverage around object
   - **Hemisphere**: Upper half only (good for ground-based objects)
   - **Cylinder**: Ring-based arrangement at different heights
   - **Grid**: Planar grid of cameras at fixed distance
   - **From Mesh**: Places cameras on face centers of selected mesh
3. **Configure settings**:
   - **Camera Count**: Number of cameras to generate (3-100)
   - **Distance Factor**: Multiplier of object size for camera distance
   - **Height Levels**: Vertical distribution of cameras
   - **Elevation Range**: Min/max angles for sphere arrays
4. **Click "Create Camera Array"**

### Batch Rendering

1. **Set output directory**: Choose where to save rendered images
2. **Configure render settings**:
   - **Image format**: PNG, JPEG, TIFF, or OpenEXR
   - **Resolution scale**: Render at percentage of scene resolution
   - **Skip existing**: Resume interrupted renders
   - **Hide target**: Optionally hide object during rendering
3. **Click "Batch Render Array"**

## Technical Details

### Array Algorithms

**Sphere Array**: Distributes cameras using spherical coordinates with even azimuthal spacing across multiple elevation levels.

**Hemisphere Array**: Same as sphere but constrains elevation to 0-90 degrees.

**Cylinder Array**: Creates rings of cameras at different heights, useful for tall objects.

**Grid Array**: Places cameras in a planar grid pattern, all facing the object center.

**Mesh-Face Array**: Positions cameras at each face center of a mesh, pointing toward face centers.

### Distance Calculation
Automatically analyzes object bounding box to determine optimal camera distance:
```
camera_distance = max(object_dimensions) * distance_factor
```

### File Organization
Creates organized directory structure:
```
output_directory/
├── ArrayCam_001.png
├── ArrayCam_002.png
└── ...
```

## Use Cases

- **Gaussian Splatting**: Generate training images for 3DGS reconstruction
- **Photogrammetry**: Create systematic camera coverage for mesh reconstruction
- **Product Visualization**: Render objects from multiple angles
- **Architectural Visualization**: Document buildings from all sides
- **Animation References**: Generate turntable-style reference images

## Requirements

- Blender 4.0+
- Target object must be a mesh

## Tips

- For Gaussian splatting, use **Sphere** or **Hemisphere** arrays with 24-48 cameras
- Increase **Distance Factor** for wider shots, decrease for detail captures  
- Use **Height Levels** to ensure good vertical coverage
- **Skip Existing** lets you add more cameras and re-render without duplicating work
- **Hide Target** useful when you only want the background/environment

## Workflow Integration

This addon integrates well with:
- **COLMAP**: Use rendered images directly for 3D reconstruction
- **Gaussian Splatting training**: Provides systematic camera coverage
- **Batch processing pipelines**: Automated rendering reduces manual work

## Technical Implementation

Built using modern Blender addon patterns:
- Mathematical positioning algorithms for precise camera placement
- Efficient batch processing with progress feedback  
- Clean UI with collapsible sections
- Error handling and validation
- Memory-efficient rendering loop

## License

MIT License - feel free to modify and distribute.

## Author

Built by Lohith Burra - Technical Artist specializing in pipeline automation for 3D workflows.

# COLMAP Structure-from-Motion Docker Setup

This document provides instructions for setting up and running the COLMAP SfM pipeline in Docker with Jupyter notebook interface.

## Prerequisites

- Docker installed
- At least 4GB system RAM
- Optional: NVIDIA GPU for faster processing

## Quick Start

1. **Place video files or images** in the `data/` directory:
   ```bash
   mkdir -p data
   cp your_video.mp4 data/
   # OR place image sequence in data/images/
   ```

2. **Build and start the container**:
   ```bash
   docker-compose up --build
   ```

3. **Access Jupyter Lab** at: http://localhost:8888

4. **Open the demo notebook**: `notebooks/COLMAP_SLAM_Demo.ipynb`

5. **Results** will be saved to `output/` directory on your host machine

## Directory Structure

```
hls/
├── data/             # Input videos/images (mount point)
├── output/           # Processing results (mount point)
├── temp/             # Temporary processing files
├── notebooks/        # Jupyter notebooks
├── modules/          # Other project modules
├── Dockerfile        # Docker image definition
├── docker-compose.yml
└── requirements.txt
```

## Usage Instructions

### Processing a Video

1. **Place your video** in the `data/` directory
   - Supported formats: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm

2. **Configure parameters** in the notebook:
   ```python
   CONFIG = {
       'frame_skip': 10,               # Extract every 10th frame
       'max_frames': 100,              # Process max 100 frames
       'resize_factor': 0.5,           # Resize frames to 50%
       'feature_type': 'SIFT',         # SIFT features
       'matcher_type': 'exhaustive',   # Exhaustive matching
   }
   ```

3. **Run the notebook cells** in order:
   - Frame extraction from video
   - COLMAP reconstruction
   - Results visualization and export

### Processing Image Sequences

1. **Place images** in `data/images/` directory
2. **Skip frame extraction** step in notebook
3. **Run COLMAP reconstruction** directly on image directory

### Output Structure

Each processed video/image sequence creates a timestamped output directory:
```
output/
└── video_name_20231201_143022/
    ├── frames/              # Extracted frames (if from video)
    ├── reconstruction/      # COLMAP results
    │   ├── 0/              # Reconstruction model
    │   ├── database.db     # COLMAP database
    │   ├── points.ply      # Point cloud
    │   └── trajectory.txt  # Camera poses (TUM format)
    └── visualization/       # Plots and visualizations
        ├── camera_trajectory.png
        └── reconstruction_stats.png
```

## Advanced Configuration

### Feature Types

**SIFT Features** (Recommended):
- Classical, reliable features
- Good for most scenarios
- CPU/GPU compatible

### Matching Types

**Exhaustive Matching**:
- Matches every image with every other image
- Most accurate but slower
- Good for unordered image sets

**Sequential Matching**:
- Matches consecutive images
- Faster for video sequences
- Good for ordered video frames

### Performance Tuning

**For faster processing:**
```python
CONFIG = {
    'frame_skip': 20,           # Skip more frames
    'max_frames': 50,           # Process fewer frames
    'resize_factor': 0.25,      # Smaller images
    'matcher_type': 'sequential',
}
```

**For better quality:**
```python
CONFIG = {
    'frame_skip': 5,            # Use more frames
    'max_frames': 200,          # Process more frames
    'resize_factor': 0.8,       # Larger images
    'matcher_type': 'exhaustive',
}
```

## Troubleshooting

### Common Issues

**Container won't start:**
- Check Docker installation
- Verify sufficient disk space (build requires ~3GB)
- Check port 8888 is not in use

**Reconstruction fails:**
- Check video quality (avoid pure rotation, need translation)
- Try different frame skip values
- Ensure sufficient image overlap
- Check image sharpness (avoid blurry images)

**Memory issues:**
- Reduce `max_frames` parameter
- Increase Docker memory limits
- Use smaller input images (`resize_factor`)

### Logs and Debugging

**View container logs:**
```bash
docker-compose logs colmap-sfm
```

**Access container shell:**
```bash
docker-compose exec colmap-sfm bash
```

**Test COLMAP installation:**
```bash
docker-compose exec colmap-sfm colmap --help
```

## Alternative Usage

### Command Line Processing

Run COLMAP directly without Jupyter:
```bash
docker-compose exec colmap-sfm ./test.sh
```

### Native Installation

For running without Docker:
```bash
# Install dependencies
sudo apt-get install colmap
pip install -r requirements.txt

# Run notebook
jupyter lab notebooks/COLMAP_SLAM_Demo.ipynb
```

## File Formats

### Input
- **Videos**: MP4, AVI, MOV, MKV, WMV, FLV, WebM
- **Image sequences**: JPG, PNG (place in `data/images/` directory)

### Output
- **COLMAP files**: cameras.bin, images.bin, points3D.bin (in reconstruction/0/)
- **Trajectory**: TUM format trajectory.txt (timestamp tx ty tz qx qy qz qw)
- **Point cloud**: PLY format points.ply
- **Database**: SQLite database.db
- **Visualizations**: PNG plots

## Performance Expectations

**Typical processing times** (depends on hardware):
- Frame extraction: 30 seconds - 2 minutes
- Feature extraction: 1-5 minutes for 100 frames
- Feature matching: 1-10 minutes depending on method
- Reconstruction: 1-5 minutes
- Total pipeline: 5-20 minutes per video

**Resource usage:**
- System RAM: 2-8GB during processing
- Disk space: ~500MB per processed video
- CPU: Multi-core recommended

## Camera Model Support

COLMAP automatically detects camera parameters from:
- **EXIF data** in images
- **Manual configuration** in notebook
- **Automatic calibration** during reconstruction

Supported camera models:
- SIMPLE_PINHOLE
- PINHOLE
- SIMPLE_RADIAL
- RADIAL
- OPENCV
- FULL_OPENCV

## Quality Tips

**For best reconstruction quality:**
1. **Good camera motion**: Combine translation and rotation
2. **Sufficient overlap**: 60-80% overlap between consecutive images
3. **Sharp images**: Avoid motion blur
4. **Textured scenes**: Avoid featureless walls or surfaces
5. **Consistent lighting**: Avoid extreme lighting changes
6. **Stable camera**: Reduce camera shake

## Next Steps

After processing:
1. **Analyze results** in the output visualization plots
2. **Import point cloud** into 3D software (MeshLab, CloudCompare, Blender)
3. **Use trajectory data** for camera path analysis
4. **Export to other formats** using COLMAP tools
5. **Experiment with parameters** for different scenes
# COLMAP-SLAM Docker Setup

This document provides instructions for setting up and running the COLMAP-SLAM pipeline in Docker with Jupyter notebook interface.

## Prerequisites

- Docker with GPU support (nvidia-docker2)
- NVIDIA drivers installed on host
- At least 8GB GPU memory recommended
- 16GB+ system RAM recommended

## Quick Start

1. **Place video files** in the `videos/` directory:
   ```bash
   mkdir -p videos
   cp your_video.mp4 videos/
   ```

2. **Build and start the container**:
   ```bash
   docker-compose up --build
   ```

3. **Access Jupyter Lab** at: http://localhost:8888

4. **Open the demo notebook**: `notebooks/COLMAP_SLAM_Demo.ipynb`

5. **Results** will be saved to `outputs/` directory on your host machine

## Directory Structure

```
hls/
├── videos/           # Input videos (mount point)
├── outputs/          # Processing results (mount point)
├── notebooks/        # Jupyter notebooks
├── modules/
│   └── COLMAP_SLAM/  # SLAM pipeline code
├── Dockerfile        # Docker image definition
├── docker-compose.yml
└── requirements.txt
```

## Usage Instructions

### Processing a Video

1. **Place your video** in the `videos/` directory
   - Supported formats: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm

2. **Configure parameters** in the notebook:
   ```python
   CONFIG = {
       'frame_skip': 5,                    # Extract every 5th frame
       'max_frames': 100,                  # Process max 100 frames
       'init_frames': 30,                  # Frames for initialization
       'optical_flow_threshold': 0.05,     # Keyframe selection
       'extractor': enums.Extractors.SuperPoint,
       'matcher': enums.Matchers.SuperGlue,
   }
   ```

3. **Run the notebook cells** in order:
   - Frame extraction from video
   - SLAM reconstruction
   - Results visualization and export

### Output Structure

Each processed video creates a timestamped output directory:
```
outputs/
└── video_name_20231201_143022/
    ├── frames/              # Extracted frames
    ├── reconstruction/      # SLAM results
    │   ├── colmap/         # COLMAP binary files
    │   ├── estimation.txt  # Camera trajectory (TUM format)
    │   └── reconstruction_summary.txt
    └── visualization/       # Plots and visualizations
        ├── camera_trajectory.png
        └── reconstruction_stats.png
```

## Advanced Configuration

### Feature Extractors and Matchers

**SuperPoint + SuperGlue** (Recommended for quality):
- Neural network-based features
- More robust but slower
- Requires GPU

**ORB + Hamming** (Faster alternative):
- Classical features
- Faster processing
- Works on CPU

### Performance Tuning

**For faster processing:**
```python
CONFIG = {
    'frame_skip': 10,           # Skip more frames
    'max_frames': 50,           # Process fewer frames
    'extractor': enums.Extractors.ORB,
    'matcher': enums.Matchers.OrbHamming,
}
```

**For better quality:**
```python
CONFIG = {
    'frame_skip': 2,            # Use more frames
    'max_frames': 200,          # Process more frames
    'init_frames': 50,          # More initialization frames
    'extractor': enums.Extractors.SuperPoint,
    'matcher': enums.Matchers.SuperGlue,
}
```

## Troubleshooting

### Common Issues

**Container won't start:**
- Check Docker and nvidia-docker2 installation
- Verify GPU drivers: `nvidia-smi`
- Check disk space (Docker build requires ~5GB)

**CUDA/GPU errors:**
- Fallback to CPU: Set `CUDA_VISIBLE_DEVICES=""`
- Use ORB features instead of SuperPoint

**Memory issues:**
- Reduce `max_frames` parameter
- Increase Docker memory limits
- Use smaller input videos

**Reconstruction fails:**
- Check video quality (avoid pure rotation, need translation)
- Reduce `optical_flow_threshold` for more keyframes
- Increase `init_frames` for better initialization

### Logs and Debugging

**View container logs:**
```bash
docker-compose logs colmap-slam
```

**Access container shell:**
```bash
docker-compose exec colmap-slam bash
```

**Check GPU usage:**
```bash
nvidia-smi
```

## Alternative Usage

### GUI Mode (Linux with X11)

For the original GUI application:
```bash
# Enable X11 forwarding
xhost +local:docker

# Run GUI version
docker-compose --profile gui up
```

### Command Line Processing

Run SLAM directly without Jupyter:
```bash
docker-compose exec colmap-slam python COLMAP_SLAM/pipeline.py
```

## File Formats

### Input
- **Videos**: MP4, AVI, MOV, MKV, WMV, FLV, WebM
- **Image sequences**: JPG, PNG (place in `data/` directory)

### Output
- **COLMAP files**: cameras.bin, images.bin, points3D.bin
- **Trajectory**: TUM format (.txt)
- **Point cloud**: PLY format
- **Visualizations**: PNG plots

## Performance Expectations

**Typical processing times** (depends on hardware):
- Frame extraction: 1-2 minutes for 100 frames
- SLAM reconstruction: 5-15 minutes for 100 frames
- Total pipeline: 10-20 minutes per video

**Resource usage:**
- GPU memory: 2-4GB (SuperPoint/SuperGlue)
- System RAM: 4-8GB during processing
- Disk space: ~1GB per processed video

## Next Steps

After processing:
1. **Analyze results** in the output visualization plots
2. **Import COLMAP files** into other software (MeshLab, CloudCompare)
3. **Use trajectory data** for further analysis or applications
4. **Experiment with parameters** for different video types
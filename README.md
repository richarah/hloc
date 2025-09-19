# HLS Monorepo - Internal use only

Monorepo for internal projects of Haydon Laastad Systems (name is tentative, order may be reversed, it came to me in a dream)

Work in progress. Major changes may occur at any time.

## What's this?

This repository contains computer vision and 3D reconstruction tools with three main focus areas:
- **Structure-from-Motion (SfM)** - Camera pose estimation and 3D reconstruction from images/video
- **Point Cloud Processing** - Real-time rendering and visualization of 3D data
- **Global SfM** - Alternative reconstruction approaches for improved performance

## Quick Start

### Docker Setup (Recommended)

The easiest way to run the project is using Docker:

```bash
# Build and start the container with Jupyter interface
docker-compose up --build

# Access Jupyter Lab at http://localhost:8888
# Open notebooks/COLMAP_SLAM_Demo.ipynb for guided demo
```

### Native Setup

For running outside Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Run Jupyter notebook
jupyter lab

# Open notebooks/COLMAP_SLAM_Demo.ipynb
```

## A note on nested submodules

git submodule init
git submodule update --init --recursive --remote
git submodule sync

### Active Components

- **COLMAP SfM Pipeline** - Structure-from-Motion using COLMAP for video/image sequences
  - Camera pose estimation
  - 3D point cloud reconstruction  
  - Trajectory export in TUM format
  - Interactive 3D visualization

- **Skye** - Framework for real-time point cloud rendering (C++)
  - GPU-accelerated point cloud visualization
  - Real-time rendering capabilities

- **glomap** - Global Structure-from-Motion alternative to COLMAP (C++)
  - Faster reconstruction in benchmarks
  - Global optimization approach

- **voxelprojection** - Pixel to voxel projection utilities

### Usage

#### COLMAP Structure-from-Motion

Process videos or image sequences to generate 3D reconstructions:

```bash
# Using Docker (recommended)
docker-compose up --build

# Then open notebooks/COLMAP_SLAM_Demo.ipynb in Jupyter
```

The pipeline supports:
- **Input formats**: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm videos or image directories
- **Output formats**: COLMAP binary files, PLY point clouds, TUM trajectory format
- **Visualization**: 2D trajectory plots and interactive 3D point cloud viewer

#### Key Features

- **Automatic camera calibration** from image EXIF data or manual configuration
- **Feature extraction and matching** using SIFT with COLMAP
- **Incremental 3D reconstruction** with bundle adjustment
- **Quality metrics** and reconstruction statistics
- **Export capabilities** to various formats (PLY, TUM, COLMAP binary)

## Directory Structure

```
├── data/           # Input data (images, videos)
├── output/         # Reconstruction results
├── temp/           # Temporary processing files
├── notebooks/      # Jupyter demo notebooks
├── modules/        # Core modules
│   ├── Skye/       # Point cloud rendering (C++)
│   ├── glomap/     # Global SfM (C++)
│   └── voxelprojection/ # Voxel utilities
├── Dockerfile      # Container setup
├── docker-compose.yml
└── requirements.txt
```

## Dependencies

**Core Requirements:**
- COLMAP (for Structure-from-Motion)
- Python 3.8+ with numpy, opencv, matplotlib
- pycolmap (Python COLMAP bindings)
- Open3D (3D visualization)
- Jupyter Lab (for interactive demos)

**Optional:**
- CUDA (for GPU acceleration)
- CMake (for building C++ modules)

## Development

### Building C++ Modules

```bash
# glomap
cd modules/glomap
mkdir build && cd build
cmake .. -DTESTS_ENABLED=ON
make -j$(nproc)

# Skye uses Visual Studio project files (Windows)
# See modules/Skye/Skye.sln
```

### Testing

The project uses Jupyter notebooks for interactive testing and development:

```bash
# Run the main demo
jupyter lab notebooks/COLMAP_SLAM_Demo.ipynb
```

## Roadmap

- ✅ COLMAP Structure-from-Motion pipeline
- ✅ Docker containerization
- ✅ Interactive Jupyter demos
- 🔄 Real-time SLAM capabilities
- 🔄 Integration with Skye for visualization
- 🔄 Global SfM evaluation with glomap
- 🔄 Multi-camera support
- 🔄 360-degree camera support

## Notes

- COLMAP does not natively support 360 cameras - adjustments may be needed later
- For real-time applications, consider parameter tuning for speed vs. quality trade-offs
- GPU acceleration recommended for processing large datasets
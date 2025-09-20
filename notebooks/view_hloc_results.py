# View HLoC Results
# This script loads and visualizes the outputs from HLoC camera pose estimation

# Setup and imports
import os
import numpy as np
from pathlib import Path
import json

# Add hloc module to path
import sys
sys.path.append('../modules/hloc')

from hloc import visualization
from hloc.utils import viz_3d
import pycolmap

print("Setup complete!")

# Configuration
OUTPUT_DIR = Path("../outputs/hloc_poses")
SFM_DIR = OUTPUT_DIR / "sfm"
POSES_DIR = OUTPUT_DIR / "poses"
IMAGES_DIR = Path("../temp/hloc_processing/images")

print(f"Output directory: {OUTPUT_DIR}")
print(f"SfM directory: {SFM_DIR}")
print(f"Images directory: {IMAGES_DIR}")
print(f"Checking file status...")
print(f"  SfM model: {'✓' if SFM_DIR.exists() else '✗'} {SFM_DIR}")
print(f"  Poses: {'✓' if POSES_DIR.exists() else '✗'} {POSES_DIR}")

# Load the reconstruction
try:
    model = pycolmap.Reconstruction(SFM_DIR)
    print(f"✓ Loaded reconstruction from {SFM_DIR}")
    print(f"  Number of registered images: {len(model.images)}")
    print(f"  Number of 3D points: {len(model.points3D)}")
    print(f"  Number of cameras: {len(model.cameras)}")
    
except Exception as e:
    print(f"❌ Failed to load reconstruction: {e}")
    model = None

# 3D Reconstruction Visualization
if model is not None:
    print("Creating 3D reconstruction visualization...")
    
    # Create the 3D figure
    fig = viz_3d.init_figure()
    
    # Plot the reconstruction
    viz_3d.plot_reconstruction(
        fig, model, color="rgba(255,0,0,0.5)", name="reconstruction", points_rgb=True
    )
    
    fig.show()
else:
    print("No reconstruction model available for visualization")

# Camera Trajectory Visualization
if model is not None:
    print("Creating camera trajectory visualization...")
    
    # Extract camera positions
    camera_positions = []
    image_names = []
    
    for image_id, image in model.images.items():
        # Get camera pose (convert to world coordinates)
        cam_from_world = image.cam_from_world
        world_from_cam = cam_from_world.inverse()
        
        # Extract translation (camera position in world coordinates)
        position = world_from_cam.translation
        camera_positions.append(position)
        image_names.append(image.name)
    
    camera_positions = np.array(camera_positions)
    
    print(f"Extracted {len(camera_positions)} camera positions")
    
    # Create trajectory figure
    fig_traj = viz_3d.init_figure()
    
    # Plot camera positions as points
    viz_3d.plot_points(fig_traj, camera_positions, color="blue", ps=8, name="camera_positions")
    
    # Add trajectory line using plotly
    import plotly.graph_objects as go
    fig_traj.add_trace(go.Scatter3d(
        x=camera_positions[:, 0],
        y=camera_positions[:, 1], 
        z=camera_positions[:, 2],
        mode='lines',
        name='trajectory',
        line=dict(color='red', width=3)
    ))
    
    fig_traj.update_layout(title="Camera Trajectory")
    fig_traj.show()
    
    # Print trajectory statistics
    distances = []
    for i in range(1, len(camera_positions)):
        dist = np.linalg.norm(camera_positions[i] - camera_positions[i-1])
        distances.append(dist)
    
    total_distance = sum(distances)
    displacement = np.linalg.norm(camera_positions[-1] - camera_positions[0])
    
    print(f"Trajectory Statistics:")
    print(f"  Total path length: {total_distance:.3f} m")
    print(f"  Net displacement: {displacement:.3f} m")
    print(f"  Average step size: {np.mean(distances):.3f} m")
        
else:
    print("No reconstruction model available for trajectory visualization")

# Load exported poses if available
camera_poses_file = POSES_DIR / "camera_poses.json"
trajectory_file = POSES_DIR / "trajectory_tum.txt"

if camera_poses_file.exists():
    print(f"Loading exported camera poses from {camera_poses_file}")
    
    with open(camera_poses_file, 'r') as f:
        camera_poses = json.load(f)
    
    print(f"✓ Loaded {len(camera_poses)} exported camera poses")
    
    # Display sample poses
    print("Sample poses:")
    for i, pose in enumerate(camera_poses[:3]):
        tx, ty, tz = pose['translation']
        print(f"  {pose['image_name']}: position=({tx:.3f}, {ty:.3f}, {tz:.3f})")
        
else:
    print(f"No exported camera poses found at {camera_poses_file}")

if trajectory_file.exists():
    print(f"✓ TUM trajectory file available: {trajectory_file}")
else:
    print(f"No TUM trajectory file found at {trajectory_file}")

# Summary
print("=" * 60)
print("HLOC RESULTS SUMMARY")
print("=" * 60)

if model is not None:
    print(f"✅ 3D Reconstruction loaded successfully")
    print(f"   📸 Registered images: {len(model.images)}")
    print(f"   🎯 3D points: {len(model.points3D):,}")
    print(f"   📷 Cameras: {len(model.cameras)}")
    
    print(f"📁 Output files:")
    print(f"   📄 3D model: {SFM_DIR}")
    
    if POSES_DIR.exists():
        pose_files = list(POSES_DIR.glob("*.txt")) + list(POSES_DIR.glob("*.json"))
        print(f"   📄 Exported poses: {len(pose_files)} files in {POSES_DIR}")
    
else:
    print(f"❌ No 3D reconstruction found")
    print(f"   Check that pose estimation completed successfully")
    print(f"   Expected location: {SFM_DIR}")

print("Visualization complete!")
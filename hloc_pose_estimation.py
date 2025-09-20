#!/usr/bin/env python3
"""
HLoC Camera Pose Estimation Pipeline

This script performs camera pose estimation from images/videos using HLoC (Hierarchical Localization).
It processes input videos/images, extracts features, performs Structure-from-Motion reconstruction,
and exports camera poses in multiple formats.

Features:
- Process images or videos as input
- Extract features using state-of-the-art extractors (SuperPoint, ALIKED, etc.)
- Match features using various matchers (SuperGlue, LightGlue, etc.)
- Perform Structure-from-Motion (SfM) reconstruction
- Export camera poses for all frames
- Save results without requiring GUI
"""

import os
import cv2
import numpy as np
import argparse
import logging
from pathlib import Path
import shutil
from PIL import Image
import json
import sys

# Load environment variables
from dotenv import load_dotenv
load_dotenv('.env')

# Add hloc module to path
sys.path.append('./modules/hloc')

from hloc import (
    extract_features,
    match_features,
    reconstruction,
    pairs_from_exhaustive,
    pairs_from_retrieval,
)
import pycolmap

def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def extract_frames_from_video(video_path, output_dir, frame_skip=1, max_frames=None, logger=None):
    """Extract frames from video file."""
    cap = cv2.VideoCapture(str(video_path))
    frame_count = 0
    extracted_count = 0
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if logger:
        logger.info(f"Extracting frames from {video_path.name}")
    
    while cap.isOpened() and (max_frames is None or extracted_count < max_frames):
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_skip == 0:
            frame_filename = output_dir / f"frame_{extracted_count:06d}.jpg"
            cv2.imwrite(str(frame_filename), frame)
            extracted_count += 1
            
        frame_count += 1
    
    cap.release()
    if logger:
        logger.info(f"Extracted {extracted_count} frames from {video_path.name}")
    return extracted_count

def process_input_files(input_dir, temp_dir, frame_skip=1, max_images=None, logger=None):
    """Process all input files (videos and images)."""
    images_dir = temp_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    
    processed_files = []
    total_images = 0
    
    if not input_dir.exists():
        if logger:
            logger.warning(f"Input directory {input_dir} does not exist!")
        return [], 0
    
    for file_path in input_dir.iterdir():
        if file_path.is_file():
            file_ext = file_path.suffix.lower()
            
            if file_ext in video_extensions:
                if logger:
                    logger.info(f"Processing video: {file_path.name}")
                video_output_dir = images_dir / file_path.stem
                frame_count = extract_frames_from_video(
                    file_path, video_output_dir, frame_skip, max_images, logger
                )
                total_images += frame_count
                processed_files.append((file_path, 'video', frame_count))
                
            elif file_ext in image_extensions:
                if logger:
                    logger.info(f"Copying image: {file_path.name}")
                dest_path = images_dir / file_path.name
                shutil.copy2(file_path, dest_path)
                total_images += 1
                processed_files.append((file_path, 'image', 1))
    
    if logger:
        logger.info(f"Total images to process: {total_images}")
        for file_path, file_type, count in processed_files:
            logger.info(f"  {file_path.name} ({file_type}): {count} frames")
    
    return processed_files, total_images

def collect_image_list(temp_dir, logger=None):
    """Collect all images from the processing directory."""
    images_dir = temp_dir / "images"
    image_list = []
    
    if not images_dir.exists():
        return image_list
    
    # Collect all images from subdirectories and root
    for file_path in images_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}:
            # Convert to relative path from images_dir
            rel_path = file_path.relative_to(images_dir)
            image_list.append(rel_path.as_posix())
    
    image_list.sort()
    
    if logger:
        logger.info(f"Found {len(image_list)} images for processing")
        if len(image_list) > 0:
            logger.info(f"First few image names:")
            for i, img_name in enumerate(image_list[:5]):
                logger.info(f"  {i+1}: {img_name}")
    
    return image_list

def extract_and_match_features(images_base, image_list, output_dir, feature_extractor, feature_matcher, use_netvlad_retrieval, netvlad_num_matched, logger=None):
    """Extract features from all images and match them."""
    if len(image_list) == 0:
        if logger:
            logger.warning("Skipping feature extraction - no images available")
        return False
    
    # Set up output paths
    sfm_pairs = output_dir / "pairs-sfm.txt"
    features = output_dir / "features.h5"
    matches = output_dir / "matches.h5"
    global_descriptors = output_dir / "global-features.h5"
    
    # Configure feature extractor and matcher
    feature_conf = extract_features.confs[feature_extractor]
    if feature_matcher == "superglue":
        matcher_conf = match_features.confs["superglue"]
    elif feature_extractor.startswith("aliked") and feature_matcher == "lightglue":
        matcher_conf = match_features.confs["aliked+lightglue"]
    else:
        matcher_conf = match_features.confs["nearest_neighbor"]
    
    if logger:
        logger.info(f"Feature extraction configuration: {feature_conf}")
        logger.info(f"Matching configuration: {matcher_conf}")
    
    # Extract local features
    if logger:
        logger.info("Extracting local features...")
    extract_features.main(
        feature_conf, images_base, image_list=image_list, feature_path=features
    )
    
    # Generate image pairs using NetVLAD retrieval or exhaustive matching
    if use_netvlad_retrieval:
        # Configure NetVLAD for global descriptor extraction
        retrieval_conf = extract_features.confs["netvlad"]
        if logger:
            logger.info(f"NetVLAD retrieval configuration: {retrieval_conf}")
        
        # Extract global descriptors with NetVLAD
        if logger:
            logger.info("Extracting global descriptors with NetVLAD...")
        extract_features.main(
            retrieval_conf, images_base, image_list=image_list, feature_path=global_descriptors
        )
        
        # Generate pairs using NetVLAD retrieval (top-K most similar)
        if logger:
            logger.info(f"Generating image pairs with NetVLAD retrieval (top-{netvlad_num_matched})...")
        pairs_from_retrieval.main(
            global_descriptors, sfm_pairs, num_matched=netvlad_num_matched
        )
        
        # Calculate pair statistics
        expected_pairs = len(image_list) * netvlad_num_matched
        if logger:
            logger.info(f"NetVLAD generated ~{expected_pairs:,} pairs (vs {len(image_list)*(len(image_list)-1)//2:,} exhaustive)")
    else:
        # Fallback to exhaustive matching for small datasets
        if logger:
            logger.info("Generating image pairs with exhaustive matching...")
        pairs_from_exhaustive.main(sfm_pairs, image_list=image_list)
    
    # Match features using the generated pairs
    if logger:
        logger.info("Matching features...")
    match_features.main(matcher_conf, sfm_pairs, features=features, matches=matches)
    
    if logger:
        logger.info("Feature extraction and matching completed!")
    
    return True

def run_sfm_reconstruction(images_base, image_list, output_dir, logger=None):
    """Perform Structure-from-Motion reconstruction."""
    if len(image_list) == 0:
        if logger:
            logger.warning("Skipping SfM reconstruction - no images available")
        return None
    
    # Set up SfM output directory
    sfm_dir = output_dir / "sfm"
    sfm_pairs = output_dir / "pairs-sfm.txt"
    features = output_dir / "features.h5"
    matches = output_dir / "matches.h5"
    
    if logger:
        logger.info("Running Structure-from-Motion reconstruction...")
    
    # Run SfM reconstruction
    model = reconstruction.main(
        sfm_dir, images_base, sfm_pairs, features, matches, image_list=image_list
    )
    
    if logger:
        logger.info("Reconstruction completed!")
        logger.info(f"Number of registered images: {len(model.images)}")
        logger.info(f"Number of 3D points: {len(model.points3D)}")
        logger.info(f"Number of cameras: {len(model.cameras)}")
    
    return model

def export_camera_poses(model, output_dir, logger=None):
    """Export camera poses in multiple formats."""
    poses_dir = output_dir / "poses"
    poses_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect camera poses
    camera_poses = []
    
    for image_id, image in model.images.items():
        # Get camera pose (world-to-camera transform)
        cam_from_world = image.cam_from_world
        
        # Convert to camera-to-world (more intuitive)
        world_from_cam = cam_from_world.inverse()
        
        # Extract rotation and translation
        rotation_matrix = world_from_cam.rotation.matrix()
        translation = world_from_cam.translation
        
        # Convert rotation matrix to quaternion (w, x, y, z)
        quaternion = world_from_cam.rotation.quat  # [w, x, y, z]
        
        # Count 3D points visible in this image
        num_points3D = sum(1 for p2D in image.points2D if p2D.has_point3D())
        
        pose_data = {
            'image_id': image_id,
            'image_name': image.name,
            'camera_id': image.camera_id,
            'translation': translation.tolist(),
            'rotation_matrix': rotation_matrix.tolist(),
            'quaternion': quaternion.tolist(),  # [w, x, y, z]
            'num_points3D': num_points3D,
        }
        
        camera_poses.append(pose_data)
    
    # Sort by image name for consistent ordering
    camera_poses.sort(key=lambda x: x['image_name'])
    
    # Export as JSON
    json_file = poses_dir / "camera_poses.json"
    with open(json_file, 'w') as f:
        json.dump(camera_poses, f, indent=2)
    if logger:
        logger.info(f"Exported poses to JSON: {json_file}")
    
    # Export in TUM format (timestamp tx ty tz qx qy qz qw)
    tum_file = poses_dir / "trajectory_tum.txt"
    with open(tum_file, 'w') as f:
        f.write("# TUM trajectory format\n")
        f.write("# timestamp tx ty tz qx qy qz qw\n")
        for i, pose in enumerate(camera_poses):
            tx, ty, tz = pose['translation']
            qw, qx, qy, qz = pose['quaternion']
            f.write(f"{i:06d} {tx:.6f} {ty:.6f} {tz:.6f} {qx:.6f} {qy:.6f} {qz:.6f} {qw:.6f}\n")
    if logger:
        logger.info(f"Exported poses in TUM format: {tum_file}")
    
    # Export in COLMAP format (more detailed)
    colmap_file = poses_dir / "images_poses.txt"
    with open(colmap_file, 'w') as f:
        f.write("# COLMAP image poses\n")
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME, POINTS2D\n")
        for pose in camera_poses:
            qw, qx, qy, qz = pose['quaternion']
            tx, ty, tz = pose['translation']
            f.write(f"{pose['image_id']} {qw:.6f} {qx:.6f} {qy:.6f} {qz:.6f} ")
            f.write(f"{tx:.6f} {ty:.6f} {tz:.6f} {pose['camera_id']} {pose['image_name']}\n")
    if logger:
        logger.info(f"Exported poses in COLMAP format: {colmap_file}")
    
    return camera_poses

def analyze_trajectory(camera_poses, logger=None):
    """Analyze camera trajectory and provide statistics."""
    if len(camera_poses) < 2:
        return
    
    if logger:
        logger.info("Camera trajectory analysis:")
    
    # Calculate trajectory statistics
    positions = np.array([pose['translation'] for pose in camera_poses])
    
    # Trajectory length
    distances = np.sqrt(np.sum(np.diff(positions, axis=0)**2, axis=1))
    total_distance = np.sum(distances)
    
    # Bounding box
    min_pos = np.min(positions, axis=0)
    max_pos = np.max(positions, axis=0)
    bbox_size = max_pos - min_pos
    
    if logger:
        logger.info(f"  Total trajectory length: {total_distance:.3f} units")
        logger.info(f"  Average step size: {np.mean(distances):.3f} units")
        logger.info(f"  Scene bounding box: {bbox_size[0]:.3f} x {bbox_size[1]:.3f} x {bbox_size[2]:.3f}")
        logger.info(f"  Center position: ({np.mean(positions, axis=0)})")

def main():
    parser = argparse.ArgumentParser(description="HLoC Camera Pose Estimation Pipeline")
    
    # Input/Output paths
    parser.add_argument("--input_dir", type=Path, default=Path("./videos"), 
                        help="Input directory containing videos or images (default: ./videos)")
    parser.add_argument("--output_dir", type=Path, default=Path("./outputs/hloc_poses"),
                        help="Output directory for results (default: ./outputs/hloc_poses)")
    parser.add_argument("--temp_dir", type=Path, default=Path("./temp/hloc_processing"),
                        help="Temporary directory for processing (default: ./temp/hloc_processing)")
    
    # Feature extraction and matching
    parser.add_argument("--feature_extractor", type=str, default="superpoint_aachen",
                        choices=["superpoint_aachen", "aliked", "aliked-n16", "disk", "d2net", "r2d2"],
                        help="Feature extractor to use (default: superpoint_aachen)")
    parser.add_argument("--feature_matcher", type=str, default="superglue",
                        choices=["superglue", "lightglue", "nearest_neighbor"],
                        help="Feature matcher to use (default: superglue)")
    
    # NetVLAD retrieval
    parser.add_argument("--use_netvlad_retrieval", action="store_true", default=True,
                        help="Use NetVLAD for image retrieval (default: True)")
    parser.add_argument("--netvlad_num_matched", type=int, default=20,
                        help="Number of most similar images to match with NetVLAD (default: 20)")
    
    # Processing parameters
    parser.add_argument("--max_images", type=int, default=None,
                        help="Maximum number of images to process (default: None, process all)")
    parser.add_argument("--frame_skip", type=int, default=1,
                        help="Extract every N-th frame from videos (default: 1, keep all)")
    
    # Logging
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Override with environment variables if available
    if os.getenv('USE_NETVLAD_RETRIEVAL'):
        args.use_netvlad_retrieval = os.getenv('USE_NETVLAD_RETRIEVAL', 'True').lower() == 'true'
    if os.getenv('NETVLAD_NUM_MATCHED'):
        args.netvlad_num_matched = int(os.getenv('NETVLAD_NUM_MATCHED', 20))
    if os.getenv('FRAME_SAMPLE_RATE'):
        args.frame_skip = int(os.getenv('FRAME_SAMPLE_RATE', 1))
    
    # Create output directories
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.temp_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("HLoC Camera Pose Estimation Pipeline Starting")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Temporary directory: {args.temp_dir}")
    logger.info(f"Feature extractor: {args.feature_extractor}")
    logger.info(f"Feature matcher: {args.feature_matcher}")
    logger.info(f"Using NetVLAD retrieval: {args.use_netvlad_retrieval} (top-{args.netvlad_num_matched} matches)")
    logger.info(f"Frame sampling rate: {args.frame_skip} (every {args.frame_skip} frames)")
    
    try:
        # Process input files
        logger.info("Processing input files...")
        processed_files, total_image_count = process_input_files(
            args.input_dir, args.temp_dir, args.frame_skip, args.max_images, logger
        )
        
        if total_image_count == 0:
            logger.error("No valid input files found! Please add videos or images to the input directory.")
            return 1
        
        # Collect image list
        images_base = args.temp_dir / "images"
        image_list = collect_image_list(args.temp_dir, logger)
        
        if len(image_list) == 0:
            logger.error("No images found for processing!")
            return 1
        
        # Extract and match features
        success = extract_and_match_features(
            images_base, image_list, args.output_dir, 
            args.feature_extractor, args.feature_matcher,
            args.use_netvlad_retrieval, args.netvlad_num_matched, logger
        )
        
        if not success:
            logger.error("Feature extraction and matching failed!")
            return 1
        
        # Run SfM reconstruction
        model = run_sfm_reconstruction(images_base, image_list, args.output_dir, logger)
        
        if model is None:
            logger.error("SfM reconstruction failed!")
            return 1
        
        # Export camera poses
        logger.info("Extracting and exporting camera poses...")
        camera_poses = export_camera_poses(model, args.output_dir, logger)
        
        logger.info(f"Exported {len(camera_poses)} camera poses")
        
        # Display pose summary
        if len(camera_poses) > 0:
            logger.info("Camera poses summary:")
            for i, pose in enumerate(camera_poses[:5]):  # Show first 5
                tx, ty, tz = pose['translation']
                logger.info(f"  {pose['image_name']}: position=({tx:.3f}, {ty:.3f}, {tz:.3f})")
            
            if len(camera_poses) > 5:
                logger.info(f"  ... and {len(camera_poses) - 5} more")
        
        # Analyze trajectory
        analyze_trajectory(camera_poses, logger)
        
        # Final summary
        logger.info("=" * 60)
        logger.info("HLoC CAMERA POSE ESTIMATION PIPELINE - SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✓ Successfully processed {len(image_list)} input images")
        logger.info(f"✓ Reconstructed {len(model.images)} camera poses")
        logger.info(f"✓ Generated {len(model.points3D)} 3D points")
        logger.info(f"✓ Used {len(model.cameras)} camera model(s)")
        
        reconstruction_rate = len(model.images) / len(image_list) * 100
        logger.info(f"✓ Reconstruction success rate: {reconstruction_rate:.1f}%")
        
        logger.info("\nOutput files:")
        logger.info(f"  📁 Main output directory: {args.output_dir}")
        logger.info(f"  📄 Camera poses (JSON): poses/camera_poses.json")
        logger.info(f"  📄 Trajectory (TUM): poses/trajectory_tum.txt")
        logger.info(f"  📄 COLMAP poses: poses/images_poses.txt")
        logger.info(f"  📁 3D reconstruction: sfm/")
        logger.info(f"  📄 Features: features.h5")
        logger.info(f"  📄 Matches: matches.h5")
        
        logger.info("=" * 60)
        logger.info("Pipeline execution completed successfully!")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
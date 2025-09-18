#!/bin/bash

# COLMAP Structure-from-Motion Test Script
# This script extracts frames from a video and runs COLMAP reconstruction

set -e  # Exit on any error

echo "🚀 COLMAP SfM Test Script"
echo "========================"

# Configuration
VIDEO_PATH="/app/data/drone1.mp4"
FRAMES_DIR="/app/temp/frames"
OUTPUT_DIR="/app/temp/reconstruction"
FRAME_SKIP=10
MAX_FRAMES=50
RESIZE_FACTOR=0.5

# Clean up previous runs
echo "🧹 Cleaning up previous runs..."
rm -rf "$FRAMES_DIR" "$OUTPUT_DIR"
mkdir -p "$FRAMES_DIR" "$OUTPUT_DIR"

# Check if running in Docker
if [ ! -f /.dockerenv ]; then
    echo "❌ This script should be run inside the Docker container"
    echo "Run: docker-compose exec colmap-sfm bash"
    echo "Then: ./test.sh"
    exit 1
fi

# Check if video exists
if [ ! -f "$VIDEO_PATH" ]; then
    echo "❌ Video not found: $VIDEO_PATH"
    echo "Available videos in /app/data/:"
    ls -la /app/data/ || echo "No data directory found"
    exit 1
fi

echo "📹 Video found: $VIDEO_PATH"
echo "📁 Frames output: $FRAMES_DIR"
echo "📁 COLMAP output: $OUTPUT_DIR"

# Create Python script for frame extraction
cat > /tmp/extract_frames.py << 'EOF'
import cv2
import os
import sys

def extract_frames(video_path, output_dir, frame_skip=10, max_frames=50, resize_factor=0.5):
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return 0
    
    # Get video info
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video info: {total_frames} frames, {fps:.2f} FPS, {width}x{height}")
    
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_skip == 0:
            if resize_factor != 1.0:
                new_width = int(width * resize_factor)
                new_height = int(height * resize_factor)
                frame = cv2.resize(frame, (new_width, new_height))
            
            frame_filename = f"frame{extracted_count:06d}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            
            extracted_count += 1
            if extracted_count % 10 == 0:
                print(f"  Extracted {extracted_count} frames...")
            
            if max_frames and extracted_count >= max_frames:
                break
        
        frame_count += 1
    
    cap.release()
    print(f"✅ Extracted {extracted_count} frames")
    return extracted_count

if __name__ == "__main__":
    video_path = sys.argv[1]
    output_dir = sys.argv[2]
    frame_skip = int(sys.argv[3])
    max_frames = int(sys.argv[4])
    resize_factor = float(sys.argv[5])
    
    count = extract_frames(video_path, output_dir, frame_skip, max_frames, resize_factor)
    print(f"EXTRACTED_COUNT={count}")
EOF

# Extract frames
echo "🎬 Extracting frames from video..."
cd /app
python /tmp/extract_frames.py "$VIDEO_PATH" "$FRAMES_DIR" "$FRAME_SKIP" "$MAX_FRAMES" "$RESIZE_FACTOR"

# Check if frames were extracted
FRAME_COUNT=$(ls -1 "$FRAMES_DIR"/*.jpg 2>/dev/null | wc -l)
if [ "$FRAME_COUNT" -eq 0 ]; then
    echo "❌ No frames extracted!"
    exit 1
fi

echo "✅ Extracted $FRAME_COUNT frames"

# Create Python script for COLMAP reconstruction
cat > /tmp/run_colmap.py << 'EOF'
import os
import sys
import pycolmap
from pathlib import Path

def run_colmap_reconstruction(frames_dir, output_dir):
    print("🔧 Initializing COLMAP reconstruction...")
    
    frames_path = Path(frames_dir)
    output_path = Path(output_dir)
    
    # Create database
    database_path = output_path / "database.db"
    print(f"📂 Creating database: {database_path}")
    
    # Feature extraction
    print("🔍 Extracting SIFT features...")
    pycolmap.extract_features(database_path, frames_path)
    
    # Feature matching
    print("🔗 Matching features...")
    pycolmap.match_exhaustive_features(database_path)
    
    # Incremental reconstruction
    print("🏗️  Running incremental reconstruction...")
    maps = pycolmap.incremental_mapping(database_path, frames_path, output_path)
    
    if not maps:
        print("❌ No reconstruction generated!")
        return False
    
    print(f"✅ Generated {len(maps)} reconstruction(s)")
    
    # Get the best reconstruction (largest)
    best_idx = max(maps.keys(), key=lambda k: len(maps[k].images))
    reconstruction = maps[best_idx]
    
    print(f"📊 Best reconstruction stats:")
    print(f"  Images: {len(reconstruction.images)}")
    print(f"  Points: {len(reconstruction.points3D)}")
    print(f"  Cameras: {len(reconstruction.cameras)}")
    
    # Export point cloud
    output_ply = output_path / "points.ply"
    reconstruction.export_PLY(str(output_ply))
    print(f"💾 Point cloud saved: {output_ply}")
    
    # Export camera poses in TUM format
    output_trajectory = output_path / "trajectory.txt"
    with open(output_trajectory, 'w') as f:
        f.write("# timestamp tx ty tz qx qy qz qw\n")
        for image_id in sorted(reconstruction.images.keys()):
            image = reconstruction.images[image_id]
            quat = image.qvec  # quaternion (w, x, y, z)
            trans = image.tvec  # translation
            # Convert to TUM format: timestamp tx ty tz qx qy qz qw
            f.write(f"{image_id:.6f} {trans[0]:.6f} {trans[1]:.6f} {trans[2]:.6f} "
                   f"{quat[1]:.6f} {quat[2]:.6f} {quat[3]:.6f} {quat[0]:.6f}\n")
    
    print(f"📍 Trajectory saved: {output_trajectory}")
    
    return True

if __name__ == "__main__":
    frames_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    try:
        success = run_colmap_reconstruction(frames_dir, output_dir)
        if success:
            print("\n✅ COLMAP reconstruction completed successfully!")
        else:
            print("\n❌ COLMAP reconstruction failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ COLMAP failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF

# Run COLMAP
echo "🚀 Running COLMAP reconstruction..."
python /tmp/run_colmap.py "$FRAMES_DIR" "$OUTPUT_DIR"

# Show results
echo ""
echo "📊 Results Summary"
echo "=================="
echo "Input video: $VIDEO_PATH"
echo "Frames extracted: $FRAME_COUNT"
echo "Output directory: $OUTPUT_DIR"

echo ""
echo "📁 Generated files:"
if [ -d "$OUTPUT_DIR" ]; then
    ls -lah "$OUTPUT_DIR/"
else
    echo "  No output directory found"
fi

# Check key output files
KEY_FILES=("trajectory.txt" "points.ply" "database.db")
echo ""
echo "🔍 Key output files:"
for file in "${KEY_FILES[@]}"; do
    if [ -f "$OUTPUT_DIR/$file" ]; then
        size=$(stat -f%z "$OUTPUT_DIR/$file" 2>/dev/null || stat -c%s "$OUTPUT_DIR/$file" 2>/dev/null)
        echo "  ✅ $file (${size} bytes)"
    else
        echo "  ❌ $file (missing)"
    fi
done

# Show trajectory sample
if [ -f "$OUTPUT_DIR/trajectory.txt" ]; then
    echo ""
    echo "🛰️  Camera trajectory sample (first 5 poses):"
    head -5 "$OUTPUT_DIR/trajectory.txt"
fi

echo ""
echo "🎉 Test completed!"
echo "💡 To view results: ls -la $OUTPUT_DIR/"
echo "💡 To see trajectory: cat $OUTPUT_DIR/trajectory.txt"

# Clean up temp files
rm -f /tmp/extract_frames.py /tmp/run_colmap.py

echo "✨ Done!"
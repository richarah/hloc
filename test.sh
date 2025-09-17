#!/bin/bash

# COLMAP-SLAM Test Script
# This script extracts frames from a video and runs the SLAM pipeline

set -e  # Exit on any error

echo "🚀 COLMAP-SLAM Test Script"
echo "=========================="

# Configuration
VIDEO_PATH="/workspace/videos/drone1.mp4"
FRAMES_DIR="/workspace/temp/frames"
OUTPUT_DIR="/workspace/temp/reconstruction"
FRAME_SKIP=10
MAX_FRAMES=20
RESIZE_FACTOR=0.25

# Clean up previous runs
echo "🧹 Cleaning up previous runs..."
rm -rf "$FRAMES_DIR" "$OUTPUT_DIR"
mkdir -p "$FRAMES_DIR" "$OUTPUT_DIR"

# Check if running in Docker
if [ ! -f /.dockerenv ]; then
    echo "❌ This script should be run inside the Docker container"
    echo "Run: docker-compose exec colmap-slam bash"
    echo "Then: ./test.sh"
    exit 1
fi

# Check if video exists
if [ ! -f "$VIDEO_PATH" ]; then
    echo "❌ Video not found: $VIDEO_PATH"
    echo "Available videos in /workspace/videos/:"
    ls -la /workspace/videos/ || echo "No videos directory found"
    exit 1
fi

echo "📹 Video found: $VIDEO_PATH"
echo "📁 Frames output: $FRAMES_DIR"
echo "📁 SLAM output: $OUTPUT_DIR"

# Create Python script for frame extraction
cat > /tmp/extract_frames.py << 'EOF'
import cv2
import os
import sys

def extract_frames(video_path, output_dir, frame_skip=10, max_frames=20, resize_factor=0.25):
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
            if extracted_count % 5 == 0:
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
cd /workspace
python /tmp/extract_frames.py "$VIDEO_PATH" "$FRAMES_DIR" "$FRAME_SKIP" "$MAX_FRAMES" "$RESIZE_FACTOR"

# Check if frames were extracted
FRAME_COUNT=$(ls -1 "$FRAMES_DIR"/*.jpg 2>/dev/null | wc -l)
if [ "$FRAME_COUNT" -eq 0 ]; then
    echo "❌ No frames extracted!"
    exit 1
fi

echo "✅ Extracted $FRAME_COUNT frames"

# Create Python script for SLAM
cat > /tmp/run_slam.py << 'EOF'
import os
import sys
sys.path.append('/workspace/modules/COLMAP_SLAM')

from pipeline import Pipeline
from src import enums

def run_slam(frames_dir, output_dir):
    print("🔧 Initializing SLAM pipeline...")
    
    # Create pipeline
    pipeline = Pipeline(
        extractor=enums.Extractors.SuperPoint,
        matcher=enums.Matchers.SuperGlue
    )
    
    # Load data
    print(f"📂 Loading frames from: {frames_dir}")
    pipeline.load_data(
        images=frames_dir,
        outputs=output_dir,
        exports="reconstruction.ply",
        init_max_num_images=30,
        frame_skip=1,
        max_frame=-1
    )
    
    print(f"📊 Loaded {len(pipeline.frame_names)} frames for processing")
    
    # Run SLAM
    print("🏃 Running SLAM reconstruction...")
    pipeline.run(optical_flow_threshold=0.05)
    
    # Print results
    print("\n📈 Reconstruction Summary:")
    print("=" * 50)
    print(pipeline.reconstruction.summary())
    
    return pipeline

if __name__ == "__main__":
    frames_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    try:
        pipeline = run_slam(frames_dir, output_dir)
        print("\n✅ SLAM reconstruction completed successfully!")
        
        # Save summary
        with open(f"{output_dir}/summary.txt", "w") as f:
            f.write("COLMAP-SLAM Reconstruction Summary\n")
            f.write("=" * 40 + "\n\n")
            f.write(pipeline.reconstruction.summary())
        
        print(f"📄 Summary saved to: {output_dir}/summary.txt")
        
    except Exception as e:
        print(f"❌ SLAM failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
EOF

# Run SLAM
echo "🚀 Running SLAM pipeline..."
python /tmp/run_slam.py "$FRAMES_DIR" "$OUTPUT_DIR"

# Show results
echo ""
echo "📊 Results Summary"
echo "=================="
echo "Input video: $VIDEO_PATH"
echo "Frames extracted: $FRAME_COUNT"
echo "Output directory: $OUTPUT_DIR"

if [ -f "$OUTPUT_DIR/summary.txt" ]; then
    echo ""
    echo "📈 Reconstruction Summary:"
    cat "$OUTPUT_DIR/summary.txt"
fi

echo ""
echo "📁 Generated files:"
if [ -d "$OUTPUT_DIR" ]; then
    ls -lah "$OUTPUT_DIR/"
else
    echo "  No output directory found"
fi

# Check key output files
KEY_FILES=("estimation.txt" "reconstruction.ply" "cameras.bin" "images.bin" "points3D.bin")
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
if [ -f "$OUTPUT_DIR/estimation.txt" ]; then
    echo ""
    echo "🛰️  Camera trajectory sample (first 5 poses):"
    head -5 "$OUTPUT_DIR/estimation.txt"
fi

echo ""
echo "🎉 Test completed!"
echo "💡 To view results: ls -la $OUTPUT_DIR/"
echo "💡 To see trajectory: cat $OUTPUT_DIR/estimation.txt"

# Clean up temp files
rm -f /tmp/extract_frames.py /tmp/run_slam.py

echo "✨ Done!"
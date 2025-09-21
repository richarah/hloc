# HLS Monorepo - Internal use only

Monorepo for internal projects of Haydon Laastad Systems.

Work in progress. Major changes may occur at any time.

### Setup & usage

```bash
git submodule init
git submodule update --init --recursive --remote
git submodule sync

# Using Docker (recommended)
docker-compose up
```

## The big idea / VoPR pipeline
1. input all the videos/photos in the zone of operation. drone footage, photos, cctv, everything. (NB: DO NOT INCLUDE IMAGES WITH FIDUCIAL MARKERS; this may confuse the feature matching algo later on)
2. generate a point cloud from these.
3. calibrate the cameras we want to use and get a picture from them, use this with hloc and our point cloud for relative localisation (where are cameras in relation to each other?)
4. compare with Ground Control Points, known camera positions, or distances between known GPS coords to calculate absolute scale.
optionally: place object of known size at a known position within the FOV of a camera. log its position within the point cloud. repeat for multiple cameras. use this data to create a mapping between realspace and pointcloud-space
5. run voxel-projection, detect stuff

## To do
- post-generation localisation workflow
- relative-to-absolute scale workflow
- intrinsic calibration (work out distortion factor of camera)
- something to figure out if we are indoors or outdoors and select a solver accordingly, unless we set manually
- charuco: already solved, detect_diamonds.cpp?
- checkpoints
- luke bort urelevant data
- further research into SNS solver and necessary iters to get acceptable results
- Skye integration for real time visualisation
- assess impact of removing thread cap in /mnt/c/Users/rahay/Documents/hls/modules/hloc/hloc/reconstruction.py:112
- feature matching match_features.py:242,244 diminishing returns?
- make COLMAP defaults less conservative?
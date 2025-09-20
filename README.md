# HLS Monorepo - Internal use only

Monorepo for internal projects of Haydon Laastad Systems.

Work in progress. Major changes may occur at any time.

### Setup & usage

```bash
git submodule init
git submodule update --init --recursive --remote
git submodule sync

# Using Docker (recommended)
docker-compose up --build

# Then open notebooks/COLMAP_SLAM_Demo.ipynb in Jupyter, 127.0.0.1 port 8888
```

**Optional:**
- CUDA (for GPU acceleration)
- CMake (for building C++ modules)

The project uses Jupyter notebooks for interactive testing and development, these can be found under `./notebooks`.

## Roadmap

- Explore replacing Sinkhorn algo with sparse Newton-Sinkhorn https://arxiv.org/html/2401.12253v1/#S6
- Skye integration for real time visualisation
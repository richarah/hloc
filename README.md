# HLS monorepo - INTERNAL USE ONLY

Monorepo for internal projects of Haydon Laastad Systems (name is tentative, it came to me in a dream)

This is as WIP as it gets. Major changes may occur at any time.

#### Demos (TBD)

- SLAM from single moving viewport (sousveillance or FPV drone footage)

- Tomographic 3D reconstruction from partially-overlapping static viewports (CCTV footage or similar)

- Viewport calibration (Aruco/ChAruco pattern unless more suitable standards exist)

- Rendering from point cloud?

#### Modules

- **Skye** - framework for being able to render any point cloud that fits in GPU memory, in real time

- **COLMAP_SLAM** - Simultaneous Localization and Mapping (SLAM) pipeline

- **glomap** - Global SfM. COLMAP alternative, possibly to be used for augmenting SLAM pipeline. Faster in benchmarks, efficacy yet to be assessed for our use-case

#### Todos

- finish demos
- explore possibilities for replacing/augmenting COLMAP components in SfM/SLAM pipeline with GLOMAP
- integrate Skye, real-time visualisation



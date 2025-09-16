# HLS monorepo - Internal use only

Monorepo for internal projects of Haydon Laastad Systems (name is tentative, order may be reversed, it came to me in a dream)

Work in progress. Major changes may occur at any time.

#### Demos (TBD)

- SLAM from single moving viewport (sousveillance or FPV drone footage). Realtime if possible

- Tomographic 3D reconstruction from partially-overlapping static viewports (CCTV footage or similar). Realtime if possible

- Viewport calibration (Aruco/ChAruco pattern unless more suitable standards exist)

- Rendering from point cloud?

**Speculative:**

- SLAM + sensor fusion, multiple viewports? See tank example from presentation

#### Modules

- **Skye** - framework for being able to render any point cloud that fits in GPU memory, in real time

- **COLMAP_SLAM** - Simultaneous Localization and Mapping (SLAM) pipeline

- **glomap** - Global SfM. COLMAP alternative, possibly to be used for augmenting SLAM pipeline. Faster in benchmarks, efficacy yet to be assessed for our use-case

#### Todos

- finish demos
- explore possibilities for replacing/augmenting COLMAP components in SfM/SLAM pipeline with GLOMAP
- integrate Skye, real-time visualisation

**Outside this repo**

- server

- 

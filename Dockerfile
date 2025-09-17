FROM nvidia/cuda:12.2.0-base-ubuntu20.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /workspace

# Add deadsnakes PPA for Python 3.10
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/nightly && \
    apt-get update

RUN apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3.10-distutils \
    python3-apt

# Install system dependencies
RUN apt-get install -y \
    git \
    build-essential \
    gnupg \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libboost-test-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libsqlite3-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev \
    wget \
    unzip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libglu1-mesa \
    libosmesa6-dev \
    freeglut3-dev \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.10 and set it as default
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python3.10 get-pip.py && \
    rm get-pip.py && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip3 pip3 /usr/local/bin/pip3.10 1

# Install newer CMake (required for COLMAP's faiss dependency)
# RUN apt-get update && \
#    wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null && \
#    add-apt-repository 'deb https://apt.kitware.com/ubuntu/ focal main' && \
#    apt-get update && \
#    apt-get install -y cmake && \
#    rm -rf /var/lib/apt/lists/*

# Install COLMAP using pre-built package
RUN apt-get update && apt-get install -y colmap && rm -rf /var/lib/apt/lists/*

# Install COLMAP (fix compilation issues with main branch) - COMMENTED OUT FOR SPEED
# RUN git clone https://github.com/colmap/colmap.git /tmp/colmap && \
#     cd /tmp/colmap && \
#     sed -i 's/problem.IsParameterBlockConstant(point3D.xyz.data())/problem.IsParameterBlockConstant(const_cast<double*>(point3D.xyz.data()))/g' src/colmap/estimators/bundle_adjustment.cc && \
#     mkdir build && \
#     cd build && \
#     cmake .. -DCMAKE_CUDA_ARCHITECTURES=all && \
#     make -j$(nproc) && \
#     make install && \
#     rm -rf /tmp/colmap

# Install Python dependencies
COPY requirements.txt /workspace/
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip3 install --no-cache-dir hloc && \
    pip3 install --no-cache-dir pycolmap && \
    pip3 install --no-cache-dir pyceres && \
    pip3 install --no-cache-dir -r requirements.txt

# Install hloc (Hierarchical Localization) - COMMENTED OUT FOR SPEED
# RUN git clone --recursive https://github.com/cvg/Hierarchical-Localization.git /tmp/hloc && \
#     cd /tmp/hloc && \
#     pip3 install -e . && \
#     rm -rf /tmp/hloc/.git

# Install pyceres - COMMENTED OUT FOR SPEED
# RUN git clone https://github.com/cvg/pyceres.git /tmp/pyceres && \
#     cd /tmp/pyceres && \
#     pip3 install -e . && \
#     rm -rf /tmp/pyceres/.git

# Set OpenGL environment variables for headless operation
ENV LIBGL_ALWAYS_INDIRECT=0
ENV MESA_GL_VERSION_OVERRIDE=4.5
ENV MESA_GLSL_VERSION_OVERRIDE=450
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV DISPLAY=:99

# Create directories for data and outputs
RUN mkdir -p /workspace/data /workspace/outputs /workspace/videos

# Copy the project code
COPY modules/COLMAP_SLAM/ /workspace/COLMAP_SLAM/
COPY notebooks/ /workspace/notebooks/

# Install Jupyter and extensions
RUN pip3 install --no-cache-dir jupyter jupyterlab ipywidgets tqdm

# Expose Jupyter port
EXPOSE 8888

# Create startup script
RUN echo '#!/bin/bash\n\
# Start virtual display for headless GUI operations\n\
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &\n\
# Start Jupyter Lab\n\
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token="" --NotebookApp.password=""\n\
' > /workspace/start.sh && chmod +x /workspace/start.sh

CMD ["/workspace/start.sh"]
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np
import pycolmap

logger = logging.getLogger(__name__)


def parse_image_list(path, with_intrinsics=False):
    images = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip("\n")
            if len(line) == 0 or line[0] == "#":
                continue
            name, *data = line.split()
            if with_intrinsics:
                model, width, height, *params = data
                params = np.array(params, float)
                cam = pycolmap.Camera(
                    model=model, width=int(width), height=int(height), params=params
                )
                images.append((name, cam))
            else:
                images.append(name)

    assert len(images) > 0
    logger.info(f"Imported {len(images)} images from {path.name}")
    return images


def parse_image_lists(paths, with_intrinsics=False):
    images = []
    files = list(Path(paths.parent).glob(paths.name))
    assert len(files) > 0
    for lfile in files:
        images += parse_image_list(lfile, with_intrinsics=with_intrinsics)
    return images


def parse_retrieval(path):
    retrieval = defaultdict(list)
    with open(path, "r") as f:
        for p in f.read().rstrip("\n").split("\n"):
            if len(p) == 0:
                continue
            parts = p.split()
            if len(parts) == 2:
                # Simple case: no spaces in filenames
                q, r = parts
            else:
                # Handle filenames with spaces: split only on the space between two .jpg/.png/.jpeg paths
                # Find where the first image path ends (after .jpg, .png, etc.)
                for i, part in enumerate(parts):
                    if part.endswith(('.jpg', '.png', '.jpeg', '.JPG', '.PNG', '.JPEG')):
                        # First image ends here, rest is the second image
                        q = ' '.join(parts[:i+1])
                        r = ' '.join(parts[i+1:])
                        break
                else:
                    # Fallback: couldn't find image extension, skip this line
                    logger.warning(f"Could not parse retrieval line: {p}")
                    continue
            retrieval[q].append(r)
    return dict(retrieval)


def names_to_pair(name0, name1, separator="/"):
    return separator.join((name0.replace("/", "-"), name1.replace("/", "-")))


def names_to_pair_old(name0, name1):
    return names_to_pair(name0, name1, separator="_")

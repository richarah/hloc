import argparse
import multiprocessing
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import pycolmap
import tqdm

from . import logger
from .triangulation import (
    OutputCapture,
    estimation_and_geometric_verification,
    import_features,
    import_matches,
    parse_option_args,
)
from .utils.io import open_colmap_database


def create_sanitized_pairs_file(pairs_path: Path, output_path: Path) -> Path:
    """
    Create a sanitized pairs file for pycolmap that handles spaces in filenames.
    Uses tab separator instead of space to avoid splitting issues.
    """
    with open(str(pairs_path), "r") as f_in, open(str(output_path), "w") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            # Handle image paths with spaces by using non-greedy match on common image extensions
            match = re.match(
                r'(.+?\.(?:jpg|jpeg|png|bmp|tiff|tif))\s+(.+?\.(?:jpg|jpeg|png|bmp|tiff|tif))$',
                line,
                re.IGNORECASE
            )
            if match:
                # Write with tab separator for pycolmap
                f_out.write(f"{match.group(1)}\t{match.group(2)}\n")
            else:
                # Passthrough if simple format
                parts = line.split()
                if len(parts) == 2:
                    f_out.write(f"{parts[0]}\t{parts[1]}\n")
                else:
                    logger.warning(f"Could not parse pair line: {line}")
    return output_path


def create_empty_db(database_path: Path):
    if database_path.exists():
        logger.warning("The database already exists, deleting it.")
        database_path.unlink()
    logger.info("Creating an empty database...")
    with open_colmap_database(database_path) as _:
        pass


def import_images(
    image_dir: Path,
    database_path: Path,
    camera_mode: pycolmap.CameraMode,
    image_list: Optional[List[str]] = None,
    options: Optional[Dict[str, Any]] = None,
):
    logger.info("Importing images into the database...")
    if options is None:
        options = {}
    images = list(image_dir.iterdir())
    if len(images) == 0:
        raise IOError(f"No images found in {image_dir}.")
    with pycolmap.ostream():
        pycolmap.import_images(
            database_path,
            image_dir,
            camera_mode,
            image_names=image_list or [],
            options=options,
        )


def get_image_ids(database_path: Path) -> Dict[str, int]:
    images = {}
    with open_colmap_database(database_path) as db:
        images = {image.name: image.image_id for image in db.read_all_images()}
    return images


def incremental_mapping(
    database_path: Path,
    image_dir: Path,
    sfm_path: Path,
    options: Optional[Dict[str, Any]] = None,
) -> dict[int, pycolmap.Reconstruction]:
    num_images = pycolmap.Database(database_path).num_images
    pbars = []

    def restart_progress_bar():
        if len(pbars) > 0:
            pbars[-1].close()
        pbars.append(
            tqdm.tqdm(
                total=num_images,
                desc=f"Reconstruction {len(pbars)}",
                unit="images",
                postfix="registered",
                mininterval=3.0,      # Update every 3 seconds max (reduces screen scrollback pollution)
                miniters=10,          # Update after at least 10 iterations (additional rate limiting)
                smoothing=0.5,        # Smooth the speed estimate (0=instant, 1=infinite)
                leave=False,          # Don't leave progress bar in scrollback after completion
            )
        )
        pbars[-1].update(2)

    # Convert dictionary options to IncrementalPipelineOptions object
    pipeline_options = pycolmap.IncrementalPipelineOptions()
    if options:
        # Set mapper options (these are nested under pipeline_options.mapper)
        for key, value in options.items():
            if hasattr(pipeline_options.mapper, key):
                setattr(pipeline_options.mapper, key, value)
            elif hasattr(pipeline_options, key):
                setattr(pipeline_options, key, value)
            else:
                logger.warning(f"Unknown mapper option: {key}")

    reconstructions = pycolmap.incremental_mapping(
        str(database_path),
        str(image_dir),
        str(sfm_path),
        options=pipeline_options,
        initial_image_pair_callback=restart_progress_bar,
        next_image_callback=lambda: pbars[-1].update(1),
    )

    return reconstructions


def run_reconstruction(
    sfm_dir: Path,
    database_path: Path,
    image_dir: Path,
    verbose: bool = False,
    options: Optional[Dict[str, Any]] = None,
) -> pycolmap.Reconstruction:
    models_path = sfm_dir / "models"
    models_path.mkdir(exist_ok=True, parents=True)
    logger.info("Running 3D reconstruction...")
    if options is None:
        options = {}
    options = {"num_threads": min(multiprocessing.cpu_count(), 64), **options}

    with OutputCapture(verbose):
        reconstructions = incremental_mapping(
            database_path, image_dir, models_path, options=options
        )

    if len(reconstructions) == 0:
        logger.error("Could not reconstruct any model!")
        return None
    logger.info(f"Reconstructed {len(reconstructions)} model(s).")

    largest_index = None
    largest_num_images = 0
    for index, rec in reconstructions.items():
        num_images = rec.num_reg_images()
        if num_images > largest_num_images:
            largest_index = index
            largest_num_images = num_images
    assert largest_index is not None
    logger.info(
        f"Largest model is #{largest_index} " f"with {largest_num_images} images."
    )

    for filename in [
        "images.bin",
        "cameras.bin",
        "points3D.bin",
        "frames.bin",
        "rigs.bin",
    ]:
        if (sfm_dir / filename).exists():
            (sfm_dir / filename).unlink()
        shutil.move(str(models_path / str(largest_index) / filename), str(sfm_dir))
    return reconstructions[largest_index]


def main(
    sfm_dir: Path,
    image_dir: Path,
    pairs: Path,
    features: Path,
    matches: Path,
    camera_mode: pycolmap.CameraMode = pycolmap.CameraMode.AUTO,
    verbose: bool = False,
    skip_geometric_verification: bool = False,
    min_match_score: Optional[float] = None,
    image_list: Optional[List[str]] = None,
    image_options: Optional[Dict[str, Any]] = None,
    mapper_options: Optional[Dict[str, Any]] = None,
) -> pycolmap.Reconstruction:
    assert features.exists(), features
    assert pairs.exists(), pairs
    assert matches.exists(), matches

    sfm_dir.mkdir(parents=True, exist_ok=True)
    database = sfm_dir / "database.db"

    logger.info(f"Writing COLMAP logs to {sfm_dir / 'colmap.LOG.*'}")
    pycolmap.logging.set_log_destination(pycolmap.logging.INFO, sfm_dir / "colmap.LOG.")

    create_empty_db(database)
    import_images(image_dir, database, camera_mode, image_list, image_options)
    image_ids = get_image_ids(database)

    # Create sanitized pairs file for pycolmap (handles spaces in filenames)
    sanitized_pairs = sfm_dir / "pairs-sanitized.txt"
    create_sanitized_pairs_file(pairs, sanitized_pairs)

    with open_colmap_database(database) as db:
        import_features(image_ids, db, features)
        import_matches(
            image_ids,
            db,
            sanitized_pairs,  # Use sanitized pairs file
            matches,
            min_match_score,
            skip_geometric_verification,
        )
    if not skip_geometric_verification:
        estimation_and_geometric_verification(database, sanitized_pairs, verbose)  # Use sanitized pairs
    reconstruction = run_reconstruction(
        sfm_dir, database, image_dir, verbose, mapper_options
    )
    if reconstruction is not None:
        logger.info(
            f"Reconstruction statistics:\n{reconstruction.summary()}"
            + f"\n\tnum_input_images = {len(image_ids)}"
        )
    return reconstruction


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sfm_dir", type=Path, required=True)
    parser.add_argument("--image_dir", type=Path, required=True)

    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--matches", type=Path, required=True)

    parser.add_argument(
        "--camera_mode",
        type=str,
        default="AUTO",
        choices=list(pycolmap.CameraMode.__members__.keys()),
    )
    parser.add_argument("--skip_geometric_verification", action="store_true")
    parser.add_argument("--min_match_score", type=float)
    parser.add_argument("--verbose", action="store_true")

    parser.add_argument(
        "--image_options",
        nargs="+",
        default=[],
        help="List of key=value from {}".format(pycolmap.ImageReaderOptions().todict()),
    )
    parser.add_argument(
        "--mapper_options",
        nargs="+",
        default=[],
        help="List of key=value from {}".format(
            pycolmap.IncrementalMapperOptions().todict()
        ),
    )
    args = parser.parse_args().__dict__

    image_options = parse_option_args(
        args.pop("image_options"), pycolmap.ImageReaderOptions()
    )
    mapper_options = parse_option_args(
        args.pop("mapper_options"), pycolmap.IncrementalMapperOptions()
    )

    main(**args, image_options=image_options, mapper_options=mapper_options)

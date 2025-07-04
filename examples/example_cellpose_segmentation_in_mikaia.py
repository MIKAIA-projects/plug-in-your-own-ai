"""
This script provides a simple integration of Cellpose segmentation with the MIKAIA API.
It processes a whole slide image by tiling, applies a two-stain preprocessing, runs Cellpose instance segmentation,
and creates polygon annotations for each detected cell instance in MIKAIA.
Don't forget to install the required packages:
pip install cellpose opencv-python scikit-image tqdm numpy
mikaia_plugin_api can be installed from the MIKAIA plugin repository, use wheel file
"""
import cv2
import sys
import tqdm
import numpy as np
from mikaia_plugin_api import mikaia_api as miaapi
from cellpose import models


def calculate_input_in_um(input_width_px, slide_info):
    """
    Convert input tile width in pixels to micrometers using slide native resolution.
    Args:
        input_width_px (int): Tile width in pixels.
        slide_info: Slide info object with nativeResolution attribute.
    Returns:
        tuple: (input_width_um, input_height_um) in micrometers.
    """
    res = slide_info.nativeResolution  # resolution in um/px
    input_width_um = input_width_px * res.width
    input_height_um = input_width_px * res.height
    return input_width_um, input_height_um


def calculate_tiles_from_rois(rois, input_width_um, input_height_um):
    """
    Split each ROI into tiles of the given size in micrometers.
    Args:
        rois (list): List of ROI objects.
        input_width_um (float): Tile width in micrometers.
        input_height_um (float): Tile height in micrometers.
    Returns:
        list: List of tile coordinates [[x0, y0], [x1, y1]] in micrometers.
    """
    tiles = []
    for roi in rois:
        if isinstance(roi, miaapi.RectF):
            roi_x_um = roi.x
            roi_y_um = roi.y
            roi_width_um = roi.width
            roi_height_um = roi.height
        else:
            br = roi.boundingRect()
            roi_x_um = br.x
            roi_y_um = br.y
            roi_width_um = br.width
            roi_height_um = br.height

        num_tiles_width = int(np.ceil(roi_width_um / input_width_um))
        num_tiles_height = int(np.ceil(roi_height_um / input_height_um))

        current_corner = miaapi.PointF(roi_x_um, roi_y_um)
        for y in range(num_tiles_height):
            for x in range(num_tiles_width):
                tile = [[current_corner.x, current_corner.y],
                        [current_corner.x + input_width_um, current_corner.y + input_height_um]]
                tiles.append(tile)
                current_corner.x += input_width_um
            current_corner.x = roi_x_um
            current_corner.y += input_height_um
    return tiles


def find_instance_contour(inst_map, correction_factor_h, correction_factor_w, tile_coordinates, pad=0):
    """
    Find contours for each instance in the instance mask and map them to slide coordinates.
    Args:
        inst_map (ndarray): Instance mask (H, W), each cell has a unique label.
        correction_factor_h (float): Scaling factor for x-coordinates.
        correction_factor_w (float): Scaling factor for y-coordinates.
        tile_coordinates (list): Top-left coordinates of the tile in micrometers.
        pad (int): Optional padding for contour coordinates.
    Returns:
        list: List of contours (each a list of [x, y] points in slide micrometers).
    """
    from skimage.measure import regionprops
    props = regionprops(inst_map)
    x_tile, y_tile = tile_coordinates[0]
    result = []
    for r in props:
        minr, minc, maxr, maxc = r.bbox
        mask = (r.image.astype('uint8')) * 255
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        cnt = max(cnts, key=cv2.contourArea).reshape(-1, 2)
        cnt[:, 0] = np.clip(cnt[:, 0] + minc + pad, 0, inst_map.shape[1] - 1)
        cnt[:, 1] = np.clip(cnt[:, 1] + minr + pad, 0, inst_map.shape[0] - 1)
        cnt = cnt.astype('float32')
        cnt[:, 0] = cnt[:, 0] * correction_factor_h + x_tile
        cnt[:, 1] = cnt[:, 1] * correction_factor_w + y_tile
        result.append(cnt.tolist())
    return result


def cellpose_mikaia_simple_pipeline(cur_slide_service, checkpoint_path, cellpose_channels,
                                    input_width_px=1500, scale_factor=1.):
    """
    Main pipeline for Cellpose segmentation and annotation in MIKAIA.
    Args:
        cur_slide_service: MIKAIA SlideService object.
        checkpoint_path (str): Path to Cellpose model weights.
        cellpose_channels: Channel configuration for Cellpose.
        input_width_px (int): Tile width in pixels.
        scale_factor (float): Optional scaling factor for resolution.
    """
    class_list = ["Cells"]
    color_list = ["#FFFF0000"]
    def stain_deconvolution_two_stain(image):
        """
        Dummy stain deconvolution for two stains. Replace with your own logic if needed.
        Args:
            image (ndarray): RGB image (H, W, 3).
        Returns:
            tuple: (out_1, out_2) two single-channel images.
        """
        out_1 = image[:, :, 0]  # R
        out_2 = image[:, :, 1]  # G
        return out_1, out_2

    def post_aug_two_stain(image):
        """
        Preprocessing: apply two-stain deconvolution and stack as two channels.
        Args:
            image (ndarray): RGB image (H, W, 3).
        Returns:
            ndarray: Preprocessed image (2, H, W) float32.
        """
        out_1, out_2 = stain_deconvolution_two_stain(image)
        out = np.stack([out_2, out_1], axis=-1)
        out = np.transpose(out, (2, 0, 1))
        out = out.astype("float32")
        out /= 255.
        return out

    preprocess_func = post_aug_two_stain
    print("Loading model...")
    cur_model = models.CellposeModel(gpu=True, pretrained_model=checkpoint_path)
    slide_info = cur_slide_service.getSlideInfo()
    input_width_um, input_height_um = calculate_input_in_um(input_width_px, slide_info)
    slide_rect = slide_info.slideRect
    rois = cur_slide_service.getAnalysisRoi().roi
    if len(rois) == 0:
        rois = [slide_rect]
    if not isinstance(rois, list):
        rois = [rois]
    tiles = calculate_tiles_from_rois(rois, input_width_um, input_height_um)
    _ = [cur_slide_service.createAnnotationClass(
        class_name=class_list[0], description=class_list[0],
        group_name="Cell segmentation", line_width_px=3,
        line_color=color_list[0], fill_color=color_list[0], opacity=0.3)]
    for tile_coords in tqdm.tqdm(tiles, desc="Processing tiles", total=len(tiles)):
        tile_img = cur_slide_service.getROI(
            tile_coords[0][0], tile_coords[0][1], input_width_um, input_height_um,
            slide_info.nativeResolution.width * scale_factor, slide_info.nativeResolution.height * scale_factor, px_format="RGB")
        inst_mask = process_tile_cellpose(cur_model, preprocess_func(tile_img), cellpose_channels)
        correction_factor_h = input_width_um / inst_mask.shape[1]
        correction_factor_w = input_height_um / inst_mask.shape[0]
        contours = find_instance_contour(inst_mask.astype(np.int32), correction_factor_h, correction_factor_w, tile_coords)
        annotations = []
        for cnt in contours:
            if len(cnt) < 3:
                continue
            cnt_flat = np.array(cnt).flatten().tolist()
            annotations.append(cur_slide_service.createAnnotation(
                "Polygon", outline=[cnt_flat], class_name=class_list[0]))
        if annotations:
            cur_slide_service.addAnnotations(annotations)
    print("End of pipeline, annotations added to slide.")


def process_tile_cellpose(cur_model, input_image, cellpose_channels):
    """
    Run Cellpose model on a preprocessed tile image.
    Args:
        cur_model: Cellpose model object.
        input_image (ndarray): Preprocessed image (2, H, W) float32.
        cellpose_channels: Channel configuration for Cellpose.
    Returns:
        ndarray: Instance mask (H, W) with unique labels per cell.
    """
    input_image = np.array(input_image)
    cell_inst_map = cur_model.eval(input_image, channels=cellpose_channels, normalize=False, rescale=1.0, bsize=224,
                                   tile_overlap=0.2, niter=300,
                                   flow_threshold=0.4)[0]
    return cell_inst_map


def main(stop=False):
    """
    Entry point for running the Cellpose-MIKAIA integration pipeline.
    Args:
        stop (bool): If True, waits for user input before continuing (for debugging).
    """
    if stop:
        print(sys.argv[1])
        input("Press ENTER when you have copied the new path...")
        exit(0)

    slide_service_path = sys.argv[1]
    ss = miaapi.SlideService(slide_service_path)
    cellpose_weights = "YOUR_CELLPOSE_WEIGHTS_PATH"  # Replace with your Cellpose model weights path
    cellpose_mikaia_simple_pipeline(cur_slide_service=ss, checkpoint_path=cellpose_weights, cellpose_channels=None,
                                    input_width_px=2048, scale_factor=1)

if __name__ == "__main__":
    main()

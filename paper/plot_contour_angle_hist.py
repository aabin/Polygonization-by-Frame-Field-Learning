import argparse
import fnmatch
import os

import random
import matplotlib.pyplot as plt

import numpy as np
import shapely.geometry
import shapely.affinity
import skimage.io
import skimage.measure
from matplotlib.ticker import EngFormatter, StrMethodFormatter
from tqdm import tqdm

from functools import partial

from lydorn_utils import python_utils, math_utils
from lydorn_utils import print_utils

from frame_field_learning import save_utils, viz_utils


def compute_polygon_angles(polygon):
    # --- Rotate polygon so that main axis is aligned with the x-axis
    min_rot_rect = polygon.minimum_rotated_rectangle
    min_rot_rect_contour = np.array(min_rot_rect.exterior.coords[:])
    min_rot_rect_edges = min_rot_rect_contour[1:] - min_rot_rect_contour[:-1]
    min_rot_rect_norms = np.linalg.norm(min_rot_rect_edges, axis=1)
    max_norms_index = np.argmax(min_rot_rect_norms)
    longest_edge = min_rot_rect_edges[max_norms_index]
    main_angle = np.angle(longest_edge[0] + 1j*longest_edge[1])
    polygon = shapely.affinity.rotate(polygon, -main_angle, use_radians=True)
    # ---

    # min_rot_rect = polygon.minimum_rotated_rectangle
    # plt.plot(*polygon.exterior.xy)
    # plt.plot(*min_rot_rect.exterior.xy)
    # plt.gca().set_aspect('equal', adjustable='box')
    # plt.show()
    
    contour = np.array(polygon.exterior)
    edges = contour[1:] - contour[:-1]
    edges = edges[:, 1] + 1j * edges[:, 0]
    angles = np.angle(edges)
    angles[angles < 0] += np.pi  # Don't care about direction of edge

    return angles


def get_angles(background_filepath, mask_filepath, level=0.5, tol=0.1):
    # Read images
    bg_image = skimage.io.imread(background_filepath) / 255
    mask = skimage.io.imread(mask_filepath) / 255

    # Compute contours
    contours = skimage.measure.find_contours(mask, level, fully_connected='low', positive_orientation='high')
    polygons = [shapely.geometry.Polygon(contour[:, ::-1]) for contour in contours]
    # Filter out really small polylines
    polygons = [polygon for polygon in polygons if 2 < polygon.area]
    # Simplify
    polygons = [polygon.simplify(tol, preserve_topology=True) for polygon in polygons]

    # fig = plt.figure()
    # ax = fig.addsubplot(111)
    # ax.imshow(bg_image)
    # for contour in contours:
    #     ax.plot(contour[:, 1], contour[:, 0], color="blue")
    # ax.show()

    # --- Plot polygons on image
    minx = 1084
    miny = 391+256
    maxx = minx+1024
    maxy = miny+256
    box = shapely.geometry.box(minx, miny, maxx - 1, maxy - 1)
    bg_image = bg_image[miny:maxy, minx:maxx]
    # polygons_collection = shapely.geometry.GeometryCollection(polygons)
    # cropped_multipolygon = polygons_collection.intersection(box)
    cropped_polygons = []
    for poly in polygons:
        cropped_polygon = poly.intersection(box)
        if cropped_polygon.geom_type == "Polygon" and not cropped_polygon.is_empty:
            cropped_polygon = shapely.affinity.translate(cropped_polygon, xoff=-minx, yoff=-miny)
            cropped_polygons.append(cropped_polygon)
    out_filepath = os.path.splitext(mask_filepath)[0] + ".pdf"
    viz_utils.save_poly_viz(bg_image, cropped_polygons, out_filepath, linewidths=10, markersize=10, alpha=0.5, draw_vertices=True)
    # ---

    # Compute angles
    contours_angles = [compute_polygon_angles(polygon) for polygon in polygons]

    angles = np.concatenate(contours_angles)
    relative_degrees = angles * 180 / np.pi
    return relative_degrees


def plot_contour_angle_hist(background_filepath, list_info, level=0.5, tol=0.1):
    legend = []
    start = 0
    stop = 180
    bin_count = 100
    bin_edges = np.linspace(start, stop, bin_count + 1)
    bin_width = (stop - start) / bin_count
    bars_per_bin = len(list_info)
    bin_width_per_bar = bin_width / bars_per_bin  # the width of the bars
    for i, info in enumerate(list_info):
        degrees = get_angles(background_filepath, info["mask_filepath"], level, tol)
        hist, bin_edges = np.histogram(degrees, bins=bin_edges)
        freq = hist / np.sum(hist)
        # plt.bar(bin_edges[1:] + (i - bars_per_bin//2)*bin_width_per_bar - bin_width_per_bar/2, freq, width=bin_width_per_bar, alpha=1.0)
        plt.bar(bin_edges[1:] - bin_width/2, freq, width=bin_width, alpha=0.5, label=info["name"])
        # legend.append(info["name"])

    plt.title("Histogram of relative contour angles")
    plt.xlabel("Relative angle")
    plt.ylabel("Freq")
    plt.gca().xaxis.set_major_formatter(StrMethodFormatter(u"{x:.0f}°"))
    plt.legend(loc="upper left")
    plt.xlim(0, 180)
    plt.savefig("histogram_of_relative_contour_angles.pdf", transparent=True)
    plt.show()


def main():
    background_filepath = "inria_dataset_test_sample.jpg"

    list_info = [
        {
            "name": "ICTNet",
            "mask_filepath": "inria_dataset_test_sample_result.ictlab.jpg"
        },
        {
            "name": "Ours",
            "mask_filepath": "inria_dataset_test_sample_result.ours.tif"
        },
    ]

    plot_contour_angle_hist(background_filepath, list_info, tol=1)


if __name__ == '__main__':
    main()

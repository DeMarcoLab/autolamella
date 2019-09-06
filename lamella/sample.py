import matplotlib
import matplotlib.pyplot as plt

from autoscript_sdb_microscope_client.structures import (
    GrabFrameSettings,
    Rectangle,
    Point,
)

from lamella.autoscript import FibsemPosition
from lamella.display import quick_plot
from lamella.interactive import InteractiveRectangle


class Lamella:
    """Class for lamella samples."""

    def __init__(self, microscope=None):
        self.image = None
        self.sem_image = None
        self.custom_milling_depth = None
        self.milling_rois = None
        self.pixel_size = None
        self.fibsem_position = None
        self.fiducial_image = None
        self.fiducial_reduced_area = None
        self.original_feature_center = None
        self.fiducial_coord_realspace = None
        self.fiducial_coord_relative = None
        self.fiducial_coord_pixels = None
        self.center_coord_realspace = None
        self.fiducial_image_relative_size = None
        self.original_image = None
        self.original_image_cropped = None
        self.reference_image = None
        if microscope:
            self.image = self.set_image(microscope)
            self.pixel_size = self.set_pixel_size()
            self.fibsem_position = self.set_fibsem_position(microscope)

    def set_image(self, microscope):
        microscope.imaging.set_active_view(2)  # ion beam view
        self.image = microscope.imaging.get_image()
        try:
            self.set_pixel_size()
        except AttributeError:
            pass
        return self.image

    def set_sem_image(self, microscope, settings):
        microscope.imaging.set_active_view(1)  # SEM beam view
        camera_settings = GrabFrameSettings(
            reduced_area=Rectangle(0, 0, 1, 1),
            resolution=settings["imaging"]["resolution"],
        )
        self.sem_image = microscope.imaging.grab_frame(camera_settings)
        microscope.imaging.set_active_view(2)  # Restore ion beam view
        return self.sem_image

    def set_pixel_size(self):
        if self.image is not None:
            self.pixel_size = self.image.metadata.binary_result.pixel_size
            return self.image.metadata.binary_result.pixel_size

    def set_fibsem_position(self, microscope):
        self.fibsem_position = FibsemPosition(microscope)
        return self.fibsem_position

    def set_fiducial(
        self,
        image,
        coord_realspace,
        coord_relative,
        coord_pixels,
        fiducial_reduced_area,
    ):
        self.fiducial_image = image
        self.fiducial_coord_realspace = coord_realspace
        self.fiducial_coord_relative = coord_relative
        self.fiducial_coord_pixels = coord_pixels
        self.fiducial_reduced_area = fiducial_reduced_area
        self.original_feature_center = Point(x=0, y=0)

    def set_center(self, image, settings):
        fig, ax = quick_plot(image)
        roi_size_x = settings["lamella"]["lamella_width"]
        roi_size_y = (2 * settings["lamella"]["total_cut_height"]) + settings[
            "lamella"
        ]["lamella_height"]
        pixelsize_x = image.metadata.binary_result.pixel_size.x
        field_of_view_x = [
            -(image.width * pixelsize_x) / 2,
            +(image.width * pixelsize_x) / 2,
        ]
        field_of_view_y = [
            -(image.height * pixelsize_x) / 2,
            +(image.height * pixelsize_x) / 2,
        ]
        central_lamella_height = settings["lamella"]["lamella_height"]
        buffer = settings["fiducial"]["min_distance_from_lamella"]
        # display fiducial marker position
        pixelsize_x = image.metadata.binary_result.pixel_size.x
        fiducial_size_x = settings["fiducial"]["fiducial_length"]
        fiducial_size_y = settings["fiducial"]["fiducial_length"]
        x_coord_existing_patch = self.fiducial_coord_realspace[0] - (
            fiducial_size_x / 2
        )
        y_coord_existing_patch = self.fiducial_coord_realspace[1] - (
            fiducial_size_y / 2
        )
        existing_fiducial = matplotlib.patches.Rectangle(
            [x_coord_existing_patch, y_coord_existing_patch],
            settings["fiducial"]["fiducial_length"],
            settings["fiducial"]["fiducial_length"],
            fill=False,
            color="y",
        )
        # select lamella position
        myfig = InteractiveRectangle(
            fig,
            ax,
            roi_size_x=roi_size_x,
            roi_size_y=roi_size_y,
            fov_x=field_of_view_x,
            fov_y=field_of_view_y,
            central_lamella_height=central_lamella_height,
            existing_fiducial=existing_fiducial,
            min_distance_from_lamella=buffer,
        )
        myfig.show()
        self.center_coord_realspace = myfig.coords
        return self.center_coord_realspace

    def set_custom_milling_depth(self):
        message = (
            "If you want a custom milling depth for the LAMELLA "
            "enter it here in meters, else- slam on ENTER:\n"
        )
        custom_depth = input(message)
        if custom_depth == "":
            return
        else:
            try:
                custom_depth = float(custom_depth)
            except ValueError as e:
                print(e)
                custom_depth = input(message)
                custom_depth = float(custom_depth)
            self.custom_milling_depth = custom_depth
            return self.custom_milling_depth

    def save_matplotlib_figure_with_overlays(self, settings, output_filename):
        fig, ax = quick_plot(self.image)
        pixelsize_x = self.image.metadata.binary_result.pixel_size.x
        width_fiducial = (
            settings["fiducial"]["fiducial_length"] * self.image.width * pixelsize_x
        )
        height_fiducial = width_fiducial
        x_fiducial = self.fiducial_coord_realspace[0] - (width_fiducial / 2)
        y_fiducial = self.fiducial_coord_realspace[1] - (height_fiducial / 2)
        rect_fiducial = matplotlib.patches.Rectangle(
            [x_fiducial, y_fiducial],
            width_fiducial,
            height_fiducial,
            fill=False,
            color="r",
            linewidth=2,
        )
        ax.add_artist(rect_fiducial)

        width_lamella = settings["lamella"]["lamella_width"]
        height_lamella = settings["lamella"]["lamella_height"]
        x_lamella = self.center_coord_realspace[0] - (width_lamella / 2)
        y_lamella = self.center_coord_realspace[1] - (height_lamella / 2)
        rect_lamella = matplotlib.patches.Rectangle(
            [x_lamella, y_lamella],
            width_lamella,
            height_lamella,
            fill=False,
            color="g",
            linewidth=2,
        )
        ax.add_artist(rect_lamella)
        plt.savefig(output_filename)
        return fig, ax

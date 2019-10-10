import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from tkinter import Tk, filedialog

from autolamella.display import quick_plot


def ask_user(message, default=None):
    """Ask the user a question and return True if they say yes.

    Parameters
    ----------
    message : str
        The question to ask the user.
    default : str, optional
        If the user presses Enter without typing an answer,
        the default indicates how to interpret this.
        Choices are 'yes' or 'no'. The efault is None.

    Returns
    -------
    bool
        Returns True if the user answers yes, and false if they answer no.
    """
    yes = ["yes", "y"]
    no = ["no", "n"]
    if default:
        if default.lower() == "yes":
            yes.append("")
        elif default.lower() == "no":
            no.append("")
    all_posiible_responses = yes + no
    user_response = "initial non-empty string"
    while user_response not in all_posiible_responses:
        user_response = input(message)
        if user_response.lower() in yes:
            return True
        elif user_response.lower() in no:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def choose_directory():
    """Ask the user to create or select an EMPTY directory with Tkinter.

    Returns
    -------
    str
        Path to directory for output files.
    """
    print("Create a new EMPTY directory to store your output images.")
    root = Tk()
    save_directory = filedialog.askdirectory()
    while os.listdir(save_directory):  # while loop breaks for empty directory
        save_directory = filedialog.askdirectory()
    root.destroy()
    return save_directory


def select_point(image):
    """Return location of interactive user click on image.

    Parameters
    ----------
    image : AdornedImage or 2D numpy array.

    Returns
    -------
    coords
          Coordinates of last point clicked in the image.
          Coordinates are in x, y format.
          Units are the same as the matplotlib figure axes.
    """
    fig, ax = quick_plot(image)
    coords = []

    def on_click(event):
        print(event.ydata, event.xdata)
        coords.append(event.ydata)
        coords.append(event.xdata)

    fig.canvas.mpl_connect("button_press_event", on_click)
    plt.show()
    return np.flip(coords[-2:], axis=0)  # coordintes in x, y format


def _rectangles_overlap(bottomleft_1, topright_1, bottomleft_2, topright_2):
    """Compare two rectangles and return True if they are overlapping.

    Parameters
    ----------
    bottomleft_1 : listlike, float
        x, y coordinate of bottom left corner of rectangle 1.
    topright_1 : listlike, float
        x, y coordinate of top right corner of rectangle 1.
    bottomleft_2 : listlike, float
        x, y coordinate of bottom left corner of rectangle 2.
    topright_2 : listlike, float
        x, y coordinate of top right corner of rectangle 2.

    Returns
    -------
    boolean
        True if rectangles are overlapping, False if they do not overlap.
    """
    # check if bottom_left_1 is above top_right_2
    if bottomleft_1[1] > topright_2[1]:
        return False
    # check if bottom_left_2 is above top_right_1
    elif bottomleft_2[1] > topright_1[1]:
        return False
    # check if top_right_1 is to the left of bottom_left_2
    elif topright_1[0] < bottomleft_2[0]:
        return False
    # check if top_right_2 is to the left of bottom_left_1
    elif topright_2[0] < bottomleft_1[0]:
        return False
    # else, rectangles are overlapping
    else:
        return True


class InteractiveRectangle(object):
    def __init__(
        self,
        fig,
        ax,
        roi_size_x=1e-6,
        roi_size_y=1e-6,
        fov_x=None,
        fov_y=None,
        central_lamella_height=None,
        existing_fiducial=None,
        min_distance_from_lamella=0.0,
    ):
        """Interactive tool for the user to click and set ROI position.

        Parameters
        ----------
        fig : matplotlib figure object
            Figure displaying ion beam image on real space axes.
        ax : matplotlib axes object
            Figure axes must be in real space units.
        roi_size_x : float, optional
            The size in real space of the ROI in x, by default 1e-6
        roi_size_y : float, optional
            The size in real space of the ROI in y, by default 1e-6
        fov_x : listlike, float, optional
            Field of view minimum and maximum in x, by default None
        fov_y : listlike, float, optional
            Field of view minimum and maximum in y, by default None
        central_lamella_height : float, optional
            Height of lamella region, by default None
        existing_fiducial : Matplotlib rectangle patch, optional
        min_distance_from_lamella : float, optional
            Separation between fiducial and lamella milling in real space,
            by default 0.
        """
        self.fig = fig
        self.ax = ax
        self.roi_size_x = roi_size_x
        self.roi_size_y = roi_size_y
        self.field_of_view_x = fov_x
        self.field_of_view_y = fov_y
        self.central_lamella_height = central_lamella_height
        self.buffer = min_distance_from_lamella
        self.existing_fiducial = existing_fiducial
        self.coords = []

        self.rect = matplotlib.patches.Rectangle((0, 0), 0, 0, fill=False, color="y")
        self.ax.add_artist(self.rect)
        if central_lamella_height:
            self.rect_lamella = matplotlib.patches.Rectangle(
                (0, 0), 0, 0, fill=False, color="c"
            )
            self.ax.add_artist(self.rect_lamella)
        self.ax.set_title("Click to set the ROI marker")
        if existing_fiducial:
            self.ax.add_artist(existing_fiducial)
        self.fig.canvas.mpl_connect("button_press_event", self.on_click)

    def on_click(self, event):
        if event.inaxes is None:
            return
        # Ensure we are not too close to the edge
        if self.field_of_view_x:
            if (event.xdata - (self.roi_size_x / 2)) <= self.field_of_view_x[0]:
                print("Too close to the edge, please reselect.")
                return
            elif (event.xdata + (self.roi_size_x / 2)) >= self.field_of_view_x[1]:
                print("Too close to the edge, please reselect.")
                return
        if self.field_of_view_y:
            if (event.ydata - (self.roi_size_y / 2)) <= self.field_of_view_y[0]:
                print("Too close to the edge, please reselect.")
                return
            elif (event.ydata + (self.roi_size_y / 2)) >= self.field_of_view_y[1]:
                print("Too close to the edge, please reselect.")
                return
        print(event.xdata, event.ydata)
        self.coords = [event.xdata, event.ydata]
        self.rect.set_x(event.xdata - (self.roi_size_x / 2))
        self.rect.set_y(event.ydata - (self.roi_size_y / 2))
        self.rect.set_width(self.roi_size_x)
        self.rect.set_height(self.roi_size_y)
        # Also display the lamella itself, if appropriate
        if self.central_lamella_height:
            self.rect_lamella.set_x(event.xdata - (self.roi_size_x / 2))
            self.rect_lamella.set_y(event.ydata - (self.central_lamella_height / 2))
            self.rect_lamella.set_width(self.roi_size_x)
            self.rect_lamella.set_height(self.central_lamella_height)
        # # Ensure there is sufficent separation between the lamella & fiducial
        if self.existing_fiducial is not None:
            bottom_left_1 = np.array(self.existing_fiducial.xy) - self.buffer
            top_right_1 = np.array(self.existing_fiducial.xy) + np.array(
                [
                    self.existing_fiducial.get_width() + self.buffer,
                    self.existing_fiducial.get_height() + self.buffer,
                ]
            )
            bottom_left_2 = self.rect_lamella.xy
            top_right_2 = np.array(self.rect_lamella.xy) + np.array(
                [self.rect_lamella.get_width(), self.rect_lamella.get_height()]
            )
            if _rectangles_overlap(
                bottom_left_1, top_right_1, bottom_left_2, top_right_2
            ):
                print("Lamella too close to the fiducial marker")
                return

        self.fig.canvas.draw()

    def show(self):
        plt.show()

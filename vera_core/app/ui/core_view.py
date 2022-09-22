import matplotlib.pyplot as plt
import numpy as np

from trame.ui.html import DivLayout

from trame.widgets import matplotlib

OPTION = {
    "name": "core_view",
    "label": "Core View",
    "icon": "mdi-chart-donut-variant",
}

plt.set_cmap("jet")


def initialize(server, vera_out_file):
    state, ctrl = server.state, server.controller

    # Create the figure and axes we will use
    fig, ax = plt.subplots()
    colorbar = None

    if OPTION not in state.grid_options:
        state.grid_options.append(OPTION)

    def figure_size():
        if state.figure_size is None:
            return {}

        dpi = state.figure_size.get("dpi")
        rect = state.figure_size.get("size")
        w_inch = rect.get("width") / dpi
        h_inch = rect.get("height") / dpi

        # FIXME: the height isn't working. It is always 0.

        return {
            "figsize": (w_inch, h_inch),
            "dpi": dpi,
        }

    def create_image(img):
        figsize_dict = figure_size()
        if "figsize" in figsize_dict:
            width, height = figsize_dict["figsize"]
            fig.set_width(width)
            fig.set_height(height)

        if "dpi" in figsize_dict:
            dpi = figsize_dict["dpi"]
            fig.set_depi(dpi)

        axes_image = ax.imshow(img)

        nonlocal colorbar
        if colorbar:
            colorbar.remove()

        colorbar = fig.colorbar(axes_image)
        return fig

    # A cache of core images.
    cached_core_images = {}

    @state.change("figure_size", "selected_array", "selected_layer")
    def update_core_view(selected_array, selected_layer, **kwargs):
        selected_layer = int(selected_layer)

        cache_key = (selected_layer, selected_array)
        if cache_key in cached_core_images:
            # Shortcut if we have a cache. We might still need to redraw
            # if the figure size was updated.
            image_data = cached_core_images[cache_key]
            ctrl.update_figure(create_image(image_data))
            return

        array = getattr(vera_out_file.active_state, selected_array)

        # Load the layer and swap axes for faster indexing
        layer_array = array[:, :, selected_layer].swapaxes(0, 2)
        layer_array = layer_array.swapaxes(1, 2)

        reduced_core_map = vera_out_file.core.reduced_core_map
        map_shape = reduced_core_map.shape

        # Create the full sized image
        image_shape = (map_shape[0] * array.shape[0], map_shape[1] * array.shape[1])
        image = np.empty(image_shape, dtype=array.dtype)

        # Populate it with the arrays
        for i in range(reduced_core_map.shape[0]):
            i_slice = slice(i * array.shape[0], (i + 1) * array.shape[0])
            for j in range(reduced_core_map.shape[1]):
                j_slice = slice(j * array.shape[1], (j + 1) * array.shape[1])
                index = reduced_core_map[i, j]
                if index == 0:
                    # Empty
                    image[i_slice, j_slice] = np.nan
                    continue

                image[i_slice, j_slice] = layer_array[index - 1]

        if selected_array == "pin_powers":
            # Make anywhere that is zero be nan
            image[np.where(image == 0)] = np.nan

        # Only allow one image in the cache
        MAX_ITEMS_IN_CACHE = 1
        while len(cached_core_images) >= MAX_ITEMS_IN_CACHE:
            cached_core_images.pop(next(iter(cached_core_images)))

        cached_core_images[cache_key] = image

        ctrl.update_figure(create_image(image))

    with DivLayout(server, template_name="core_view"):
        # FIXME: why can't we use trame.SizeObserver() here?
        # with trame.SizeObserver("figure_size"):
        html_figure = matplotlib.Figure(style="position: absolute")
        ctrl.update_figure = html_figure.update
# -*- coding: utf-8 -*-
"""
Interface to the spirit web view used in the plotting tool.
"""

import json
import numpy as np
from IPython.core.display import display, HTML, Javascript


def setup():
    """
    Initialize the HTML object which is the canvas for the spirit spin view
    """
    return HTML('''
    <div id="vfr_frame_wrapper">
    </div>
    <script>
        window.addEventListener("message", (event) => {
          if (event.origin !== "https://florianrhiem.iffgit.fz-juelich.de")
            return;
          window.vfr_iframe = event.source;
        }, false);
        var frame_wrapper = document.getElementById("vfr_frame_wrapper");
        var iframe_url = "https://florianrhiem.iffgit.fz-juelich.de/VFRendering/notebook_view/?origin=" + window.location.origin;
        frame_wrapper.innerHTML = '<iframe src="' + iframe_url + '" style="width: 100%; height:600px; border: 1px solid black;"></iframe>';
    </script>
    ''')


def update(positions, directions, rectilinear=True):
    """
    Update the spirit spin view HTML object with new positions and directions.
    """
    n_cells = positions.shape[:-1][::-1]
    n = int(np.prod(positions.shape[:-1]))
    positions = positions.reshape(np.prod(positions.shape))
    directions = directions.reshape(np.prod(directions.shape))
    message = {
        'function': 'update_state',
        'state': {
            'n': n,
            'n_cells': n_cells,
            'rectilinear': 1 if rectilinear else 0,
            'positions': positions.tolist(),
            'directions': directions.tolist()
        }
    }
    display(Javascript(f'''
    window.vfr_iframe.postMessage({json.dumps(message)}, "https://florianrhiem.iffgit.fz-juelich.de");
    '''),
            clear=True)

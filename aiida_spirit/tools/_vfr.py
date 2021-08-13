# -*- coding: utf-8 -*-
"""
Interface to the spirit web view used in the plotting tool.
"""

import json
import secrets
import numpy as np
from IPython.core.display import display, HTML, Javascript

_vfr_frame_id_mapping = {}
_next_frame_id = 1
_frame_id_suffix = secrets.token_hex(32)

# pylint: disable=line-too-long,global-statement


def setup(vfr_frame_id=''):
    """Create a frame in the jupyter ntoebook to into which the spins are shown."""
    global _vfr_frame_id_mapping, _next_frame_id, _frame_id_suffix
    if vfr_frame_id not in _vfr_frame_id_mapping:
        _vfr_frame_id_mapping[vfr_frame_id] = 'vfr_frame_wrapper_' + str(
            _next_frame_id) + '_' + _frame_id_suffix
        _next_frame_id += 1
    vfr_frame_id = _vfr_frame_id_mapping[vfr_frame_id]
    unique_id = secrets.token_hex(32)
    return HTML('''
    <div id="''' + vfr_frame_id + '''" name="''' + vfr_frame_id +
                '''" data-vfr-id="''' + unique_id + '''">
    </div>
    <script>
        window.addEventListener("message", (event) => {
          if (event.origin !== "https://judftteam.github.io") {
            return;
          }
          if (event.data['frame_id'] !== "''' + vfr_frame_id + '''") {
            return;
          }
          if (typeof window.vfr_iframe === 'undefined') {
            window.vfr_iframe = {};
          }
          window.vfr_iframe["''' + vfr_frame_id + '''"] = event.source;
        }, false);
        /* remove duplicate frame wrappers */
        var existing_frame_wrappers = document.getElementsByName("''' +
                vfr_frame_id + '''");
        if (existing_frame_wrappers.length > 1) {
            for (var i = 0; i < existing_frame_wrappers.length; i++) {
                console.log(existing_frame_wrappers[i].dataset.vfrId);
                if (existing_frame_wrappers[i].dataset.vfrId !== "''' +
                unique_id + '''") {
                    console.log(existing_frame_wrappers[i]);
                    existing_frame_wrappers[i].remove();
                }
            }
        }
        var frame_wrapper = document.getElementById("''' + vfr_frame_id +
                '''");
        var iframe_url = "https://judftteam.github.io/aiida-spirit/vfr_notebook_view/?origin=" + window.location.origin + "&frame_id='''
                + vfr_frame_id + '''";
        frame_wrapper.innerHTML = '<iframe src="' + iframe_url + '" style="width: 100%; height:600px; border: 1px solid black;"></iframe>';
    </script>
    ''')


def update(positions, directions, rectilinear=True, vfr_frame_id=''):
    """Update the spins in the frame."""
    global _vfr_frame_id_mapping
    vfr_frame_id = _vfr_frame_id_mapping[vfr_frame_id]
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
    window.vfr_iframe['{vfr_frame_id}'].postMessage({json.dumps(message)}, "https://judftteam.github.io");
    '''),
            clear=True)

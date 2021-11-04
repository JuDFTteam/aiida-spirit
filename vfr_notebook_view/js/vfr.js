"use strict";

function VFRendering(Module, canvas, finishedCallback)
{
    this._canvas = canvas;

    this._options = {};
    this._mergeOptions(this._options, VFRendering.defaultOptions);

    this._createVFRenderingBindings(Module);

    this.isTouchDevice = 'ontouchstart' in document.documentElement;
    this._options.useTouch = (VFRendering.defaultOptions.useTouch && this.isTouchDevice);
    if (this.isTouchDevice) {
        this._lastPanDeltaX = 0;
        this._lastPanDeltaY = 0;
        var mc = new Hammer.Manager(canvas, {});
        mc.add(new Hammer.Pan({ direction: Hammer.DIRECTION_ALL, threshold: 0, pointers: 1}));
        mc.on("pan", this._handlePan.bind(this));
        mc.add(new Hammer.Pinch({}));
        mc.on("pinchstart pinchin pinchout pinchmove pinchend", this._handlePinch.bind(this));
    }
    this._mouseDown = false;
    this._lastMouseX = null;
    this._lastMouseY = null;

    var supportsPassive = false;
    try {
      window.addEventListener("test", null, Object.defineProperty({}, 'passive', {
        get: function () { supportsPassive = true; }
      }));
    } catch(e) {}
    var wheelOpt = supportsPassive ? { passive: false } : false;
    var wheelEvent = 'onwheel' in document.createElement('div') ? 'wheel' : 'mousewheel';

    canvas.addEventListener(wheelEvent,         this._handleMouseScroll.bind(this), wheelOpt);
    canvas.addEventListener('DOMMouseScroll',   this._handleMouseScroll.bind(this), false);
    canvas.addEventListener('mousedown',        this._handleMouseDown.bind(this));
    canvas.addEventListener('mousemove',        this._handleMouseMove.bind(this));
    document.addEventListener('mouseup',        this._handleMouseUp.bind(this));

    this.create_state();
    this.initialize();
    this.updateGeometry();
    this.updateDirections();
    this.recenter_camera();
    this.draw();
}


VFRendering.defaultOptions = {};
VFRendering.defaultOptions.allowCameraMovement = true;
VFRendering.defaultOptions.useTouch = true;

VFRendering.prototype.updateOptions = function(options)
{
    var changedOptions = [];
    for (var option in options) {
        if (this._options.hasOwnProperty(option)) {
            if (this._options[option] !== options[option]) {
                this._options[option] = options[option];
                changedOptions.push(option);
            }
        } else {
            console.warn("VFRendering does not recognize option '" + option +"'.");
        }
    }
    if (changedOptions.length == 0) {
        return;
    }
};

VFRendering.prototype._mergeOptions = function(options, defaultOptions) {
    this._options = {};
    for (var option in defaultOptions) {
        this._options[option] = defaultOptions[option];
    }
    for (var option in options) {
        if (defaultOptions.hasOwnProperty(option)) {
            this._options[option] = options[option];
        } else {
            console.warn("VFRendering does not recognize option '" + option +"'.");
        }
    }
};


// ------------------------------------------------

VFRendering.prototype._createVFRenderingBindings = function(Module)
{
    Module.create_state = Module.cwrap('create_state', 'number', []);
    VFRendering.prototype.create_state = function() {
        this._state = Module.create_state();
    };

    Module.initialize = Module.cwrap('initialize', null, ['number']);
    VFRendering.prototype.initialize = function() {
        Module.initialize(this._state);
    };

    Module.draw = Module.cwrap('draw');
    VFRendering.prototype._draw = function() {
        Module.draw();
    };

    // Module.set_camera = Module.cwrap('set_camera');
    VFRendering.prototype.set_camera = function(position, center, up) {
        position = new Float32Array(position);
        var position_ptr = Module._malloc(position.length * position.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(position, position_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        center = new Float32Array(center);
        var center_ptr = Module._malloc(center.length * center.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(center, center_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        up = new Float32Array(up);
        var up_ptr = Module._malloc(up.length * up.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(up, up_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        Module._set_camera(position_ptr, center_ptr, up_ptr);
    };

    VFRendering.prototype.align_camera = function(direction, up) {
        direction = new Float32Array(direction);
        var direction_ptr = Module._malloc(direction.length * direction.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(direction, direction_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        up = new Float32Array(up);
        var up_ptr = Module._malloc(up.length * up.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(up, up_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        Module._align_camera(direction_ptr, up_ptr);
    };

    VFRendering.prototype.recenter_camera = function() {
        Module._recenter_camera();
    };

    Module.set_background = Module.cwrap('set_background', null, ['number']);
    VFRendering.prototype.set_background = function(colour) {
        colour = new Float32Array(colour);
        var colour_ptr = Module._malloc(colour.length * colour.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(colour, colour_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        Module.set_background(colour_ptr);
    };

    Module.set_vertical_field_of_view = Module.cwrap('set_vertical_field_of_view', null, ['number']);

    Module.set_coordinate_system = Module.cwrap('set_coordinate_system', null, ['number', 'number']);
    VFRendering.prototype.set_coordinatesystem = function(show, position) {
        Module.set_coordinate_system(this._state, show, position);
    };

    Module.set_miniview = Module.cwrap('set_miniview', null, ['number', 'number']);
    VFRendering.prototype.set_miniview = function(show, position) {
        Module.set_miniview(this._state, show, position);
        Module._draw();
    }

    Module.set_boundingbox_colour = Module.cwrap('set_boundingbox_colour', null, ['number', 'number', 'number']);
    VFRendering.prototype.set_boundingbox_colour = function(colour) {
        colour = new Float32Array(colour);
        var colour_ptr = Module._malloc(colour.length * colour.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(colour, colour_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        Module.set_boundingbox_colour(colour_ptr);
    };

    Module.set_boundingbox = Module.cwrap('set_boundingbox', null, ['number', 'number', 'number']);
    VFRendering.prototype.set_boundingbox = function(show, line_width) {
        Module.set_boundingbox(this._state, show, line_width);
    };

    Module.set_dots = Module.cwrap('set_dots', null, ['number', 'number']);
    VFRendering.prototype.set_dots = function(show) {
        Module.set_dots(this._state, show);
    };

    Module.set_arrows = Module.cwrap('set_arrows', null, ['number', 'number']);
    VFRendering.prototype.set_arrows = function(show) {
        Module.set_arrows(this._state, show);
    };

    Module.set_spheres = Module.cwrap('set_spheres', null, ['number', 'number']);
    VFRendering.prototype.set_spheres = function(show) {
        Module.set_spheres(this._state, show);
    };

    Module.set_boxes = Module.cwrap('set_boxes', null, ['number', 'number']);
    VFRendering.prototype.set_boxes = function(show) {
        Module.set_boxes(this._state, show);
    };

    Module.set_surface = Module.cwrap('set_surface', null, ['number', 'number']);
    VFRendering.prototype.set_surface = function(show) {
        Module.set_surface(this._state, show);
    };

    Module.set_isosurface = Module.cwrap('set_isosurface', null, ['number', 'number']);
    VFRendering.prototype.set_isosurface = function(show) {
        Module.set_isosurface(this._state, show);
    };


    Module.update_state = Module.cwrap('update_state', null, ['number', 'number', 'number', 'number', 'number', 'number']);
    VFRendering.prototype.update_state = function(state) {
        var n = state.n;
        var n_cells = state.n_cells;
        var rectilinear = state.rectilinear;
        var positions = state.positions;
        var directions = state.directions;
        n_cells = new Float32Array(n_cells);
        var n_cells_ptr = Module._malloc(n_cells.length * n_cells.BYTES_PER_ELEMENT);
        Module.HEAP32.set(n_cells, n_cells_ptr/Module.HEAP32.BYTES_PER_ELEMENT);
        positions = new Float32Array(positions);
        var positions_ptr = Module._malloc(positions.length * positions.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(positions, positions_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        directions = new Float32Array(directions);
        var directions_ptr = Module._malloc(directions.length * directions.BYTES_PER_ELEMENT);
        Module.HEAPF32.set(directions, directions_ptr/Module.HEAPF32.BYTES_PER_ELEMENT);
        Module.update_state(this._state, n, n_cells_ptr, rectilinear, positions_ptr, directions_ptr);
        this.updateGeometry();
        this.updateDirections();
        /* Enable/Disable features restricted to rectilinear geometry */
        var bounding_box_toggle = $('#input-show-boundingbox');
        var surface_toggle = $('#input-show-surface');
        var isosurface_toggle = $('#input-show-isosurface');
        if (state.rectilinear) {
            bounding_box_toggle.prop('disabled', false);
            surface_toggle.prop('disabled', false);
            isosurface_toggle.prop('disabled', false);
        } else {
            if (bounding_box_toggle.prop('checked')) {
                bounding_box_toggle.prop('checked', false);
            }
            if (surface_toggle.prop('checked')) {
                surface_toggle.prop('checked', false);
            }
            if (isosurface_toggle.prop('checked')) {
                isosurface_toggle.prop('checked', false);
            }
            bounding_box_toggle.prop('disabled', true);
            surface_toggle.prop('disabled', true);
            isosurface_toggle.prop('disabled', true);
            this.set_boundingbox(false);
            this.set_surface(false);
            this.set_isosurface(false);
        }
    };

    // ----------------------- Functions

    VFRendering.prototype.draw = function() {
        var width = this._canvas.clientWidth;
        var height = this._canvas.clientHeight;
        this.drawWithResolution(width, height);
    }

    VFRendering.prototype.drawWithResolution = function(width, height) {
        this._canvas.width = width;
        this._canvas.height = height;
        Module._draw();
    }

    VFRendering.prototype.updateDirections = function() {
        Module._update_directions(this._state);
        Module._draw();
    }

    VFRendering.prototype.updateGeometry = function() {
        Module._update_geometry(this._state);
        Module._draw();
    }

    VFRendering.prototype.set_rendermode = function(mode) {
        Module._set_rendermode(mode);
        Module._draw();
    }

    VFRendering.prototype.updateVisibility = function(zRange) {
        Module._set_visibility(zRange[0], zRange[1]);
        Module._draw();
    }

    VFRendering.prototype.setVectorSphere = function(pointSizeRange) {
        Module._set_vectorsphere(pointSizeRange[0], pointSizeRange[1]);
        Module._draw();
    }

    VFRendering.prototype.setColormap = function(colormap) {
        var idx_cmap = 0;
        if( colormap == "hsv" )
        {
            idx_cmap = 0;
        }
        else if( colormap == "hue" )
        {
            idx_cmap = 1;
        }
        else if( colormap == "bluered" )
        {
            idx_cmap = 2;
        }
        else if( colormap == "bluegreenred" )
        {
            idx_cmap = 3;
        }
        else if( colormap == "bluewhitered" )
        {
            idx_cmap = 4;
        }
        else if( colormap == "red" )
        {
            idx_cmap = 5;
        }
        else if( colormap == "white" )
        {
            idx_cmap = 6;
        }
        else if( colormap == "gray" )
        {
            idx_cmap = 7;
        }
        else if( colormap == "black" )
        {
            idx_cmap = 8;
        }
        else if( colormap == "black" )
        {
            idx_cmap = 8;
        }
        Module._set_colormap(idx_cmap);
        Module._draw();
    }

    // ----------------------- Handlers

    VFRendering.prototype._handlePinch = function(event) {
        if (!this._options.useTouch) return;
        if (event.scale > 1) {
            Module._mouse_scroll(-0.3*event.scale);
        } else {
            Module._mouse_scroll(0.3/event.scale);
        }
        this.draw();
    };

    VFRendering.prototype._handlePan = function(event) {
        if (!this._options.useTouch) return;
        var deltaX = event.deltaX;
        var deltaY = event.deltaY;

        var prev = Module._malloc(2*Module.HEAPF32.BYTES_PER_ELEMENT);
        var na_ptr = prev+0*Module.HEAPF32.BYTES_PER_ELEMENT;
        var nb_ptr = prev+1*Module.HEAPF32.BYTES_PER_ELEMENT;
        Module.HEAPF32[na_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = this._lastPanDeltaX;
        Module.HEAPF32[nb_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = this._lastPanDeltaY;
        var current = Module._malloc(2*Module.HEAPF32.BYTES_PER_ELEMENT);
        var na_ptr = current+0*Module.HEAPF32.BYTES_PER_ELEMENT;
        var nb_ptr = current+1*Module.HEAPF32.BYTES_PER_ELEMENT;
        Module.HEAPF32[na_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = deltaX;
        Module.HEAPF32[nb_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = deltaY;

        if (event.isFinal) {
            this._lastPanDeltaX = 0;
            this._lastPanDeltaY = 0;
        } else {
            this._lastPanDeltaX = event.deltaX;
            this._lastPanDeltaY = event.deltaY;
        }

        Module._mouse_move(prev, current, 1);
        this.draw();
    };

    VFRendering.prototype._handleMouseDown = function(event) {
        if (this._options.useTouch) return;
        if (!this._options.allowCameraMovement) {
            return;
        }
        this._mouseDown = true;
        this._lastMouseX = event.clientX;
        this._lastMouseY = event.clientY;
    };

    VFRendering.prototype._handleMouseUp = function(event) {
        if (this._options.useTouch) return;
        this._mouseDown = false;
    };

    VFRendering.prototype._handleMouseMove = function(event) {
        if (this._options.useTouch) return;
        if (!this._options.allowCameraMovement) {
            return;
        }
        if (!this._mouseDown) {
            return;
        }
        var newX = event.clientX;
        var newY = event.clientY;

        var prev = Module._malloc(2*Module.HEAPF32.BYTES_PER_ELEMENT);
        var na_ptr = prev+0*Module.HEAPF32.BYTES_PER_ELEMENT;
        var nb_ptr = prev+1*Module.HEAPF32.BYTES_PER_ELEMENT;
        Module.HEAPF32[na_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = this._lastMouseX;
        Module.HEAPF32[nb_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = this._lastMouseY;
        var current = Module._malloc(2*Module.HEAPF32.BYTES_PER_ELEMENT);
        var na_ptr = current+0*Module.HEAPF32.BYTES_PER_ELEMENT;
        var nb_ptr = current+1*Module.HEAPF32.BYTES_PER_ELEMENT;
        Module.HEAPF32[na_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = newX;
        Module.HEAPF32[nb_ptr/Module.HEAPF32.BYTES_PER_ELEMENT] = newY;

        var movement_mode = 1;
        if (event.shiftKey) {
            movement_mode = 0;
        }
        Module._mouse_move(prev, current, movement_mode);
        this.draw();
        this._lastMouseX = newX;
        this._lastMouseY = newY;
    };

    VFRendering.prototype._handleMouseScroll = function(event) {
        if (this._options.useTouch) return;
        if (!this._options.allowCameraMovement) {
            return;
        }
        var scale = 1;
        if (event.shiftKey)
        {
            scale = 0.1;
        }
        var delta = Math.max(-1, Math.min(1, (event.wheelDelta || -event.detail)));
        Module._mouse_scroll(-delta*scale);
        this.draw();
        event.preventDefault();
    };
};

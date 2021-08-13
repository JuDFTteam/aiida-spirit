
$(document).ready(function()
{
    $('form').attr('onsubmit', 'return false;');
    var canvas = document.getElementById("webgl-canvas");

    Module_VFRendering().then(function(Module) {
        window.FS = Module.FS
        window.vfr = new VFRendering(Module, canvas);
    }).then(function()
    {
        $( window ).resize(function() {
            vfr.draw();
        });
        $('.collapse').on('hidden.bs.collapse', function () {
            vfr.draw();
        });
        $('.collapse').on('shown.bs.collapse', function () {
            vfr.draw();
        });
        $('#input-show-settings').on('change', function () {
            vfr.draw();
        });

        window.addEventListener('keydown', function(event) {
            var key = event.keyCode || event.which;
            if (key == 88) { // x
                vfr.align_camera([-1, 0, 0], [0, 0, 1]);
                vfr.draw();
            }
            else if (key == 89) { // y
                vfr.align_camera([0, 1, 0], [0, 0, 1]);
                vfr.draw();
            }
            else if (key == 90) { // z
                vfr.align_camera([0, 0, -1], [0, 1, 0]);
                vfr.draw();
            }
            // else{
            //     console.log('key code ' + key + ' was pressed!');
            // }
        });

        function update() {
        };

        // --------------------------

    function updateColormap() {
        var colormap = $("option:selected", $('#select-colormap'))[0].value;
            vfr.setColormap(colormap);
        }
        $('#select-colormap').on('change', updateColormap);
        updateColormap();

        function updateBackgroundColor() {
            var backgroundColor = $("option:selected", $('#select-backgroundcolor'))[0].value;
            var colors = {
                'white': [1.0, 1.0, 1.0],
                'gray': [0.5, 0.5, 0.5],
                'black': [0.0, 0.0, 0.0]
            };
            var boundingBoxColors = {
                'white': [0.0, 0.0, 0.0],
                'gray': [1.0, 1.0, 1.0],
                'black': [1.0, 1.0, 1.0]
            };
            vfr.set_background(colors[backgroundColor]);
            vfr.set_boundingbox_colour(boundingBoxColors[backgroundColor]);
            vfr.draw();
            // console.log("background update", colors[backgroundColor]);
        }
        $('#select-backgroundcolor').on('change', updateBackgroundColor);
        updateBackgroundColor();

        function updateRenderers() {
            var rendermode = $("option:selected", $('#select-rendermode'))[0].value;
            var show_miniview           = $('#input-show-miniview').is(':checked');
            var show_coordinatesystem   = $('#input-show-coordinatesystem').is(':checked');
            var show_boundingbox        = $('#input-show-boundingbox').is(':checked');
            var boundingbox_line_width  = 0;
            var show_dots               = $('#input-show-dots').is(':checked');
            var show_arrows             = $('#input-show-arrows').is(':checked');
            var show_spheres            = $('#input-show-spheres').is(':checked');
            var show_boxes              = $('#input-show-boxes').is(':checked');
            var show_isosurface         = $('#input-show-isosurface').is(':checked');
            var show_surface            = $('#input-show-surface').is(':checked');
            // console.log(rendermode);

            // var coordinateSystemPosition = JSON.parse($("option:selected", $('#select-coordinatesystem-position'))[0].value);
            // var miniViewPosition = JSON.parse($("option:selected", $('#select-miniview-position'))[0].value);
            var coordinateSystemPosition = $('#select-coordinatesystem-position')[0].selectedIndex;
            var miniViewPosition = $('#select-miniview-position')[0].selectedIndex;

            if( rendermode == "SYSTEM" )
            {
                vfr.set_rendermode(0);
            }
            else
            {
                vfr.set_rendermode(1);
            }

            vfr.set_miniview(show_miniview, miniViewPosition);
            vfr.set_coordinatesystem(show_coordinatesystem, coordinateSystemPosition);
            vfr.set_boundingbox(show_boundingbox, boundingbox_line_width);
            vfr.set_dots(show_dots);
            vfr.set_arrows(show_arrows);
            vfr.set_spheres(show_spheres);
            vfr.set_boxes(show_boxes);
            vfr.set_surface(show_surface);
            vfr.set_isosurface(show_isosurface);

            vfr.draw();
        }
        $('#select-rendermode').on('change', updateRenderers);
        $('#select-coordinatesystem-position').on('change', updateRenderers);
        $('#select-miniview-position').on('change', updateRenderers);
        $('#input-show-miniview').on('change', updateRenderers);
        $('#input-show-coordinatesystem').on('change', updateRenderers);
        $('#input-show-boundingbox').on('change', updateRenderers);
        $('#input-show-dots').on('change', updateRenderers);
        $('#input-show-arrows').on('change', updateRenderers);
        $('#input-show-spheres').on('change', updateRenderers);
        $('#input-show-boxes').on('change', updateRenderers);
        $('#input-show-surface').on('change', updateRenderers);
        $('#input-show-isosurface').on('change', updateRenderers);
        updateRenderers();

        $("#input-zrange-filter").slider();
        function updateZRangeFilter() {
            var zRange = $("#input-zrange-filter").slider('getValue');
            vfr.updateVisibility(zRange);
        }
        $('#input-zrange-filter').on('change', updateZRangeFilter);
        updateZRangeFilter();

        $("#input-spinspherewidget-pointsize").slider();
        function updateSpherePointSize() {
            var pointSizeRange = $("#input-spinspherewidget-pointsize").slider('getValue');
            vfr.setVectorSphere(pointSizeRange);
        }
        $('#input-spinspherewidget-pointsize').on('change', updateSpherePointSize);
        updateSpherePointSize();

        if (!VFRendering.isTouchDevice) {
            $('#input-use-touch')[0].disabled="disabled";
            $('#input-use-touch')[0].checked = false;
        }

        function updateUseTouch() {
            var useTouch = $('#input-use-touch')[0].checked;
            VFRendering.updateOptions({useTouch: useTouch});
        }
        $('#input-use-touch').on('change', updateUseTouch);


        $('#button-camera-x').on('click', function(e) {
            vfr.align_camera([-1, 0, 0], [0, 0, 1]);
            vfr.draw();
        });
        $('#button-camera-y').on('click', function(e) {
            vfr.align_camera([0, 1, 0], [0, 0, 1]);
            vfr.draw();
        });
        $('#button-camera-z').on('click', function(e) {
            vfr.align_camera([0, 0, -1], [0, 1, 0]);
            vfr.draw();
        });

        function downloadURI(uri, name) {
            var link = document.createElement("a");
            link.download = name;
            link.href = uri;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            delete link;
        }

        $('#button-screenshot').on('click', function(e) {
            var screenshot_width = document.getElementById('input-screenshot-width').value;
            var screenshot_height = document.getElementById('input-screenshot-height').value;
            if (screenshot_width && screenshot_height) {
                vfr.drawWithResolution(screenshot_width, screenshot_height);
                downloadURI(canvas.toDataURL(), "screenshot.png");
                vfr.draw();
            } else {
                alert("Please enter a valid screenshot resolution!");
            }
        });

        // ---------------------------------------------------------------------

        var url_string = window.location.href;
        var url = new URL(url_string);

        // Default camera
        vfr.set_camera([0, 0, 50], [0, 0, 0], [0, 1, 0]);

        // Visualisation
        updateRenderers();
        updateColormap();
    }
    ).then(function()
    {
        $('#div-load').hide();
    });
});

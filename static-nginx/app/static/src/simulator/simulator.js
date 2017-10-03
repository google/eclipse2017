'use strict';

/**
  Copyright 2017 Bret Lorimore, George Harder, Jacob Fenger.
  Licensed under the Apache License, Version 2.0 (the "License");

  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
*/

// EclipseSimulator namespace
var EclipseSimulator = {

    DEBUG: false,

    View: function(location)
    {
        this.svg_container  = $('#svg-container').get(0);
        this.background     = $('.background');
        this.mobile_mapcont = $('#mobile-map-container').get(0);
        this.loading        = $('#loading').get(0);
        this.controls       = $('#controls').get(0);
        this.sun            = $('#sun').get(0);
        this.moon           = $('#moon').get(0);
        this.upbutton       = $('#upbutton').get(0);
        this.downbutton     = $('#downbutton').get(0);
        this.mapbutton      = $('#mapbutton').get(0);
        this.speed_btn_slow = $('#speed-button-slow').get(0);
        this.speed_btn_fast = $('#speed-button-fast').get(0);
        this.speed_menu     = $('#speed-menu').get(0);
        this.speed_sel_btn  = $('#speed-menu-button').get(0);
        this.zoombutton     = $('#zoom').get(0);
        this.playbutton     = $('#play').get(0);
        this.slider         = $('#tslider').get(0);
        this.error_snackbar = $('#error-snackbar').get(0);
        this.slider_labels  = $('[id^=slabel]');
        this.mapcanvas      = $('#map-canvas').get(0);
        this.search_input   = $('#pac-input').get(0);
        this.topbar         = $('.floating-bar.top .inner').get(0);
        this.garbage_dump   = $('#garbage-dump').get(0);
        this.totality_label = $("#totality-label").get(0);

        this.map            = new google.maps.Map(this.mapcanvas, {
                                center: EclipseSimulator.DEFAULT_LOCATION_COORDS,
                                zoom: EclipseSimulator.GEOCODE_MAP_ZOOM,
                                streetViewControl: false,
                                clickableIcons: false
                            });

        this.map_visible    = false;
        this.search_box     = undefined;
        this.marker         = undefined;
        this.maps_place     = undefined;
        this.geocoder       = undefined;

        // Used in timezone computation
        this.place_id       = EclipseSimulator.DEFAULT_LOCATION_PLACE_ID;
        this.offset         = EclipseSimulator.DEFAULT_LOCATION_UTC_OFFSET;
        this.in_totality    = EclipseSimulator.DEFAULT_LOCATION_IN_TOTALITY;

        this.end_of_slider = false;

        // Sun/moon position in radians
        this.sunpos  = {x: 0, y: 0, r: 0.25 * Math.PI / 180, apparant_r: 0.34 * Math.PI / 180};
        this.moonpos = {x: 0, y: 0, r: 0.25 * Math.PI / 180};

        // Wide field of view in radians
        this.wide_fov = {
            // Max x fov is 140 degrees - will be set by first call to View.update_fov when the
            // simulator is in wide mode
            x: undefined,

            // Max y fov is 90 degrees
            y: undefined,

            // Desired y fov. Will be used unless this would mean fov x exceeding _x_max
            _y_desired: 8 * Math.PI / 180,

            // Max x fov
            _x_max: 160 * Math.PI / 180,

            // Desired y REFERENCE FOV - this is what we use to enable the sun tracking in wide mode
            _y_ref:         undefined,
            _x_ref:         undefined,
        };

        // Zoomed field of view in radians
        this.zoomed_fov = {
            // Max x fov is 140 degrees - will be set by first call to View.update_fov when the
            // simulator is zoomed
            x: undefined,

            // Max y fov is 90 degrees
            y: undefined,

            // Desired y fov. Will be used unless this would mean fov x exceeding _x_max
            _y_desired: 5 * Math.PI / 180,

            // Max x fov
            _x_max: 160 * Math.PI / 180,

            // Desired y REFERENCE FOV - this is what we use to enable the sun tracking in wide mode
            // this is never actually used for this fov, since it is the zoom fov but is included to
            // simplify the View.update_fov code
            _y_ref:         undefined,
            _x_ref:         undefined,
        };

        this.zoom_level    = EclipseSimulator.VIEW_ZOOM_WIDE;
        this.current_fov   = this.wide_fov;

        // Eclipse info
        this.eclipse_pos   = {
            alt: 0,
            az:  0,
        };
        this.eclipse_time  = new Date();
        this.current_time  = new Date();

        this.sun_beg_pos   = {
            alt: 0,
            az:  0,
        };
        this.sun_end_pos   = {
            alt: 0,
            az:  0,
        };
        this.sun_moon_position_ratios = {
            x: {
                start: 0,
                end:   0,
            },
            y: {
                start: 0,
                end:   0,
            },
        };

        // Acting SVG size - we set the SVG canvas to be the entire width of the window,
        // but we don't want to report this to the simulator, as this results in too wide of an
        // aspect ratio that makes it difficult to keep the sun in view vertically without
        // exceeding 180 degrees of horizontal field of view, which doesn't even make sense.
        // Therefore, we report the environment size using the variable below, which is set by the
        // update_sim_size function.
        this.acting_svg_size = {
            height: 0,
            width: 0,
        };
        // This is the offset of the "acting SVG canvas" from the left side of the actual SVG canvas
        // This value is computed as (actual_svg_w - acting_svg_w)/2
        this.svg_horizontal_offset = 0;

        // True simulator window size
        this.environment_size = {
            height: 0,
            width: 0,
        };

        this.location_name = location !== undefined ? location.name : EclipseSimulator.DEFAULT_LOCATION_NAME;
        this.time_zone_name = location !== undefined ? "" : EclipseSimulator.DEFAULT_LOCATION_TIME_ZONE;

        this.playing       = false;
        this.play_speed    = EclipseSimulator.VIEW_PLAY_SPEED_SLOW;
    },

    Controller: function(location)
    {
        this.view                         = new EclipseSimulator.View(location);
        this.model                        = new EclipseSimulator.Model(location);
        this.current_animation_id         = undefined;
        this.previous_animation_timestamp = undefined;
    },

    Model: function(location)
    {
        // Current simulator coordinates
        this.coords = location !== undefined ? location.coords : EclipseSimulator.DEFAULT_LOCATION_COORDS;

        // Current simulator time
        this.date = new Date(EclipseSimulator.ECLIPSE_DAY);

        // Computed eclipse time -- temp value, this will be set when
        // Model.compute_eclipse_time_and_pos is called
        this.eclipse_time = new Date(EclipseSimulator.ECLIPSE_DAY);
    },

    // Convert degrees to radians
    deg2rad: function(v)
    {
        return v * Math.PI / 180;
    },

    // Convert radians to degrees
    rad2deg: function(v)
    {
        return v * 180 / Math.PI;
    },

    // Convert a to be on domain [0, 2pi)
    normalize_rad: function(a)
    {
        var pi2 = Math.PI * 2;
        return a - (pi2 * Math.floor(a / pi2));
    },

    // Compute a1 - a2. return value in [0, 2pi)
    rad_diff: function(a1, a2)
    {
        var diff = EclipseSimulator.rad_abs_diff(a1, a2);
        return EclipseSimulator.rad_gt(a1, a2) ? diff : -diff;
    },

    // Compute positive distance in radians between two angles
    rad_abs_diff: function(a1, a2)
    {
        a1 = EclipseSimulator.normalize_rad(a1);
        a2 = EclipseSimulator.normalize_rad(a2);

        var diff = a1 > a2 ? (a1 - a2) : (a2 - a1);

        return diff > Math.PI ? (2 * Math.PI) - diff : diff;
    },

    // Determine if angle a is greater than angle b
    // That is, if b < a <= (b + pi)
    rad_gt: function(a, b)
    {
        a = EclipseSimulator.normalize_rad(a);
        b = EclipseSimulator.normalize_rad(b);

        a = EclipseSimulator.normalize_rad(a - b);
        b = 0;

        return a > b && a <= Math.PI;
    },

    // Compute sun/moon angular seperation and moon radius
    // See https://en.wikipedia.org/wiki/Angular_distance
    compute_sun_moon_sep: function(sun, moon) {
        var a = (Math.sin(sun.alt) * Math.sin(moon.alt)) +
                (Math.cos(sun.alt) * Math.cos(moon.alt) * Math.cos(sun.az - moon.az));
        return Math.acos(a);
    },

    get_local_time_from_date: function(date, offset, include_seconds) {
        // Convert UTC offset in minutes to hours
        var hour_offset = offset/60;

        var local_hour;
        var am_pm_string;

        // Zero padding in js is gross
        var mins = "" + date.getMinutes();
        mins     = mins.length == 1 ? "0" + mins : mins;
        var secs = "";
        // compute local hour relative to UTC time
        local_hour = (date.getUTCHours() + hour_offset + 11) % 12 + 1;

        if (date.getUTCHours() + hour_offset >= 12)
        {
            am_pm_string = "PM";
        }
        else
        {
            am_pm_string = "AM";
        }

        if (include_seconds)
        {
            secs = "" + date.getSeconds();
            secs = secs.length == 1 ? "0" + secs : secs;
        }

        var label_string = local_hour + ":" + mins + (include_seconds ? ":" + secs : "") + '\u00a0' + am_pm_string;

        return label_string;
    },


    // Target amount of the field of view that is "filled" by the sun's path
    VIEW_TARGET_FOV_FILL: 0.9,

    VIEW_MAP_MAX_H: 400,

    // Distance between map and top of window (phone mode)
    VIEW_MAP_TMARGIN: 92,

    VIEW_MAP_LMARGIN: 8,

    GEOCODE_MAP_ZOOM : 8,

    VIEW_ZOOM_WIDE: 'wide',

    VIEW_ZOOM_ZOOM: 'zoom',

    VIEW_SLIDER_STEP_MIN: {
        zoom: .25,
        wide: .25,
    },

    VIEW_BG_IMAGE_W:             1397,
    VIEW_BG_IMAGE_H:             789,
    VIEW_BG_IMAGE_HILL_CREST_H:  242,
    VIEW_BG_IMAGE_HILL_VALLEY_H: 151,

    VIEW_ACTING_SVG_MAX_ASPECT_RATIO: 1.5,

    VIEW_PHONE_DISP_W_MAX: 750,

    VIEW_MAP_MAX_W: 800,

    VIEW_MAP_TOTALITY_LAT: [39.995, 41.495, 42.855, 43.593, 44.1, 44.472, 44.752, 44.963, 45.12, 45.233, 45.308, 45.35, 45.365, 45.355, 45.322, 45.27, 45.198, 45.11, 45.007, 44.888, 44.755, 44.612, 44.455, 44.288, 44.11, 43.923, 43.727, 43.522, 43.307, 43.085, 42.855, 42.618, 42.375, 42.123, 41.867, 41.603, 41.333, 41.058, 40.777, 40.49, 40.198, 39.902, 39.598, 39.292, 38.98, 38.663, 38.342, 38.015, 37.685, 37.35, 37.012, 36.668, 36.32, 35.968, 35.612, 35.252, 34.887, 34.518, 34.145, 33.767, 33.385, 32.998, 32.608, 32.212, 31.812, 31.408, 30.998, 30.585, 30.165, 29.74, 29.312, 28.875, 28.435, 27.987, 27.533, 27.073, 26.607, 26.133, 25.65, 25.16, 24.662, 24.152, 23.633, 23.102, 22.558, 22.002, 21.43, 20.84, 20.232, 19.6, 18.94, 18.247, 17.513, 16.725, 15.86, 14.877, 13.66, 11.26, 10.782, 13.477, 14.587, 15.512, 16.333, 17.088, 17.793, 18.462, 19.098, 19.712, 20.302, 20.873, 21.43, 21.97, 22.498, 23.015, 23.522, 24.018, 24.505, 24.983, 25.453, 25.917, 26.372, 26.822, 27.263, 27.7, 28.132, 28.557, 28.977, 29.392, 29.802, 30.207, 30.607, 31.003, 31.393, 31.78, 32.163, 32.54, 32.915, 33.283, 33.65, 34.01, 34.368, 34.722, 35.07, 35.415, 35.757, 36.093, 36.425, 36.753, 37.078, 37.398, 37.713, 38.025, 38.332, 38.633, 38.93, 39.223, 39.512, 39.793, 40.072, 40.343, 40.612, 40.872, 41.128, 41.377, 41.62, 41.857, 42.087, 42.308, 42.523, 42.732, 42.93, 43.122, 43.303, 43.475, 43.637, 43.787, 43.927, 44.053, 44.167, 44.267, 44.35, 44.418, 44.467, 44.493, 44.5, 44.478, 44.428, 44.345, 44.22, 44.048, 43.813, 43.5, 43.072, 42.455, 41.42, 39.48],

    VIEW_MAP_TOTALITY_LNG: [-171.748, -164.505, -156.937, -152.105, -148.257, -144.965, -142.047, -139.4, -136.963, -134.695, -132.568, -130.56, -128.655, -126.84, -125.105, -123.442, -121.843, -120.305, -118.82, -117.385, -115.997, -114.65, -113.345, -112.077, -110.842, -109.642, -108.472, -107.332, -106.218, -105.132, -104.07, -103.032, -102.015, -101.02, -100.043, -99.087, -98.148, -97.227, -96.322, -95.432, -94.555, -93.693, -92.843, -92.007, -91.182, -90.367, -89.562, -88.767, -87.98, -87.202, -86.432, -85.667, -84.91, -84.157, -83.41, -82.667, -81.927, -81.19, -80.457, -79.723, -78.992, -78.26, -77.528, -76.795, -76.06, -75.323, -74.582, -73.835, -73.083, -72.325, -71.56, -70.785, -70.002, -69.205, -68.398, -67.575, -66.737, -65.88, -65.003, -64.103, -63.178, -62.225, -61.24, -60.218, -59.155, -58.045, -56.88, -55.652, -54.35, -52.958, -51.46, -49.828, -48.023, -45.99, -43.627, -40.74, -36.81, -27.332, -27.552, -38.467, -42.078, -44.827, -47.108, -49.09, -50.857, -52.46, -53.935, -55.308, -56.595, -57.808, -58.962, -60.062, -61.117, -62.128, -63.107, -64.052, -64.97, -65.862, -66.732, -67.582, -68.413, -69.23, -70.032, -70.82, -71.597, -72.365, -73.123, -73.873, -74.617, -75.355, -76.088, -76.817, -77.543, -78.267, -78.988, -79.71, -80.432, -81.153, -81.875, -82.6, -83.327, -84.058, -84.792, -85.53, -86.273, -87.023, -87.778, -88.542, -89.31, -90.088, -90.875, -91.672, -92.477, -93.293, -94.122, -94.963, -95.817, -96.683, -97.565, -98.462, -99.373, -100.303, -101.252, -102.218, -103.205, -104.213, -105.243, -106.298, -107.377, -108.483, -109.617, -110.78, -111.975, -113.203, -114.468, -115.772, -117.117, -118.507, -119.943, -121.433, -122.982, -124.592, -126.27, -128.027, -129.87, -131.813, -133.87, -136.062, -138.413, -140.963, -143.765, -146.908, -150.548, -155.018, -161.407, -171.433],

    VIEW_BG_COLOR_NIGHT: [0,   0,   0],
    VIEW_BG_COLOR_DAY:   [140, 210, 221],

    VIEW_OUTSIDE_TOTALITY_MAX_DARK_OPACITY: 0.65,

    VIEW_SLIDER_NSTEPS: 720,

    VIEW_PLAY_SPEED_SLOW: 'slow',

    VIEW_PLAY_SPEED_FAST: 'fast',

    VIEW_PLAY_SPEED: {
        zoom: {
            slow: 1000,
            fast: 4000
        },
        wide: {
            slow: 1000,
            fast: 4000
        },
    },

    DEFAULT_USER_ERR_MSG: 'An error occured',

    DEFAULT_USER_ERR_TIMEOUT: 2000,

    DEFAULT_LOCATION_NAME: 'Corvallis, OR, United States',

    DEFAULT_LOCATION_COORDS: {
        lat: 44.567353,
        lng: -123.278622,
    },

    DEFAULT_LOCATION_IN_TOTALITY: true,

    DEFAULT_LOCATION_TIME_ZONE: 'PDT',

    DEFAULT_LOCATION_UTC_OFFSET: -420,  // minutes

    DEFAULT_LOCATION_PLACE_ID: 'ChIJfdcUqp1AwFQRvsC9Io-ADdc',

    ECLIPSE_DAY: new Date('08/21/2017'),

    ECLIPSE_ECOAST_HOUR: 20,

    ECLIPSE_WCOAST_HOUR: 16,

    PLAY_PAUSE_BUTTON: {
        true:  'play_arrow',
        false: 'pause',
    },

    MOON_RADIUS: 1737,

    TIME_ZONE_API_ENDPOINT: "/services/geo/timezone",

};


// =============================
//
// EclipseSimulator.View methods
//
// =============================

EclipseSimulator.View.prototype.init = function()
{

    // Needs to be called the first time as this will set the simulator size
    this._update_sim_size();

    // Have to create a reference to this, because inside the window
    // refresh function callback this refers to the window object
    var view = this;

    // This makes the sun move along with the slider
    // A step toward calculating and displaying the sun and moon at a specific time based on the slider
    $(this.slider).on('input', function() {
        view.playing = false;
        view.slider_change();
    });

    $(this.slider).tooltip({
        track: true,
        classes: {
            "ui-tooltip": "slider-tooltip mdl-shadow--2dp"
        }
    });

    // Increments the slider on a click
    $(this.upbutton).click(function() {
        view.playing = false;
        view.slider_change('up');
    });

    // Decrements the slider on a click
    $(this.downbutton).click(function() {
        view.playing = false;
        view.slider_change('down');
    });

    // Keyboard bindings
    $(document).keydown(function(e) {
        var tag = e.target.tagName.toLowerCase();
        if (tag == 'input') {
            return;
        }
        switch(e.which) {
        // space bar
        case 32:
            $(view.playbutton).click();
            break;
        // left arrow key
        case 37:
            $(view.downbutton).click();
            break;
        // right arrow key
        case 39:
            $(view.upbutton).click();
            break;
        default:
                return;
        }
    });

    $(this.zoombutton).click(function() {
        view.playing = false;
        view.toggle_zoom()
    });

    $(this.playbutton).click(function() {
        $(view).trigger('EclipseView_toggle_playing');
    });

    //toggle's the view play speed and disables the menu option for the current speed
    $(this.speed_menu).click(function(e) {
        if (view.play_speed == EclipseSimulator.VIEW_PLAY_SPEED_SLOW)
        {
            view.play_speed = EclipseSimulator.VIEW_PLAY_SPEED_FAST;
            $(view.speed_btn_fast).attr('disabled', true);
            $(view.speed_btn_slow).attr('disabled', false);
        }
        else
        {
            view.play_speed = EclipseSimulator.VIEW_PLAY_SPEED_SLOW;
            $(view.speed_btn_fast).attr('disabled', false);
            $(view.speed_btn_slow).attr('disabled', true);
        }
        $(view.speed_sel_btn).find('span').text($(e.target).text());
    });

    // Hide the map when the view initializes
    $(this.mapcanvas).hide();
    this._create_polygon_map();

    // Toggles the visibility of the map on click
    $(this.mapbutton).click(function() {
        view.playing = false;
        view.toggle_map();
    });

    this._init_top_bar();
    this.initialize_location_entry();

    // Rescale the window when the parent iframe changes size
    $(window).resize(function() {
        view._update_sim_size();
        view._adjust_size_based_control_ui();
        view._adjust_size_based_map_ui(0);
        view.update_fov();
        view.refresh();
    });

    $(window).on("message", function(e) {
        if (e.originalEvent && e.originalEvent.data) {
            // Check if lat and lng are there.
            var data = e.originalEvent.data;
            if (data.lat && data.lng) {
                var latLng = new google.maps.LatLng(data);
                view.setPlace(latLng, true);
            }
        }
    });

    view._adjust_size_based_control_ui();
    view._adjust_size_based_map_ui(0);
    this.set_play_speed_label();
    this.update_fov();
    this.refresh();
};

EclipseSimulator.View.prototype._onPlaceResponse = function(place, status) {
    var view = this;
    if (status == google.maps.places.PlacesServiceStatus.OK) {
        view.offset = place.utc_offset;
        view.queryTimeZone(place);
    }
};

EclipseSimulator.View.prototype.initialize_location_entry = function()
{
    var view = this;

    var autocomplete_options = {
        componentRestrictions: {country: 'us'}
    };
    view.search_box = new google.maps.places.Autocomplete(this.search_input, autocomplete_options);

    view.marker = new google.maps.Marker({
        map: this.map,
        position: EclipseSimulator.DEFAULT_LOCATION_COORDS,
    });
    view.marker.setVisible(true);

    view.geocoder            = new google.maps.Geocoder();
    view.autocomplete_service = new google.maps.places.AutocompleteService();
    view.places_service       = new google.maps.places.PlacesService(view.garbage_dump);

    // Listen for the event fired when the user selects a prediction and retrieve
    // more details for that place.
    view.search_box.addListener('place_changed', function() {

        view.playing = false;

        view.marker.setVisible(false);
        view.maps_place = view.search_box.getPlace();

        if (!view.maps_place.geometry)
        {
            var options = {
                input: view.maps_place.name,
                componentRestrictions: {country: 'us'}
            };

            view.autocomplete_service.getPlacePredictions(options, function(predictions, status) {
                if (status != google.maps.places.PlacesServiceStatus.OK) {
                    view.display_error_to_user("Location not found");
                    return;
                }

                view.geocoder.geocode({'placeId': predictions[0].place_id}, function(results, status) {
                    if (status === 'OK') {
                        if (results[0].formatted_address.includes('USA')) {

                            view.maps_place = results[0];

                            view.marker.setVisible(false);

                            // Update location name
                            view.name = results[0].formatted_address;
                            view.search_input.value = results[0].formatted_address;

                            if (!view.maps_place)
                            {
                                view.display_error_to_user("No details available for: " + view.maps_place.name);
                                return;
                            }

                            view.map.setCenter(view.maps_place.geometry.location);
                            view.map.setZoom(EclipseSimulator.GEOCODE_MAP_ZOOM);

                            view.marker.setPosition(view.maps_place.geometry.location);
                            view.marker.setVisible(true);

                            // Update location name
                            view.name = view.maps_place;

                            $(view).trigger('EclipseView_location_updated', view.maps_place.geometry.location);

                            var request = {
                                placeId: predictions[0].place_id
                            };
                            view.places_service.getDetails(request, view._onPlaceResponse.bind(view));

                        } else {
                            view.display_error_to_user("Simulator is restricted to the United States");
                            return;
                        }
                    } else {
                        view.display_error_to_user("Location not found");
                        return;
                    }
                });

            });
            return;
        } else {

            view.offset = view.maps_place.utc_offset;

            // If the place has a geometry, then present it on a map.
            if (view.maps_place.geometry.viewport != undefined) {
                view.map.fitBounds(view.maps_place.geometry.viewport);
                view.map.setZoom(EclipseSimulator.GEOCODE_MAP_ZOOM);
            } else {
                view.map.setCenter(view.maps_place.geometry.location);
                view.map.setZoom(EclipseSimulator.GEOCODE_MAP_ZOOM);
            }
            view.marker.setPosition(view.maps_place.geometry.location);
            view.marker.setVisible(true);

            // Update location name
            view.name = view.maps_place.formatted_address;

            $(view).trigger('EclipseView_location_updated', view.maps_place.geometry.location);
            view.queryTimeZone(view.maps_place);
        }
    });

    google.maps.event.addListener(view.map, 'click', function(event) {
        this.setPlace(event.latLng);
    }.bind(view));

    // Set initial searchbox text
    this.search_input.value = this.location_name;
};

EclipseSimulator.View.prototype.setPlace = function(gLatLng, center) {
   var view = this;
   view.maps_place = gLatLng;

   var latlng = {lat: view.maps_place.lat(), lng: view.maps_place.lng()};

   view.geocoder.geocode({'location': latlng}, function(results, status) {
       if (status === 'OK') {

           if (results[1].formatted_address.includes('USA')) {

               view.marker.setVisible(false);


               view.name = results[1].formatted_address;
               view.search_input.value = results[1].formatted_address;

               if (!view.maps_place)
               {
                   view.display_error_to_user("No details available for: " + view.maps_place.name);
                   return;
               }

               view.marker.setPosition(view.maps_place);
               view.marker.setVisible(true);

               // Update location name
               view.name = view.maps_place;

               $(view).trigger('EclipseView_location_updated', view.maps_place);

               var request = {
                   placeId: results[1].place_id
               };
               view.places_service.getDetails(request, view._onPlaceResponse.bind(view));
               if (center) {
                   view.map.setCenter(gLatLng);
               }
           } else {
               view.display_error_to_user("Simulator is restricted to the United States");
               return;
           }
       } else {
           view.display_error_to_user("Location not found");
           return;
       }
   });
};

EclipseSimulator.View.prototype.queryTimeZone = function(place) {
    $.ajax({
        url: EclipseSimulator.TIME_ZONE_API_ENDPOINT,
        data: {
                location: place.geometry.location.lat() +"," + place.geometry.location.lng(),
                key: api_key,
                timestamp: EclipseSimulator.ECLIPSE_DAY.getTime() / 1000
             }
        })
        .done(function(data) {
            var timeZoneName = "";
            if (data.timeZoneName) {
                // Convert to abbreviation.
                var names = data.timeZoneName.split(" ");
                for (var index = 0; index < names.length; index++) {
                    timeZoneName += names[index].charAt(0);
                }
            }
            this.time_zone_name = timeZoneName;
            this.update_slider_labels();
        }.bind(this));
};

EclipseSimulator.View.prototype.update_totality = function() {
    if (google.maps.geometry && this.marker && this.marker.getVisible()) {
        if (google.maps.geometry.poly.containsLocation(this.marker.getPosition(), this.eclipsePath)) {
            $(this.totality_label).text("Total eclipse");
            this.in_totality = true;
        } else {
            $(this.totality_label).text("Partial eclipse");
            this.in_totality = false;
        }
    } else {
        $(this.totality_label).text("");
        this.in_totality = false;
    }
};

EclipseSimulator.View.prototype._update_sim_size = function(zoomed)
{
    zoomed = zoomed || false;
    var h = $(window).height();
    var w = $(window).width();

    var svg_margin_left = 0;
    var svg_w           = w;
    var svg_h           = h;
    if (!zoomed)
    {
        // Add bottom buffer - define altitude 0 to be the bottom of the hill crests - using the valleys
        // can result in the sun falling below the hills
        svg_h -= h * this.compute_y_percetage_of_frame(EclipseSimulator.VIEW_BG_IMAGE_HILL_CREST_H);

        if ((svg_w / svg_h) > EclipseSimulator.VIEW_ACTING_SVG_MAX_ASPECT_RATIO)
        {
            svg_w = svg_h * EclipseSimulator.VIEW_ACTING_SVG_MAX_ASPECT_RATIO;
            svg_margin_left = (w - svg_w) / 2;
        }
    }

    this.acting_svg_size.height = svg_h;
    this.acting_svg_size.width  = svg_w;
    this.svg_horizontal_offset  = (w - svg_w) / 2;
    $(this.svg_container).css({
        'height': svg_h,
        'width':  w,
    });

    this.environment_size.height = h;
    this.environment_size.width  = w;
    this.background.css({
        'height': h,
        'width':  w,
    });

    $(this.loading).css('height', w + 'px');

    return {
        height: h,
        width:  w,
        svg_h:  svg_h,
    }
};

EclipseSimulator.View.prototype.show = function()
{
    this.background.show();
    $([this.svg_container, this.sun, this.moon]).show();
};

EclipseSimulator.View.prototype.refresh = function()
{

    if (this.zoom_level == EclipseSimulator.VIEW_ZOOM_ZOOM)
    {
        var az_center  = this.sunpos.az;
        var alt_center = this.sunpos.alt;
    }
    else
    {
        var centers    = this.compute_wide_mode_altaz_centers();
        var az_center  = centers.az;
        var alt_center = centers.alt;
    }

    // Position sun/moon. Cannot do this until window is displayed
    this.position_body_at_percent_coords(
        this.sun,
        {
            x: this.get_ratio_from_altaz(this.sunpos.az,  az_center,  this.current_fov.x, this.sunpos.r),
            y: this.get_ratio_from_altaz(this.sunpos.alt, alt_center, this.current_fov.y, this.sunpos.r),
            r: this.get_ratio_from_body_angular_r(this.sunpos.apparant_r, this.sunpos.alt, alt_center),
        }
    );
    this.position_body_at_percent_coords(
        this.moon,
        {
            x: this.get_ratio_from_altaz(this.moonpos.az,  az_center,  this.current_fov.x, this.moonpos.r),
            y: this.get_ratio_from_altaz(this.moonpos.alt, alt_center, this.current_fov.y, this.moonpos.r),
            r: this.get_ratio_from_body_angular_r(this.moonpos.r, this.moonpos.alt, alt_center),
        }
    );

    // === Update background and moon color === //

    var p = this.compute_percent_eclipse();

    // Brightness of sun is exponential in its area
    p = Math.pow(100, p - 1);

    // Cap the darkness if not in path of totality
    if (!this.in_totality)
    {
        p = Math.min(p, EclipseSimulator.VIEW_OUTSIDE_TOTALITY_MAX_DARK_OPACITY);
    }

    // Compute sky color - this is the same color used for the moon
    var rgba_str = this.get_rgba_string(p, EclipseSimulator.VIEW_BG_COLOR_DAY,
                                        EclipseSimulator.VIEW_BG_COLOR_NIGHT);

    // Update background and moon lightness
    this.update_bg_lightness(p, rgba_str);
    this.update_moon_lightness(rgba_str);

};

// Computes percentage of frame (in the y direction) that is occupied by an object
// (say a hill on the background) that is ref_height pixels high in the original background
// image. This is variable since the background scales with the window size
EclipseSimulator.View.prototype.compute_y_percetage_of_frame = function(ref_height)
{
    var ratio                   = this.environment_size.width / this.environment_size.height;
    var image_ratio             = EclipseSimulator.VIEW_BG_IMAGE_W / EclipseSimulator.VIEW_BG_IMAGE_H;
    var overall_hill_percentage = ref_height / EclipseSimulator.VIEW_BG_IMAGE_H;
    var hidden_bottom           = 0;

    // Window aspect ratio is greater than image aspect ratio => top/bottom of background image are
    // cut off
    if (ratio > image_ratio)
    {
        var rel_img_height      = this.environment_size.width / image_ratio;
        var rel_hill_height     = rel_img_height * (ref_height / EclipseSimulator.VIEW_BG_IMAGE_H);
        hidden_bottom           = (rel_img_height - this.environment_size.height) / 2;
        overall_hill_percentage = (rel_hill_height - hidden_bottom) / this.environment_size.height;
    }

    return Math.max(0, overall_hill_percentage);
};

EclipseSimulator.View.prototype.position_body_at_percent_coords = function(target, pos)
{
    // This happens early on in initialization
    if (isNaN(pos.r) || isNaN(pos.x) || isNaN(pos.y) || pos.r < 0)
    {
        return;
    }

    // Adjust radius
    $(target).attr('r', (this.acting_svg_size.height * pos.r));

    // with SVG, (0, 0) is top left corner
    $(target).attr('cy', (this.acting_svg_size.height * (1 - pos.y)));

    $(target).attr('cx', this.svg_horizontal_offset + (this.acting_svg_size.width * pos.x));

};

EclipseSimulator.View.prototype.get_ratio_from_body_angular_r = function(r, alt, center)
{
    var x = EclipseSimulator.rad_abs_diff(alt, center);
    return (Math.sin(x + r) - Math.sin(x)) / (2 * Math.sin(this.current_fov.y / 2));
};

EclipseSimulator.View.prototype.get_ratio_from_altaz = function(altaz, center, fov, body_r)
{
    var dist_from_center = Math.sin(altaz - center);
    var half_fov_width   = Math.sin(fov / 2);

    if (EclipseSimulator.rad_abs_diff(altaz, center) > (Math.PI / 2))
    {
        return -0.5;
    }

    return 0.5 + (0.5 * dist_from_center / half_fov_width);
};

EclipseSimulator.View.prototype.slider_change = function(direction)
{
    var current    = parseFloat(this.slider.value);
    var offset     = 0;
    var max_offset = EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level]
                     * EclipseSimulator.VIEW_SLIDER_NSTEPS / 2;

    if (direction === 'up')
    {
        offset = 2 * EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level];
    }
    else if (direction === 'down')
    {
        offset = (-1) * 2 * EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level];
    }
    var new_val = current + offset;

    if (new_val <= max_offset && new_val >= (-max_offset))
    {
        this.slider.MaterialSlider.change(new_val);
        $(this).trigger('EclipseView_time_updated', new_val);
    }

    if (new_val >= max_offset || new_val <= (-max_offset))
    {
        this.end_of_slider = true;
    }
};

EclipseSimulator.View.prototype.set_play_speed_label = function()
{
    $(this.speed_btn_slow).text(EclipseSimulator.VIEW_PLAY_SPEED[this.zoom_level][EclipseSimulator.VIEW_PLAY_SPEED_SLOW] + 'X');
    $(this.speed_btn_fast).text(EclipseSimulator.VIEW_PLAY_SPEED[this.zoom_level][EclipseSimulator.VIEW_PLAY_SPEED_FAST] + 'X');
};

EclipseSimulator.View.prototype.toggle_loading = function()
{
    $(this.loading).toggle();
};

// resets the slider to the start
EclipseSimulator.View.prototype.reset_controls = function()
{
    // compute the minimum slider value
    var min_slider_val = (-1) * EclipseSimulator.VIEW_SLIDER_NSTEPS
        * EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level] / 2;

    // Need this check in case MDL has not finished initializing
    if (this.slider.MaterialSlider !== undefined)
    {
        this.slider.MaterialSlider.change(min_slider_val);
    }
};

EclipseSimulator.View.prototype.display_error_to_user = function(error_msg, timeout)
{
    error_msg = error_msg === undefined ? EclipseSimulator.DEFAULT_USER_ERR_MSG
                                        : error_msg;

    timeout = timeout === undefined ? EclipseSimulator.DEFAULT_USER_ERR_TIMEOUT
                                    : timeout;

    var data = {
        message:        error_msg,
        timeout:        timeout,
        actionHandler:  undefined,
        actionText:     '',
    };

    this.error_snackbar.MaterialSnackbar.showSnackbar(data);
};

EclipseSimulator.View.prototype.update_slider_labels = function()
{
    var slider_range_ms = 1000 * 60 * EclipseSimulator.VIEW_SLIDER_NSTEPS
                          * EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level];
    var tick_sep_ms     = (slider_range_ms / (this.slider_labels.length - 1));
    var date            = new Date(this.eclipse_time.getTime() - (slider_range_ms / 2));

    for (var i = 0; i < this.slider_labels.length; i++)
    {
        var time = EclipseSimulator.get_local_time_from_date(date, this.offset);
        if (i == 0 && this.time_zone_name) {
            time += '\u00a0' + this.time_zone_name;
        }
        $(this.slider_labels[i]).text(time);
        date.setTime(date.getTime() + tick_sep_ms);
    }
};

EclipseSimulator.View.prototype.toggle_zoom = function()
{
    if (this.zoom_level === EclipseSimulator.VIEW_ZOOM_WIDE)
    {
        this.zoom_level  = EclipseSimulator.VIEW_ZOOM_ZOOM;
        this.current_fov = this.zoomed_fov;
        var label        = 'zoom_out';

        this._update_sim_size(true);

        // Hide the hills/clouds/people/etc
        $(this.background[1]).hide();
        $(this.background[2]).hide();
        $(this.background[3]).hide();
    }
    else
    {
        this.zoom_level  = EclipseSimulator.VIEW_ZOOM_WIDE;
        this.current_fov = this.wide_fov;
        var label        = 'zoom_in';
        var zooming_in   = false;

        this._update_sim_size(false);

        // Show the hills/clouds/people/etc
        $(this.background[1]).show();
        $(this.background[2]).show();
        $(this.background[3]).show();
    }
    $(this.zoombutton).find('i').text(label);

    // Update the slider labels and bounds
    this.update_slider();
    this.set_play_speed_label();

    this.update_fov();
    this.refresh();
};

EclipseSimulator.View.prototype.update_eclipse_info = function(info)
{
    this.eclipse_pos = {
        alt: info.alt,
        az:  info.az,
    };
    this.eclipse_time.setTime(info.time.getTime());
};

EclipseSimulator.View.prototype.update_sun_moon_pos = function(pos)
{
    this.sunpos.alt  = pos.sun.alt;
    this.sunpos.az   = pos.sun.az;
    this.moonpos.alt = pos.moon.alt;
    this.moonpos.az  = pos.moon.az;
    this.moonpos.r   = pos.moon.r;
}

EclipseSimulator.View.prototype.update_fov = function()
{
    var ratio         = this.acting_svg_size.width / this.acting_svg_size.height;
    var desired_x     = this._compute_fov_angle_for_screen_aspect_ratio(this.current_fov._y_desired, 1 / ratio);

    // Compute reference field of view needed to fit sun path in field of view - X DIRECTION
    var d1            = EclipseSimulator.rad_abs_diff(this.sun_beg_pos.az, this.eclipse_pos.az);
    var d2            = EclipseSimulator.rad_abs_diff(this.sun_end_pos.az, this.eclipse_pos.az);
    var diff          = Math.max(d1, d2);
    var desired_x_ref = 2 * diff / EclipseSimulator.VIEW_TARGET_FOV_FILL;

    // Compute reference field of view needed to fit sun path in field of view - Y DIRECTION
    d1                  = EclipseSimulator.rad_abs_diff(this.sun_beg_pos.alt, this.eclipse_pos.alt);
    d2                  = EclipseSimulator.rad_abs_diff(this.sun_end_pos.alt, this.eclipse_pos.alt);
    diff                = Math.max(d1, d2);
    // Just want to keep the sun in view with this desired_y_ref
    var desired_y_ref   = 2 * diff;

    // Window aspect ratio prevents desired y fov. Using the desired y fov, this.current_fov._y
    // would result in an x fov that is greater than the max allowed.
    if (desired_x > this.current_fov._x_max)
    {
        this.current_fov.x = this.current_fov._x_max
        this.current_fov.y = this._compute_fov_angle_for_screen_aspect_ratio(this.current_fov._x_max, ratio);
    }
    else
    {
        this.current_fov.x = desired_x;
        this.current_fov.y = this.current_fov._y_desired;
    }

    // Choosing desired_x_ref as fov in x direction would result in sun leaving view in y direction
    if (this._compute_fov_angle_for_screen_aspect_ratio(desired_x_ref, ratio) < desired_y_ref)
    {
        desired_x_ref = this._compute_fov_angle_for_screen_aspect_ratio(desired_y_ref, 1 / ratio);
    }
    if (desired_x_ref > this.current_fov._x_max)
    {
        desired_x_ref = this.current_fov._x_max;
    }
    this.current_fov._x_ref = desired_x_ref;
    this.current_fov._y_ref = this._compute_fov_angle_for_screen_aspect_ratio(desired_x_ref, ratio);

    // Update sun/moon position ratios
    this.sun_moon_position_ratios = {
        x: {
            start: this._compute_offset_ratio(this.eclipse_pos.az, this.sun_beg_pos.az, this.current_fov._x_ref),
            end:   this._compute_offset_ratio(this.eclipse_pos.az, this.sun_end_pos.az, this.current_fov._x_ref),
        },
        y: {
            start: this._compute_offset_ratio(this.eclipse_pos.alt, this.sun_beg_pos.alt, this.current_fov._y_ref),
            end:   this._compute_offset_ratio(this.eclipse_pos.alt, this.sun_end_pos.alt, this.current_fov._y_ref),
        },
    };
};

// Given the field of view in one direction (angle), this function computes the necessary field
// of view in the other direction necessary to achieve a screen aspect ratio of ratio. WHEN ratio IS
// COMPUTED, THE SCREEN SIZE IN THE DIMENSION CORRESPONDING TO ANGLE MUST BE ON THE TOP OF THE FRACTION
// This function maxs out at pi, so if an angle greater than pi is needed, pi will be returned
EclipseSimulator.View.prototype._compute_fov_angle_for_screen_aspect_ratio = function(angle, ratio)
{
    var inner = Math.min(1, Math.sin(angle / 2) / ratio);
    return 2 * Math.asin(inner);
};

// Computes an intermediate color between min and max, converts this color to an rgb string,
// This string is of the form 'rgba(x, y, z, a)' where x, y, and z are numbers in [0, 255]
// and a is an alpha value in [0, 1]. alpha is not computed, just returned.
//
// color_percent: Percentage min and max for the intermediate value - this value should be on the
//                interval [0, 1]
//
// start:         The starting color value, i.e. if percent 0 is passed in, start will be returned.
//                This is a 3 element array with numeric values corresponding to the red, green,
//                and blue color values. These numbers should be in [0, 255].
//
// end:           The ending color value, i.e., if percent 1 in passed in, end will be returned.
//                Format is the same as min.
//
// a:             Optional alpha - not changed, just added to rgba string
EclipseSimulator.View.prototype.get_rgba_string = function(color_percent, start, end, a)
{
    a = a || 1;
    // new values to be set to default minimum
    var new_rgb = [0, 0, 0];

    // Compute new color value based on percent and floor to integer
    for (var i = 0; i < 3; i++)
    {
        var diff   = end[i] - start[i];
        new_rgb[i] = Math.floor(color_percent * diff + start[i]);
    }

    // Create rgb str in std css format
    return "rgba(" + new_rgb[0] + "," + new_rgb[1] + "," + new_rgb[2] + "," + a + ")";
};

EclipseSimulator.View.prototype.update_bg_lightness = function(p, rgba_str)
{
    if (this.in_totality)
    {
        var show = 2;
        var hide = 3;
    }
    else
    {
        var show = 3;
        var hide = 2;
    }

    $(this.background[0]).css('background-color', rgba_str);
    $(this.background[show]).css('opacity', p);
    $(this.background[hide]).css('opacity', 0);
};

EclipseSimulator.View.prototype.update_moon_lightness = function(rgba_str)
{
    $(this.moon).attr('fill', rgba_str);
};

EclipseSimulator.View.prototype.update_slider = function()
{
    var slider_minmax = EclipseSimulator.VIEW_SLIDER_NSTEPS
                        * EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level] / 2;

    // If the current slider position is out of bounds, reset the time to eclipse time
    if (this.slider.value > slider_minmax || this.slider.value < -slider_minmax)
    {
       this.slider.MaterialSlider.change(0);
       this.slider_change();
    }

    $(this.slider).attr('min', -slider_minmax);
    $(this.slider).attr('max', slider_minmax);
    $(this.slider).attr('step', EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level]);

    // Re-render the slider as it now has a new position, since its bounds have changed
    if (this.slider.MaterialSlider !== undefined)
    {
        this.slider.MaterialSlider.boundChangeHandler();
    }
};

// Compute the percent of the eclipse
// sun_r and moon_r correspond to the radius (In radians) of each body
// Returns a percent between 0 and 1
EclipseSimulator.View.prototype.compute_percent_eclipse = function()
{
    // Avoid repeated attribute lookups
    var sun_r  = this.sunpos.r;
    var moon_r = this.moonpos.r;

    // Angular separation
    var sep        = EclipseSimulator.compute_sun_moon_sep(this.sunpos, this.moonpos);
    var lune_delta = this._compute_lune_delta(sun_r, moon_r, sep);
    var lune_area  = this._compute_lune_area(sun_r,  moon_r, sep, lune_delta);

    // Total solar eclipse
    if (lune_delta == 0)
    {
        var percent_eclipse = 1;
    }
    // No eclipse
    else if (lune_delta == -1)
    {
        var percent_eclipse = 0;
    }
    else
    {
        var percent_eclipse = 1 - (lune_area / (Math.PI * sun_r * sun_r))
    }

    if (EclipseSimulator.DEBUG)
    {
        console.log("Percent eclipse: " + percent_eclipse);
    }

    return percent_eclipse;
};

// Compute size of lune in radians
// http://mathworld.wolfram.com/Lune.html
EclipseSimulator.View.prototype._compute_lune_delta = function(sun_r, moon_r, sep)
{
    var lune_delta = -1;

    if (EclipseSimulator.DEBUG)
    {
        console.log('sep: ' + sep + ' sun_r + moon_r: ' + (sun_r + moon_r));
    }

    if (sep < (sun_r + moon_r))
    {
        var inner = ( sun_r + moon_r + sep) *
                    (-sun_r + moon_r + sep) *
                    (sun_r  - moon_r + sep) *
                    (sun_r  + moon_r - sep);

        if (inner < 0)
        {
            lune_delta = 0;
        }
        else
        {
            lune_delta = 0.25 * Math.sqrt(inner);
        }
    }

    return lune_delta;
};

// Assumes lune_delta > 0
EclipseSimulator.View.prototype._compute_lune_area = function(sun_r, moon_r, sep, lune_delta)
{
    // Avoid computing the same thing over and over again
    var moon_r2 = moon_r * moon_r;
    var sun_r2  = sun_r  * sun_r;
    var sep2    = sep * sep;

    var lune_area = (2 * lune_delta) +
                    (sun_r2  * Math.acos((moon_r2 - sun_r2 - sep2) / (2 * sun_r  * sep))) -
                    (moon_r2 * Math.acos((moon_r2 - sun_r2 + sep2) / (2 * moon_r * sep)));

    return lune_area;
};

EclipseSimulator.View.prototype.is_phone = function()
{
    return this.environment_size.width < EclipseSimulator.VIEW_PHONE_DISP_W_MAX;
};

EclipseSimulator.View.prototype._top_bar_w = function(map_open)
{
    map_open = map_open || false;
    var width = this._top_bar_control_w(map_open);
    if (map_open && !this.is_phone())
    {
        width += this._map_w(true);
    }

    return width;
};

EclipseSimulator.View.prototype._top_bar_control_w = function(map_open)
{
    map_open = map_open || false;
    var control_width = $(this.search_input).outerWidth(true);
    var is_phone = this.is_phone();

    if (!is_phone)
    {
        control_width += $(this.zoombutton).outerWidth(true);
    }

    if (!map_open || is_phone)
    {
        // This is kind of a hack. The zoom button and map button are the same size.
        // The reason we don't just use the map button here, is because when the map
        // is open and the map button is actually over the map,
        // $(this.mapbutton).outerWidth(true) returns -8
        control_width += $(this.zoombutton).outerWidth(true);
    }

    return control_width;
};

EclipseSimulator.View.prototype._map_w = function(include_margin)
{
    include_margin = include_margin || false;
    var width = this.environment_size.width;

    if (this.is_phone())
    {
        return width;
    }

    var control_width = this._top_bar_control_w(true);
    width            -= control_width;
    width             = Math.min(width, EclipseSimulator.VIEW_MAP_MAX_W);

    if (!include_margin)
    {
        width -= EclipseSimulator.VIEW_MAP_LMARGIN;
    }

    return width;
};

EclipseSimulator.View.prototype._init_top_bar = function()
{
    // Initialize top bar width
    $(this.topbar).css('width', this._top_bar_w());

    if (this.is_phone())
    {
        $(this.zoombutton).hide();
    }
};

EclipseSimulator.View.prototype._adjust_size_based_control_ui = function()
{
    if (this.is_phone())
    {
        $(this.speed_sel_btn).hide();
        $(this.upbutton).hide();
        $(this.downbutton).hide();

        for (var i = 0; i < this.slider_labels.length; i++)
        {
            if (i % 2 == 1) {
                $(this.slider_labels[i]).hide();
            }
        }
    }
    else
    {
        $(this.slider_labels).show();
        $(this.speed_sel_btn).show();
        $(this.upbutton).show();
        $(this.downbutton).show();
    }
};

EclipseSimulator.View.prototype._adjust_size_based_map_ui = function(timeout)
{
    timeout = timeout || 200;
    // Adjust map button icon and map width, if it is open
    if (this.map_visible)
    {
        $(this.mapcanvas).css('width', this._map_w());
        var icon = this.is_phone() ? 'arrow_upward' : 'arrow_back';
    }
    else
    {
        var icon = 'map';
    }
    $(this.mapbutton).find('i').text(icon);

    // Show/hide zoom button, restructure top bar DOM as needed
    if (this.is_phone())
    {
        if (this.zoom_level == EclipseSimulator.VIEW_ZOOM_ZOOM)
        {
            this.toggle_zoom();
        }
        $(this.zoombutton).hide();
        this.mobile_mapcont.appendChild(this.mapcanvas);
    }
    else
    {
        $(this.zoombutton).show();
        this.mapbutton.parentNode.insertBefore(this.mapcanvas, this.mapbutton);
    }

    var map_height = Math.min(
        $(window).height() - EclipseSimulator.VIEW_MAP_TMARGIN,
        EclipseSimulator.VIEW_MAP_MAX_H
    );
    $(this.mapcanvas).css('height', map_height + 'px');

    // Adjust top bar width
    $(this.topbar).animate({'width': this._top_bar_w(this.map_visible) + 'px'}, timeout);
};

EclipseSimulator.View.prototype.toggle_map = function()
{
    this.map_visible = !this.map_visible;

    var view = this;
    var center_map = function() {
        var center = view.map.getCenter();
        google.maps.event.trigger(view.map, "resize");
        view.map.setCenter(center);
    }

    // Reposition the map and zoom buttons
    $(this.mapbutton).toggleClass('map-open', 200);
    $(this.zoombutton).toggleClass('map-open');

    this._adjust_size_based_map_ui();

    // Show the map and center it
    $(this.mapcanvas).toggle(200, center_map);
};

// Creates the polygon of the path of totality to be used in the map display
// in the simulator. Using the arrays of latitude and longitude coordinates
// found on: https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2017Aug21Tpath.html
EclipseSimulator.View.prototype._create_polygon_map = function()
{
  var eclipse_path_coordinates = [];
  // Generate the path dictonary used in polygon creation
  for(var i = 0; i < EclipseSimulator.VIEW_MAP_TOTALITY_LAT.length; i++){
    eclipse_path_coordinates.push({lat: EclipseSimulator.VIEW_MAP_TOTALITY_LAT[i],
          lng: EclipseSimulator.VIEW_MAP_TOTALITY_LNG[i]});
  }

  // Create the polygon
  this.eclipsePath = new google.maps.Polygon({
    path: eclipse_path_coordinates,
    strokeColor: '#000000',
    strokeOpacity: 0.8,
    strokeWeight: 3,
    fillColor: '#000000',
    fillOpacity: 0.35,
    clickable: false
  });

  // Add the polygon to the map
  this.eclipsePath.setMap(this.map);
};

EclipseSimulator.View.prototype.compute_wide_mode_altaz_centers = function()
{
    var max_time_offset_ms = 0.5 * 1000 * 60 * EclipseSimulator.VIEW_SLIDER_NSTEPS *
                             EclipseSimulator.VIEW_SLIDER_STEP_MIN[EclipseSimulator.VIEW_ZOOM_WIDE];

    // range is [-1, 1]. -1 corresponds to start of slider range, 0 corresponds to time of maximal
    // eclipse, and 1 corresponds to end of slider range.
    var time_ratio = (this.current_time.getTime() - this.eclipse_time.getTime()) / max_time_offset_ms;

    return {
        az:  this.sunpos.az  + (this._wide_fov_tracking_poly(time_ratio, this.sun_moon_position_ratios.x) * this.current_fov.x),
        alt: this.sunpos.alt + (this._wide_fov_tracking_poly(time_ratio, this.sun_moon_position_ratios.y) * this.current_fov.y),
    };
};

// Computes offset ratio in field of view (centered at center_angle) with fov width fov_width.
// i.e. if position_angle is at the left edge of the field of view, -0.5 is returned, and
// if position_angle is at the right edge of the field of view, 0.5 is returned.
EclipseSimulator.View.prototype._compute_offset_ratio = function(position_angle, center_angle, fov_width)
{
    var diff = EclipseSimulator.rad_diff(position_angle, center_angle);
    var mult = diff > 0 ? 1 : -1;
    return mult * Math.sin(Math.abs(diff)) / (2 * Math.sin(fov_width / 2));
};

// Polynomial to enable smooth tracking of sun when in wide mode.
// This is an interpolating polynomial of the following points:
//
//      p0 = (-1, ratios.start)
//      p1 = (0, 0)
//      p2 = (1, ratios.end)
//
// We compute the polynomial at a given point t by computing the Lagrange basis
// polynomials l0, l1, l2 and returning (p0.y * l0(t)) + (p1.y * l1(t)) + (p2.y * l2(t))
//
// Note: we ignore since p1.y is 0
//
// For more information, see https://en.wikipedia.org/wiki/Lagrange_polynomial
//
EclipseSimulator.View.prototype._wide_fov_tracking_poly = function(t, ratios)
{
    var l0 = (t - 0) * (t - 1) / ((-1 - 0) * (-1 - 1));
    var l2 = (t + 1) * (t - 0) / (( 1 + 1) * ( 1 - 0));
    return (ratios.start * l0) + (ratios.end * l2);
};

// Returns boundary times for slider. Currently only returns wide mode boundaries
// as these are the only ones we need sun positions for - these positions are used for tracking
// in wide mode - see EclipseSimulator.View.prototype.compute_wide_mode_altaz_centers
//
// ***NOTE:*** It is critical the the order of the times returned here i.e.
// [wide_mode_slider_start, wide_mode_slider_end] is the same as the order that the sun positions
// are digested by EclipseSimulator.View.prototype._set_slider_bound_positions
EclipseSimulator.View.prototype._get_slider_bound_times = function()
{
    var max_time_offset_ms = 0.5 * 1000 * 60 * EclipseSimulator.VIEW_SLIDER_NSTEPS *
                             EclipseSimulator.VIEW_SLIDER_STEP_MIN[EclipseSimulator.VIEW_ZOOM_WIDE];

    return [
        new Date(this.eclipse_time.getTime() - max_time_offset_ms),
        new Date(this.eclipse_time.getTime() + max_time_offset_ms),
    ];
};

// Used in concert with EclipseSimulator.View.prototype._get_slider_bound_times by the controller.
// The controller calls _get_slider_bound_times, computes the sun positions at these times, and
// passes these positions to this function to set them in the view.
//
// ***NOTE:*** It is critical the the order in which positions are processed here i.e.
// [wide_mode_slider_start, wide_mode_slider_end] is the same as the order that the times are
// returned by EclipseSimulator.View.prototype._get_slider_bound_times
EclipseSimulator.View.prototype._set_slider_bound_positions = function(positions)
{
    this.sun_beg_pos = positions[0];
    this.sun_end_pos = positions[1];
};

// Updates view elements associated with simulator playing
EclipseSimulator.View.prototype.start_playing = function()
{
    // If the slider is at the very end of the time range and the user hits
    // the play button again. It will restart the playing of the simulation
    // from the beginning.
    if (this.end_of_slider)
    {
      // Restart the slider at the beginning
      this.slider.value = (-1) * EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level]
                          * EclipseSimulator.VIEW_SLIDER_NSTEPS / 2;
    }

    this.playing = true;
    $(this.playbutton).find('i').text(EclipseSimulator.PLAY_PAUSE_BUTTON[!this.playing]);
    $(this.slider).tooltip('disable');
};

// Updates view elements associated with simulator not playing if the simulator should stop playing.
// Returns true if the simulator should stop playing
EclipseSimulator.View.prototype.stop_playing = function(offset_ms)
{
    if (offset_ms !== undefined)
    {
        var max_offset_ms  = EclipseSimulator.VIEW_SLIDER_STEP_MIN[this.zoom_level]
                             * (EclipseSimulator.VIEW_SLIDER_NSTEPS / 2)
                             * 1000 * 60;
        this.end_of_slider = (offset_ms >= max_offset_ms);
    }

    if (!this.playing || this.end_of_slider || (offset_ms === undefined))
    {
        this.playing = false;
        $(this.playbutton).find('i').text(EclipseSimulator.PLAY_PAUSE_BUTTON[!this.playing]);
        $(this.slider).tooltip('enable');
        return true;
    }

    return false;
};

EclipseSimulator.View.prototype.update_slider_pos = function(offset_mins)
{
    this.slider.MaterialSlider.change(offset_mins);
};


// ===================================
//
// EclipseSimulator.Controller methods
//
// ===================================

EclipseSimulator.Controller.prototype.init = function()
{
    this.view.init();

    var controller = this;

    // Trigger these computations asynchronously, with a timeout of 1ms
    // to give the browser the chance to re-render the DOM with the loading view
    // after it has been initialized by the call to view.init()
    setTimeout(function() {

        controller.model.init();

        $(controller.view).on('EclipseView_time_updated', function(event, val) {
            // Call the handler, converting the val from minutes to milliseconds
            controller.update_simulator_time_with_offset(parseFloat(val) * 60 * 1000);
        });

        $(controller.view).on('EclipseView_location_updated', function(event, location) {
            // Call the location event handler with new location info
            controller.update_simulator_location(location);
        });

        $(controller.view).on('EclipseView_toggle_playing', function(event) {
            if (controller.view.playing)
            {
                controller.view.stop_playing();
                controller.stop_playing();
            }
            else
            {
                controller.start_playing();
            }
        });

        // Sets initial simulator location
        controller.update_simulator_location();

        // Simulator window/buttons, etc start out hidden so that the user doesn't see
        // a partially rendered view to start (e.g. height not set, etc). This only needs
        // to be shown once, so we do it manually
        controller.view.update_slider_labels();
        controller.view.show();

        var max_time_offset_ms = 0.5 * 1000 * 60 * EclipseSimulator.VIEW_SLIDER_NSTEPS *
            EclipseSimulator.VIEW_SLIDER_STEP_MIN[EclipseSimulator.VIEW_ZOOM_WIDE];

        // set simulator to start from the beginning
        controller.update_simulator_time_with_offset(0 - max_time_offset_ms);

        var min_slider_val = (-1) * EclipseSimulator.VIEW_SLIDER_NSTEPS
            * EclipseSimulator.VIEW_SLIDER_STEP_MIN[controller.view.zoom_level] / 2;

        // set slider to beginning
        controller.view.slider.value = min_slider_val;

        // Hide loading view - this starts out visible
        controller.view.toggle_loading();

        // Signal that initilization is complete, as this function completes asynchronously
        $(controller).trigger('EclipseController_init_complete');
    }, 1);

};

// Handler for when the slider gets changed
// sliderValueMS is expected to be passed in as milliseconds
EclipseSimulator.Controller.prototype.update_simulator_time_with_offset = function(time_offset_ms)
{
    // Get the computed eclipse time
    var new_sim_time_ms = this.model.eclipse_time.getTime() + time_offset_ms;

    // Update the displayed time by adding the slider value to the eclipse time
    this.model.date.setTime(new_sim_time_ms);
    this.view.current_time.setTime(new_sim_time_ms);
    $(this.view.slider).tooltip("option", "content", EclipseSimulator.get_local_time_from_date(this.view.current_time, this.view.offset, true));

    // Compute sun/moon position based off of this.model.date value
    // which is the displayed time
    var pos  = this.model.get_sun_moon_position();

    // Update the view
    this.view.update_sun_moon_pos(pos);
    this.view.refresh();

    if (EclipseSimulator.DEBUG)
    {
        console.log(
            this.model.date.toUTCString()
            + '\nlat: ' + this.model.coords.lat
            + '\nlng: ' + this.model.coords.lng
            + '\nS(alt: ' + pos.sun.alt + ' az: ' + pos.sun.az + ')'
            + '\nM(alt: ' + pos.moon.alt + ' az: ' + pos.moon.az + ')'
        );
    }

};

EclipseSimulator.Controller.prototype.update_simulator_location = function(location)
{
    if (location !== undefined)
    {
        this.model.coords = {
            lat: location.lat(),
            lng: location.lng()
        };
        parent.postMessage({simulator_location: this.model.coords}, window.location.href);
    }

    // compute the max time to be displayed on simulator
    var max_time_offset_ms = 0.5 * 1000 * 60 * EclipseSimulator.VIEW_SLIDER_NSTEPS *
        EclipseSimulator.VIEW_SLIDER_STEP_MIN[EclipseSimulator.VIEW_ZOOM_WIDE];

    // This will set the model's eclipse_time attribute
    var res = this.model.compute_eclipse_time_and_pos();
    //this.view.eclipse_time = res.getTime();

    // Set model displayed date to eclipse time
    this.model.date.setTime(res.time.getTime() - max_time_offset_ms);

    // Get new position of sun/moon
    var pos  = this.model.get_sun_moon_position();

    // Update the view
    this.view.update_sun_moon_pos(pos);
    this.view.update_eclipse_info(res);
    this.view.current_time.setTime(res.time.getTime() - max_time_offset_ms);
    this.view.reset_controls();
    this.view.update_slider();

    // Set the view slider bound sun positions
    var times     = this.view._get_slider_bound_times();
    var positions = [];
    for (var i = 0; i < times.length; i++)
    {
        positions.push(this.model._compute_sun_moon_pos(times[i]).sun);
    }
    this.view._set_slider_bound_positions(positions);


    this.view.update_fov();
    this.view.update_totality();
    this.view.refresh();
};

EclipseSimulator.Controller.prototype.start_playing = function()
{
    this.view.start_playing();

    var controller = this;
    this.current_animation_id = window.requestAnimationFrame(function(timestamp) {
        controller.previous_animation_timestamp = timestamp;
        controller._play_step(parseFloat(controller.view.slider.value) * 60 * 1000);
    });
};

EclipseSimulator.Controller.prototype.stop_playing = function() {
    window.cancelAnimationFrame(this.current_animation_id);
};

EclipseSimulator.Controller.prototype._play_step = function(offset_ms)
{
    if (this.view.stop_playing(offset_ms))
    {
        this.stop_playing();
        return;
    }

    this.view.update_slider_pos(offset_ms / 1000 / 60);
    this.update_simulator_time_with_offset(offset_ms);

    var view = this.view;
    var controller = this;
    this.current_animation_id = window.requestAnimationFrame(function(timestamp) {
        var step_ms = EclipseSimulator.VIEW_PLAY_SPEED[view.zoom_level][view.play_speed]
                      * (timestamp - controller.previous_animation_timestamp);
        controller.previous_animation_timestamp = timestamp;
        controller._play_step(offset_ms + step_ms);
    });
};


// ==============================
//
// EclipseSimulator.Model methods
//
// ==============================

EclipseSimulator.Model.prototype.init = function()
{
};

EclipseSimulator.Model.prototype.get_sun_moon_position = function()
{
    return this._compute_sun_moon_pos(this.date);
};

EclipseSimulator.Model.prototype.compute_eclipse_time_and_pos = function()
{
    // Initial date/time to begin looking for eclipse time
    var date = EclipseSimulator.ECLIPSE_DAY;
    date.setUTCHours(EclipseSimulator.ECLIPSE_WCOAST_HOUR);

    // Sun/Moon angular separation
    var prev_sep = Math.PI * 4;
    var sep      = Math.PI * 2;

    // Initial time increment of 5 minutes
    var step = 1000 * 60 * 5;

    // Set time back one step, as it will be incremented in the do while loop below, before its used
    var time = date.getTime() - step;

    // Doesn't matter
    var prev_time = 0;

    // Loop until we've reduced the step to a single second
    while (step >= 1000)
    {
        do
        {
            // Record previous iteration values
            prev_sep   = sep;
            prev_time  = time;

            // Update time for the current step
            time      += step;
            date.setTime(time);

            // Compute sun and moon position and angular separation
            var pos = this._compute_sun_moon_pos(date);
            sep     = EclipseSimulator.compute_sun_moon_sep(pos.sun, pos.moon);
        }
        while (sep < prev_sep);         // Loop until the sun/moon start getting further apart

        // Back off and reduce step
        time -= (2 * step);
        step /= 2;

        // This sets the value of prev_sep
        sep = Math.PI * 2;
    }

    // Compute eclipse position
    var pos = this._compute_sun_moon_pos(date);

    // Save eclipse time in the model
    this.eclipse_time.setTime(time);

    return {
        time: this.eclipse_time,
        az:   pos.sun.az,
        alt:  pos.sun.alt,
    };
};

EclipseSimulator.Model.prototype._compute_sun_moon_pos = function(date)
{
    var julian_date = new A.JulianDay(date);
    var coords      = A.EclCoord.fromWgs84(this.coords.lat, this.coords.lng, undefined);

    var sun = A.Solar.topocentricPosition(julian_date, coords, false);
    var moon = A.Moon.topocentricPosition(julian_date, coords, false);

    // Compute moon angular radius
    var dist = moon.delta - A.Globe.Er;
    var angular_r = Math.atan(EclipseSimulator.MOON_RADIUS / dist);

    return {
        sun: sun.hz,
        moon: {
            alt: moon.hz.alt,
            az:  moon.hz.az,
            r:   angular_r,
        },
    };
};


// ========================
//
// Simulator Initialization
//
// ========================

var global_controller = undefined;

function initSim() {

    // TEMP this is a demo - paste in a lat long from google maps
    // in the array below to position the simulator at that location!
    var c = [46.470113, -69.202133];

    var location = {
        name: 'Some location',
        coords: c,
    }

    // Makes the simulator choose the default, corvallis coords
    location = undefined;

    var controller = new EclipseSimulator.Controller(location);
    controller.init();
    parent.postMessage({simulator_status: "loaded"}, window.location.href);

    return controller;
}

/**
 * Initializes the geocode functionality and event handlers.
 */
$(function() {
    
    // 파라미터가 있으면 주소를 바로 검색한다.
    if(location.search != '') {
        var items = location.search.substr(1).split("&");

        if(items[0]=='') {
            // $("#dialog-input").dialog("open");
            return;
        }
        data = {}
        for (var index = 0; index < items.length; index++) {
            tmp = items[index].split("=");
            data[tmp[0]] = decodeURIComponent(tmp[1]);
        }
        
        // https://geocode.gimi9.com/iframe/?res_id=ebfe9a2c-63c2-4658-9475-e8ea28bc2198&file=식품제조업 2020211014.xlsx
        searchParams = new URLSearchParams(window.location.search)
        res_id = searchParams.get('res_id')
        filename = searchParams.get('file')
        
        map_preview(res_id, filename);
    };

    $("#select-sample").change(function(e, data) {
        var item_value = $("#select-sample").val();
        if (item_value == "user input") {
            $("#q").val('');
        } else {
            $.ajax({
                method: "GET",
                url: "/sample/" + item_value,
            })
            .done(function (sampleText) {
                $("#q").val(sampleText);
                $(".geocode-download").attr("value", item_value);
            });
        }
    });

    $("#chk-fail").on("change", function (event) {
        if ($(this).is(':checked'))
            $('.geocode-failed').removeClass('hide');
        else
            $('.geocode-failed').addClass('hide');
    });
    $("#chk-success").on("change", function (event) {
        if ($(this).is(':checked'))
            $('.geocode-success').removeClass('hide');
        else
            $('.geocode-success').addClass('hide');
    });

    $(".footer-a").click(function () {
        var htm;
        if ($(this).attr('id') == 'help-html')
            htm = '/static/help.html';
        else if ($(this).attr('id') == 'about-html')
            htm = '/static/about.html';
        else
            return;

        $("#dialog-html").load(htm, function () {
            $("#dialog-html").dialog("open");
        });
    })

    $("#geocode-form").on("submit", function (event) {
        $.ajax({
            method: "POST",
            url: "/api",
            data: { q: $("#q").val().trim() }
        })
        .done(function (resList) {
            render_result(resList);
        });
    });

    $("#geocode-success").on("click", function (event) {
        pos = $(ui.selected).data('pos')
        res = geocodeResults[pos];
        if (res.lat) {
            markerGroup.clearLayers();

            L.marker([res.lat, res.lng], { pos: pos })
                .addTo(markerGroup)
                .bindPopup(getPopupContents)
                .openPopup();

            if (false == map.getBounds().contains([res.lat, res.lng]))
                map.setView([res.lat, res.lng], map.zoom);
        }
    });

});


var map = L.map('map', {
    center: [37.5, 127],
    zoom: 7,
    scrollWheelZoom: true,
    zoomControl: false,
    renderer: L.canvas({ padding: 0.5 }),
    // wheelPxPerZoomLevel: 600,
    // wheelDebounceTime: 400,
});

// map.once('focus', function() { map.scrollWheelZoom.enable(); });
var markerGroup = L.featureGroup().addTo(map);
var circleGroup = L.featureGroup().addTo(map);
var geocodeResults;

L.control.zoom({
    position: 'bottomright'
}).addTo(map);

L.tileLayer('https://xdworld.vworld.kr/2d/Base/service/{z}/{x}/{y}.png', {
    // L.tileLayer('https://xdworld.vworld.kr/2d/gray/service/{z}/{x}/{y}.png', {
    // L.tileLayer('https://xdworld.vworld.kr/2d/midnight/service/{z}/{x}/{y}.png', {
    // L.tileLayer('https://xdworld.vworld.kr/2d/Satellite/service/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://xdworld.vworld.kr">브이월드</a>',
    minZoom: 6,
    maxZoom: 19
}).addTo(map);

function appendResult(res, pos) {
    let txt = res.inputaddr;
    if ((txt == undefined || txt == '') && res.lat) {
        txt = res.lat.toFixed(6) + ', ' + res.lng.toFixed(6);
    }
    
    var $li;
    if (res.lng) {
        $li = $('<li class="nav-item">' + txt + '</li>');
        $li.data({ "pos": pos });
        L.circleMarker([res.lat, res.lng], { radius: 8, fill: true, fillColor: "navy", fillOpacity: 0.9, weight: 2, pos: pos })
            .addTo(circleGroup)
            .bindPopup(getPopupContents);

        $li.click(function() {
            geocode_success_click(this);
        });
        $li.addClass('geocode-success');
    } else {
        $li = $('<li class="nav-item geocode-failed" data-bs-toggle="modal" data-bs-target="#failedModal">' + txt + '</li>');
        $li.data({ "pos": pos });

        $li.click(function() {
            geocode_fail_click(this);
        });
        $li.addClass('geocode-failed');

    }
    $("#selectable").append($li);
}

function getPopupContents(e) {  
    return getPopupContentsByPos(e.options.pos);
}

function getPopupContentsByPos(pos) {
    const res = geocodeResults[pos];
    popupText = `<b>${res.inputaddr}</b><ul class="popup-ul"><li>${res.lng.toFixed(6)}, ${res.lat.toFixed(6)}</li><li>우편번호(국가기초구역번호): ${res.z}</li><li>행정동코드: ${res.hc}</li></ul>`;
    if (res.cols) {
        colsTable = `<table class="popup-table">
        <tr>
          <th>컬럼</th>
          <th>값</th>
        </tr>
        ${Object.keys(res.cols).map(function (key) {
            return '<tr><td>' + key + '</td><td>' + res.cols[key] + '</td></tr>'
        }
        ).join("")}
        </table>`
        // popupText = popupText + '<br>' + JSON.stringify(res.cols,null,2)
        popupText = popupText + '<br>' + colsTable
    }
    return popupText
}

$(".geocode-download").click(function () {
    var filename, mime, textdata;
    const items = geocodeResults;
    filename = $(this).val();

    switch ($(this).attr('id')) {
        case "geocode-download-csv":
            {
                filename = filename + '.geocode.csv';
                mime = 'data:text/csv';
                const replacer = (key, value) => value === null ? '' : value;
                const header = ["inputaddr", "lng", "lat", "x", "y", "b", "z", "hc", "lc", "rc", "bn",];
                let csv = items.map(row => header.map(fieldName => JSON.stringify(row[fieldName], replacer)).join(','));
                csv.unshift(header.join(','));
                textdata = csv.join('\r\n');
            }
            break;

        case "geocode-download-csv-wkt":

            break;

        case "geocode-download-json":
            {
                filename = filename + '.geocode.jl';
                mime = 'data:application/json';

                let jl = items.map(row => JSON.stringify(row));
                textdata = jl.join('\r\n');
            }
            break;

        case "geocode-download-geojson":
            {
                filename = filename + '.geocode.geojson';
                mime = 'data:application/json';

                gjson = circleGroup.toGeoJSON();
                gjson.features.map((ft, i) => ft["properties"] = items[i]);

                textdata = JSON.stringify(gjson);
            }
            break;

        case "geocode-download-kml":
            {
                filename = filename + '.geocode.kml';
                mime = 'data:application/xml';

                gjson = circleGroup.toGeoJSON();
                gjson.features.map((ft, i) => ft["properties"] = items[i]);
                textdata = tokml(gjson);

            } break;

        default:
            break;
    }

    const BOM = '%ef%bb%bf';
    $("<a />", {
        "download": filename,
        "href": mime + ';charset=UTF-8,' + BOM + encodeURIComponent(textdata)
    }).appendTo("body")
        .click(function () {
            $(this).remove();
        })[0].click();
});

function geocode_success_click(e) {
    // pos = $(ui.selected).data('pos')
    pos = $(e).data('pos');
    res = geocodeResults[pos];
    if (res.lat) {
        markerGroup.clearLayers();

        L.marker([res.lat, res.lng], { pos: pos })
            .addTo(markerGroup)
            .bindPopup(getPopupContents)
            .openPopup();

        if (false == map.getBounds().contains([res.lat, res.lng]))
            map.setView([res.lat, res.lng], map.zoom);
    }
};

// click event: geocode, show result dialog
function geocode_fail_click(e) {
    pos = $(e).data('pos');
    res = geocodeResults[pos];

    $("#fail-debug").empty();
    $("#fail-debug-tks").empty();

    $('#juso-link').attr("href", 'https://www.juso.go.kr/support/AddressMainSearch.do?searchKeyword=' + res.inputaddr);
    $('#juso-link').text(res.inputaddr);

    for (x in res) {
        if (x == 'toksString') {
            tks = res[x].split('\n');
            for (k in tks) {
                $("#fail-debug-tks").append('<li class="list-group-item">' + tks[k] + '</li>');
            }
        } else {
            $("#fail-debug").append('<li class="list-group-item">' + x + ': ' + res[x] + '</li>');
        }
    }
};

/**
 * gimi9 resource Preview the map with geocode resource id and file name.
 * url: https://geocode.gimi9.com/iframe/?res_id=ebfe9a2c-63c2-4658-9475-e8ea28bc2198&file=식품제조업 2020211014.xlsx
 * 
 * @param {string} res_id - The resource ID.
 * @param {string} filename - The name of the file.
 */
function map_preview(res_id, filename, callback) {
    data = {};
    data = { res_id: res_id, file: filename };
  
    $.ajax({
      method: "POST",
      url: "https://geocode-dev.gimi9.com/api/ckan",
      data: data,
    }).done(function (resList) {
      if (resList.error != undefined) {
        $("#nav").hide();
  
        return;
      }
  
      $("#nav").show();
  
      render_result(resList);
  
      $(".geocode-download").attr("value", filename);
  
      if (callback)
        callback();
    });
  }

function render_result(resList) {
    // summray
    const totalTime = resList.total_time;
    totalCount = resList.total_count;
    successCount = resList.success_count;
    hd_successCount = resList.hd_success_count;
    summaryText = `${(totalTime).toFixed(3)}초, (${(totalCount / totalTime).toFixed(0)}건/초)`;

    $("#geocode-summary").text(summaryText);

    $("#chk-success").next().text('정상 ' + successCount + `(${(successCount / totalCount * 100).toFixed(1)}%)`);
    $("#chk-fail").next().text('오류 ' + (totalCount - successCount));

    // list
    geocodeResults = resList['results'];
    $("#selectable").empty();
    circleGroup.clearLayers();

    geocodeResults.map((res, pos) => appendResult(res, pos));
    map.fitBounds(circleGroup.getBounds(), { padding: [50, 50] });
    // $("#selectable").selectable("refresh");
    // $(".geocode-download").button("enable");

    gtag('event', 'geocode execute', {
        'app_name': 'geocoder',
        'summary': summaryText
        });
}
    //     $.ajax({
    //         method: "POST",
    //         url: "/api/ckan",
    //         // data: { res_id: res_id}
    //         data: data
    //     })
    //     .done(function (resList) {
    //         // summray
    //         const totalTime = resList.total_time;
    //         totalCount = resList.total_count;
    //         successCount = resList.success_count;
    //         if (resList.total_time) {
    //             summaryText = `${(totalTime).toFixed(3)}초, (${(totalCount/totalTime).toFixed(0)}건/초)`;
                
    //             $("#geocode-summary").text(summaryText);
    //         }

    //         // $("#chk-success").checkboxradio("option", "label", '정상 ' + successCount + `(${(successCount / totalCount * 100).toFixed(1)}%)`);
    //         // $("#chk-fail").checkboxradio("option", "label", '오류 ' + (totalCount - successCount));
    //         $("#chk-success").text('정상 ' + successCount + `(${(successCount / totalCount * 100).toFixed(1)}%)`);
    //         $("#chk-fail").text('오류 ' + (totalCount - successCount));

    //         // list
    //         geocodeResults = resList['results'];
    //         $("#selectable").empty();
    //         circleGroup.clearLayers();
    //         map.removeLayer(circleGroup);

    //         geocodeResults.map((res, pos) => appendResult(res, pos));
    //         // geocodeResults.map((res, pos) => appendResult_vw(res, pos));
    //         bnd = circleGroup.getBounds()
    //         bnd.getSouthWest().lng = Math.max(bnd.getSouthWest().lng, 123)
    //         bnd.getSouthWest().lat = Math.max(bnd.getSouthWest().lat, 32)
    //         bnd.getNorthEast().lng = Math.min(bnd.getNorthEast().lng, 133)
    //         bnd.getNorthEast().lat = Math.min(bnd.getNorthEast().lat, 39)
            
    //         // map.fitBounds(bnd, { padding: [50, 50] });
    //         map.once('moveend', function(e){map.addLayer(circleGroup);});
    //         map.flyToBounds(bnd, { padding: [50, 50], duration: 2.0 })
    //         // map.addLayer(circleGroup);
            
    //         // $("#selectable").selectable("refresh");
    //         // $(".geocode-download").button("enable");

    //         $('.geocode-download').attr('value', filename)

    //     });
    // };

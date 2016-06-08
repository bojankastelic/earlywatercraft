define([
    'jquery',
    'openlayers',
    'underscore',
    'arches',
    'map/layer-model',
    'utils'
], function($, ol, _, arches, LayerModel, utils) {
    return function(config, featureCallback) {
        config = _.extend({
            entitytypeid: 'all',
            vectorColor: '#808080'
        }, config);
        var layer = function () {
            var rgb = utils.hexToRgb(config.vectorColor);
            var zIndex = 0;
            var styleCache = {};

            var style = function(feature, resolution) {
                var mouseOver = feature.get('mouseover');
                // Nova logika velja le za skupni layer
                var ewicon = feature.get('features')[0].get('ewicon');
                if (config.entitytypeid == 'all') {
                    styleForIcon = ewicon.status + '.' + ewicon.color + '.' + ewicon.icon_type + '.' + ewicon.con_type;
                }
                var text = '1 ' + mouseOver;
                if (config.entitytypeid == 'all') {
                    text = '1 ' + styleForIcon;
                }
                
                if (!feature.get('arches_marker')) {
                    feature.set('arches_marker', true);
                }
                // Stara logika velja za vse razen skupni layer
                if (config.entitytypeid != 'all') {
                    if (styleCache[text]) {
                        return styleCache[text];
                    }
                }
                
                var iconSize = mouseOver ? 38 : 32;
                
                // Stara logika
                var iconText = arches.resourceMarker.icon
                var statusStyle = null;
                var ewStyle = null;
                // Nova logika za določanje ikone
                if (config.entitytypeid == 'all') {
                    iconText = ewicon.icon_type;
                    //console.log(ewicon);
                    ew_rgb = utils.hexToRgb(ewicon.color);
                   
                    ewStyle = new ol.style.Style({
                        text: new ol.style.Text({
                            text: iconText,
                            font: 'normal ' + iconSize*4/3 + 'px Flaticon',
                            offsetY: (iconSize*3/5)*-1,
                            stroke: new ol.style.Stroke({
                                color: 'white',
                                width: 5
                            }),
                            fill: new ol.style.Fill({
                                color: 'rgba(' + ew_rgb.r + ',' + ew_rgb.g + ',' + ew_rgb.b + ',0.9)',
                            })
                        }),
                        zIndex: mouseOver ? zIndex*3000000000 : zIndex+1
                    });
                   
                    if (ewicon.status != '') {
                        statusStyle = new ol.style.Style({
                            text: new ol.style.Text({
                                text: ewicon.status,
                                font: 'normal ' + iconSize/2 + 'px ' + arches.resourceMarker.font,
                                offsetX: (iconSize*2/7)*-1,
                                offsetY: (iconSize*6/6)*-1,
                                stroke: new ol.style.Stroke({
                                    color: 'white',
                                    width: 4
                                }),
                                fill: new ol.style.Fill({
                                    color: 'red',
                                })
                            }),
                            zIndex: mouseOver ? zIndex*4000000000 : zIndex+1
                        });
                    }
                    if (ewicon.con_type != '') {
                        constructionStyle = new ol.style.Style({
                            text: new ol.style.Text({
                                text: ewicon.con_type,
                                font: 'bold ' + iconSize/3 + 'px ' + arches.resourceMarker.font,
                                offsetX: (iconSize*3/7)*1,
                                offsetY: (iconSize*6/6)*-1,
                                stroke: new ol.style.Stroke({
                                    color: 'white',
                                    width: 4
                                }),
                                fill: new ol.style.Fill({
                                    color: 'gray',
                                })
                            }),
                            zIndex: mouseOver ? zIndex*4000000000 : zIndex+1
                        });
                    }
                }
                var styles = [new ol.style.Style({
                    text: new ol.style.Text({
                        text: arches.resourceMarker.icon,
                        font: 'normal ' + iconSize + 'px ' + arches.resourceMarker.font,
                        offsetX: 5,
                        offsetY: ((iconSize/2)*-1)-5,
                        fill: new ol.style.Fill({
                            color: 'rgba(126,126,126,0.3)',
                        })
                    }),
                    zIndex: mouseOver ? zIndex*1000000000: zIndex
                }), new ol.style.Style({
                    text: new ol.style.Text({
                        text: arches.resourceMarker.icon,
                        font: 'normal ' + iconSize + 'px ' + arches.resourceMarker.font,
                        offsetY: (iconSize/2)*-1,
                        stroke: new ol.style.Stroke({
                            color: 'white',
                            width: 3
                        }),
                        fill: new ol.style.Fill({
                            color: 'rgba(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ',0.9)',
                        })
                    }),
                    zIndex: mouseOver ? zIndex*2000000000 : zIndex+1
                })];
                if (config.entitytypeid == 'all') {
                    styles.push(ewStyle);
                    if (ewicon.status != '') {
                        styles.push(statusStyle);
                    }
                    if (ewicon.con_type != '') {
                        styles.push(constructionStyle);
                    }
                }

                zIndex += 2;

                styleCache[text] = styles;
                return styles;
            };

            var layerConfig = {
                projection: 'EPSG:3857'
            };

            if (config.entitytypeid !== null) {
                layerConfig.url = arches.urls.map_markers + config.entitytypeid;
            }

            var source = new ol.source.GeoJSON(layerConfig);
            $('.map-loading').show();
            var loadListener = source.on('change', function(e) {
                if (source.getState() == 'ready') {
                    if(typeof(featureCallback) === 'function'){
                        featureCallback(source.getFeatures());
                    }
                    ol.Observable.unByKey(loadListener);
                    $('.map-loading').hide();
                }
            });

            var clusterSource = new ol.source.Cluster({
                distance: 45,
                source: source
            });

            var clusterStyle = function(feature, resolution) {
                var size = feature.get('features').length;
                // Nova logika velja le za skupni layer
                if (config.entitytypeid == 'all') {
                    styleForIcon = '.cluster';
                    if (size == 1) {
                        ewicon = feature.get('features')[0].get('ewicon');
                        styleForIcon = ewicon.status + '.' + ewicon.color + '.' + ewicon.icon_type + '.' + ewicon.con_type;
                    }
                }
                var mouseOver = feature.get('mouseover');
                var text = size + ' ' + mouseOver;
                if (config.entitytypeid == 'all') {
                    text = size + ' ' + styleForIcon;
                }
                if (!feature.get('arches_cluster')) {
                    feature.set('arches_cluster', true);
                }
                //console.log(text);
                if (styleCache[text]) {
                    return styleCache[text];
                }

                var radius = mouseOver ? 12 : 10;

                if (size === 1) {
                    return style(feature, resolution);
                }

                if (size > 200) {
                    radius = mouseOver ? 20 : 18;
                } else if (size > 150) {
                    radius = mouseOver ? 18 : 16;
                } else if (size > 100) {
                    radius = mouseOver ? 16 : 14;
                } else if (size > 50) {
                    radius = mouseOver ? 14 : 12;
                }

                var styles = [new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: radius,
                        stroke: new ol.style.Stroke({
                            color: 'rgba(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ',0.4)',
                            width: radius
                        }),
                        fill: new ol.style.Fill({
                            color: 'rgba(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ',0.8)',
                        })
                    }),
                    text: new ol.style.Text({
                        text: size.toString(),
                        fill: new ol.style.Fill({
                            color: '#fff'
                        })
                    })
                })];
                styleCache[text] = styles;
                return styles;
            };

            var clusterLayer = new ol.layer.Vector({
                source: clusterSource,
                style: clusterStyle
            });
            
            clusterLayer.vectorSource = source;
            clusterLayer.set('is_arches_layer', true);

            return clusterLayer;
        };

        return new LayerModel(_.extend({
                layer: layer,
                onMap: true,
                isArchesLayer: true
            }, config)
        );
    };
});

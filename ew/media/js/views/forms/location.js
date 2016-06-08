define([
    'jquery',
    'underscore',
    'arches',
    'knockout', 
    'knockout-mapping', 
    'views/forms/base',
    'views/forms/sections/branch-list',
    'views/forms/sections/location-branch-list',
    'summernote'
], function ($, _, arches, ko, koMapping, BaseForm, BranchList, LocationBranchList) {
    return BaseForm.extend({
        events: function(){
            /*
            return {
                'change .state': 'stateChanged',
                'change .region': 'regionChanged'
            }
            */
	        var events = BaseForm.prototype.events.apply(this);
            events['change #select-state'] = 'stateChanged';
            events['change #select-region'] = 'regionChanged';
            return events;
        },
        initialize: function() {
            var self = this;
            var resourcetypeid = $('#resourcetypeid').val();
            var includeMap = (resourcetypeid !== 'ACTOR.E39');
            var includeParcels = !_.contains(['ACTOR.E39', 'ACTIVITY.E7', 'HISTORICAL_EVENT.E5'], resourcetypeid);
            var includeSettlementType = !_.contains(['ACTOR.E39', 'ACTIVITY.E7', 'HISTORICAL_EVENT.E5'], resourcetypeid);

            BaseForm.prototype.initialize.apply(this);

            this.region_coordinates = JSON.parse(this.form.find('#region_coordinates').val());
            //console.log(this.region_coordinates["Central Slovenia"]);
            //if (this.region_coordinates["Central Slovenia"]) {
            //    console.log(this.region_coordinates["Central Slovenia"]["minX"]);
            //}
            if (includeMap) {
                var locationBranchList = new LocationBranchList({
                    el: this.$el.find('#geom-list-section')[0],
                    data: this.data,
                    dataKey: 'SPATIAL_COORDINATES_GEOMETRY.E47'
                });
                this.lBL = locationBranchList;
                this.addBranchList(locationBranchList);
            }


            if (includeParcels) {
                this.addBranchList(new BranchList({
                    el: this.$el.find('#parcel-section')[0],
                    data: this.data,
                    dataKey: 'PLACE_APPELLATION_CADASTRAL_REFERENCE.E44',
                    validateBranch: function (nodes) {
                        return this.validateHasValues(nodes);
                    }	
                }));
            }

            this.addressBranchList = this.addBranchList(new BranchList({
                el: this.$el.find('#address-section')[0],
                data: this.data,
                dataKey: 'PLACE_ADDRESS.E45',
                validateBranch: function (nodes) {
                    return this.validateHasValues(nodes);
                }	
            }));

            this.addBranchList(new BranchList({
                el: this.$el.find('#description-section')[0],
                data: this.data,
                dataKey: 'DESCRIPTION_OF_LOCATION.E62',
                singleEdit: true
            }));
            if (includeMap) {
                this.regionBranchList = this.addBranchList(new BranchList({
                    el: this.$el.find('#region-section')[0],
                    data: this.data,
                    dataKey: 'REGION.E55',
                    singleEdit: true,
                    validateBranch: function (nodes) {
                        return this.validateHasValues(nodes);
                    }		
                }));
            }
            if (includeSettlementType) {
                this.addBranchList(new BranchList({
                    el: this.$el.find('#settlement-type-section')[0],
                    data: this.data,
                    dataKey: 'SETTLEMENT_TYPE.E55',
                    singleEdit: true,
                    validateBranch: function (nodes) {
                        if (resourcetypeid == 'HERITAGE_RESOURCE.E18') {
                            return this.validateHasValues(nodes);
                        } else {
                            return true;
                        }
                    }		
                }));
                this.addBranchList(new BranchList({
                    el: this.$el.find('#context-section')[0],
                    data: this.data,
                    dataKey: 'CONTEXT.E55',
                    singleEdit: true,
                    validateBranch: function (nodes) {
                        if (resourcetypeid == 'HERITAGE_RESOURCE.E18') {
                            return this.validateHasValues(nodes);
                        } else {
                            return true;
                        }
                    }		
                }));
            }
        },
        stateChanged: function(evt) {
            console.log('Sprememba države');
            //var error = new Error();
	    	//console.log(error.stack);
            var valueState = this.$el.find('#select-state').val();
            var valueRegion = this.$el.find('#select-region').val();
			console.log('Izbrana država ID: ' + valueState);
	        var state = '-';
	        _.each(this.regionBranchList.viewModel.branch_lists(), function(branch) {
	             _.each(branch.nodes(), function (node) {
	                 if (node.entitytypeid() === "STATE.E55" && valueState === node.value()) {
	                    state = node.label();
	                    console.log('Izbrana država: ' + node.label() + '(node.value: ' + node.value() + ')');
					 }
				});
        	});
            var domains = koMapping.fromJS(this.data['REGION.E55'].domains['REGION.E55']);
	    	var newValues = [];
            var regijaVpisana = !(valueRegion === '');
	    	if (!regijaVpisana) {
				console.log('Regija še ni vpisana.');
	    	}
            var regijaZnotrajDrzave = false;
            self = this;
            _.each(domains(), function(item){
				if (item.text() === state) {
                	var regionsForState = item.children();
                	_.each(regionsForState, function(item){
                   		//console.log(item.text());
                      	if (regijaVpisana && valueRegion === item.id()) {
							regijaZnotrajDrzave = true;
			 				console.log('Izbrana regija je že znotraj izbrane države.');
		      			}
                      	newValues.push({
                          	id: item.id(),
                          	text: item.text(),
                          	value: item.id(),
                          	label: item.text(),
                          	entitytypeid: 'REGION.E55'
                     	});
                   	});
		   			if (regijaVpisana && !regijaZnotrajDrzave) {
						console.log('Izbrana regija je izven izbrane države, zato jo pobrišemo.');
						$('#select-region').select2('data', {id: '', text: '', value: '', label: '', entitytypeid: 'REGION.E55'}, false);
						rbl = self.regionBranchList;
				        var editingBranch = rbl.getEditedBranch();
                        _.each(editingBranch.nodes(), function (node) {
                            if (node.entitytypeid() == 'REGION.E55') {
                                node.entityid('');
                                node.label('');
                                node.value('');
                            }
                            node.value.subscribe(function () {
                                rbl.trigger('change', 'edit', editingBranch);
                            });
                        });
		   			}
                }
			});      
	    	//console.log(newValues);
            if (!regijaVpisana || !regijaZnotrajDrzave) {
	    		$('#select-region').select2("destroy").select2({data: newValues}).trigger('change');
				console.log('Nove vrednosti za regijo so vpisane!');
				// Izbrišemo še entity id za regijo (da se javi validation error)
				rbl = self.regionBranchList;
				var editingBranch = rbl.getEditedBranch();
                _.each(editingBranch.nodes(), function (node) {
                    if (node.entitytypeid() == 'REGION.E55' && node.value() == '') {
                        node.entityid('');
                    }
                    node.value.subscribe(function () {
                        rbl.trigger('change', 'edit', editingBranch);
                    });
                });
	    	}
	    	if (this.region_coordinates[state]) {
                this.lBL.zoomRegion(this.region_coordinates[state]);
            } else {
                console.log('Error: state ' + state + ' has no coordinates defined!');
            }
        },
        regionChanged: function(evt) {
            console.log('Sprememba regije');
            var valueRegion = this.$el.find('#select-region').val();
	    	var valueState = this.$el.find('#select-state').val();
 	    	var region = '';
            var state = '';
	    	var drzavaVpisana = !(valueState === '');
            console.log('Izbrana regija ID: ' + valueRegion);
     	    if (valueRegion !== '') {
				_.each(this.regionBranchList.viewModel.branch_lists(), function(branch) {
	            	_.each(branch.nodes(), function (node) { 
                    	if (node.entitytypeid() === "REGION.E55" && valueRegion == node.value()) {
	                    	region = node.label();
	                    	console.log('Izbrana regija: ' + node.label());
      		         	}
		    		});
	        	});
	    	}
	    	if (!drzavaVpisana) {
	        	console.log('Država še ni vpisana.');
	    	} else {
				_.each(this.regionBranchList.viewModel.branch_lists(), function(branch) {
			         _.each(branch.nodes(), function (node) { 
		             	if (node.entitytypeid() === "STATE.E55" && valueState == node.value()) {
			            	state = node.label();
			                console.log('Izbrana država: ' + node.label());
		  		        }
					});
			    });
			}
			var domains = koMapping.fromJS(this.data['REGION.E55'].domains['REGION.E55']);
			var newValues = [];
			var CurrStateText = '';
			var found = false;
            if (valueRegion !== '') {
	        	_.each(domains(), function(item){
	            	var State = '-';
	            	if (!found) {
	               		CurrStateText = item.text();
	               		var regionsForState = item.children();
	               		_.each(regionsForState, function(item){
	                  		if (item.text() === region) {
	                     		found = true;
	                  		}
	               		});
		    		}
	        	});
	        	if (drzavaVpisana && found && CurrStateText !== state) {
		    		console.log('Država je že bila vpisana, vendar je drugačna od izbrane regije (' + CurrStateText + '!=' + state + ')');
	        	}
	        	if (!drzavaVpisana || (drzavaVpisana && found && CurrStateText !== state)) {
	           		if (found) {
                    	var CurrStateId = '';
	               		console.log('Parent state: ' + CurrStateText);
						_.each(this.regionBranchList.viewModel.branch_lists(), function(branch) {
			     			_.each(branch.nodes(), function (node) { 
		                 		if (node.entitytypeid() === "STATE.E55" && CurrStateText == node.value()) {
			            			CurrStateId = node.value();
	      		         		}
			    			});
						});
	               		console.log('Id: ' + CurrStateId+ ', Text: ' + CurrStateText);
	               		$('#select-state').select2('data', {id: CurrStateId, text: CurrStateText}, false);
	           		} else {
		       			console.log('Parent država za regijo ' + region + ' ni bila najdena!');
	           		}
	       		} else {
 	           		console.log('Država je že bila vpisana.');
	       		}
	    	}
	    	if (region !== '') {
            	if (this.region_coordinates[region]) {
                    this.lBL.zoomRegion(this.region_coordinates[region]);
                } else {
                    console.log('Error: region ' + region + ' has no coordinates defined!');
                }
            	
	    	}
        }
    });
});

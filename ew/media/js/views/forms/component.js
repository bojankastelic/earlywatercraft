define(['jquery', 
    'underscore', 
    'summernote', 
    'knockout-mapping', 
    'views/forms/base', 
    'views/forms/sections/branch-list',
    'knockout', 
    'bootstrap-datetimepicker'], function ($, _, summernote, koMapping, BaseForm, BranchList, ko) {
    return BaseForm.extend({
		events: function(){
        	var events = BaseForm.prototype.events.apply(this);
        	    events['change #select-material'] = 'materialChanged';
        	    events['change #select-material-type'] = 'materialTypeChanged';
        	    return events;
        },
       	initialize: function() {
            BaseForm.prototype.initialize.apply(this);
            this.blocked = false;
            self = this;
            this.componentBranchList = this.addBranchList(new BranchList({
                el: this.$el.find('#component-section')[0],
                data: this.data,
                dataKey: 'COMPONENT.E18',
                validateBranch: function (nodes) {
                    return this.validateHasValues(nodes);
                },
                addItem: function() {
                    var branch = this.getEditedBranch();
                    var validationAlert = this.$el.find('.branch-invalid-alert');
                    if (this.validateBranch(ko.toJS(branch.nodes))) {
                        var branch = this.getEditedBranch();
                        branch.editing(false);
                        this.addBlankEditBranch();
                        this.originalItem = null;

                        this.trigger('change', 'add', branch);
                        // Logika, ki izklopi osveževanje povezanih DDDW, izbriše njihove vrednosti in napolni master detail na začetne vrednosti (zaradi placehoderja, ki se sicer izbriše)
                        self.blocked = true;
                        var master_list = 'MATERIAL.E57';
                        var detail_list = 'MATERIAL_TYPE.E57';
                        var data_key = 'COMPONENT.E18';
                        var master_id = '#select-material';
                        var detail_id = '#select-material-type';
                        var master_placeholder = 'Material';
                        var detail_placeholder = 'Material type';
                        var newValuesM = [];
                        var newValuesD = [];
                        var domainsM = koMapping.fromJS(this.data[data_key].domains[master_list]);
	    	            _.each(domainsM(), function(item){
		                  	console.log(item.text());
		                  	newValuesM.push({
                              	id: item.id(),
                              	text: item.text(),
                              	value: item.id(),
                              	label: item.text(),
                              	entitytypeid: master_list
                         	});
                        });
                        $(master_id).select2("destroy").select2({data: newValuesM, placeholder: master_placeholder}).trigger('change');
                        $(detail_id).select2('data', {id: '', text: '', value: '', label: '', entitytypeid: detail_list}, false);
                        // Vklopimo nazaj osveževanje
                        self.blocked = false;
                    } else {
                        validationAlert.show(300);
                        setTimeout(function() {
                            validationAlert.fadeOut();
                        }, 5000);
                    }
                },
            }));

        },
        materialChanged: function(evt) {
            if (this.blocked) {
                return;
            }
            console.log('Sprememba materiala');
            var master_id = '#select-material';
            var detail_id = '#select-material-type';
            var data_key = 'COMPONENT.E18';
            var master_list = 'MATERIAL.E57'
            var detail_list = 'MATERIAL_TYPE.E57'
			var valueMaster = this.$el.find(master_id).val();
            var valueDetail = this.$el.find(detail_id).val();
            console.log('Izbran master ID: ' + valueMaster);
	        var master = '-';
	        _.each(this.componentBranchList.viewModel.branch_lists(), function(branch) {
	             _.each(branch.nodes(), function (node) {
	                 if (node.entitytypeid() === master_list && valueMaster === node.value()) {
	                    master = node.label();
	                    console.log('Izbran master: ' + node.label() + '(node.value: ' + node.value() + ')');
					 }
				});
        	});
            var domains = koMapping.fromJS(this.data[data_key].domains[detail_list]);
	    	var newValues = [];
            var detailVpisan = !(valueDetail === '');
	    	if (!detailVpisan) {
				console.log('Detail še ni vpisan.');
	    	}
            var detailZnotrajMastra = false;
            _.each(domains(), function(item){
				if (item.text() === master) {
                	var detailsForMaster = item.children();
                	_.each(detailsForMaster, function(item){
                   		if (detailVpisan && valueDetail === item.id()) {
							detailZnotrajMastra = true;
			 				console.log('Izbrana detail je že znotraj izbranega mastra.');
		      			}
                      	newValues.push({
                          	id: item.id(),
                          	text: item.text(),
                          	value: item.id(),
                          	label: item.text(),
                          	entitytypeid: detail_list
                     	});
                   	});
		   			if (detailVpisan && !detailZnotrajMastra) {
						console.log('Izbrana detail je izven izbranega mastra, zato ga pobrišemo.');
						$(detail_id).select2('data', {id: '', text: '', value: '', label: '', entitytypeid: detail_list}, false);
		   			}
                }
			});      
	    	if (!detailVpisan || !detailZnotrajMastra) {
	    		$(detail_id).select2("destroy").select2({data: newValues}).trigger('change');
				console.log('Nove vrednosti za detail so vpisane!');
	    	}
        },
        materialTypeChanged: function(evt) {
            if (this.blocked) {
                return;
            }
            console.log('Sprememba tipa materiala');
            var master_id = '#select-material';
            var detail_id = '#select-material-type';
			var data_key = 'COMPONENT.E18';
            var master_list = 'MATERIAL.E57'
            var detail_list = 'MATERIAL_TYPE.E57'
            var valueDetail = this.$el.find(detail_id).val();
	    	var valueMaster = this.$el.find(master_id).val();
 	    	var detail = '';
            var master = '';
	    	var masterVpisan = !(valueMaster === '');
            console.log('Izbran detail ID: ' + valueDetail);
     	    if (valueDetail !== '') {
				_.each(this.componentBranchList.viewModel.branch_lists(), function(branch) {
	            	_.each(branch.nodes(), function (node) { 
                    	if (node.entitytypeid() === detail_list && valueDetail == node.value()) {
	                    	detail = node.label();
	                    	console.log('Izbran detail: ' + node.label());
      		         	}
		    		});
	        	});
	    	}
	    	if (!masterVpisan) {
	        	console.log('Master še ni vpisan.');
	    	} else {
				_.each(this.componentBranchList.viewModel.branch_lists(), function(branch) {
			         _.each(branch.nodes(), function (node) { 
		             	if (node.entitytypeid() === master_list && valueMaster == node.value()) {
			            	master = node.label();
			                console.log('Izbran master: ' + node.label());
		  		        }
					});
			    });
			}
			var domains = koMapping.fromJS(this.data[data_key].domains[detail_list]);
			var newValues = [];
			var CurrMasterText = '';
			var found = false;
            if (valueDetail !== '') {
	        	// Najprej poiscemo, ce se detail nahaja v okviru trenutnega mastra (zaradi primera, ce se detaili ponavljajo)	
            	_.each(domains(), function(item){
	            	if (!found) {
	               		CurrMasterText = item.text();
						if (CurrMasterText === master) {	               		
							var detailsForMaster = item.children();
			           		_.each(detailsForMaster, function(item){
			              		if (item.text() === detail) {
			                 		found = true;
			              		}
			           		});
						}
		    		}
	        	});
				// Ce ga se nismo naslo, gremo cez vse
				if (!found) {
					_.each(domains(), function(item){
			        	if (!found) {
			           		CurrMasterText = item.text();
			           		var detailsForMaster = item.children();
			           		_.each(detailsForMaster, function(item){
			              		if (item.text() === detail) {
			                 		found = true;
			              		}
			           		});
						}
			    	});
				}
	        	if (masterVpisan && found && CurrMasterText !== master) {
		    		console.log('Master je že bil vpisana, vendar je drugačen od izbranega detaila (' + CurrMasterText + '!=' + master + ')');
	        	}
	        	if (!masterVpisan || (masterVpisan && found && CurrMasterText !== master)) {
	           		if (found) {
                    	var CurrMasterId = '';
	               		console.log('Parent master: ' + CurrMasterText);
						_.each(this.componentBranchList.viewModel.branch_lists(), function(branch) {
			     			_.each(branch.nodes(), function (node) { 
		                 		if (node.entitytypeid() === master_list && CurrMasterText == node.value()) {
			            			CurrMasterId = node.value();
	      		         		}
			    			});
						});
	               		console.log('Id: ' + CurrMasterId+ ', Text: ' + CurrMasterText);
	               		$(master_id).select2('data', {id: CurrMasterId, text: CurrMasterText}, false);
	           		} else {
		       			console.log('Parent za detail ' + detail + ' ni bil najden!');
	           		}
	       		} else {
 	           		console.log('Parent je že bila vpisan.');
	       		}
	    	}
        }
    });
});

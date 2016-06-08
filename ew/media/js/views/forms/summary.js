define(['jquery', 
    'underscore', 
    'knockout', 
    'knockout-mapping', 
    'views/forms/base', 
    'views/forms/sections/branch-list',
    'bootstrap-datetimepicker',], 
    function ($, _, ko, koMapping, BaseForm, BranchList) {
        return BaseForm.extend({
            initialize: function() {
                BaseForm.prototype.initialize.apply(this);                
                
                //console.log(this.data);
                
                var self = this;
                var date_picker = $('.datetimepicker').datetimepicker({pickTime: false});
                date_picker.on('dp.change', function(evt){
                    $(this).find('input').trigger('change'); 
                });
                this.addBranchList(new BranchList({
                    el: this.$el.find('#heritage-type-section')[0],
                    data: this.data,
                    dataKey: 'RESOURCE_TYPE_CLASSIFICATION.E55',
                    singleEdit: true,
                    validateBranch: function (nodes) {
                        //console.log(this.viewModel.branch_lists().length);
                        if (resourcetypeid.value == 'HERITAGE_RESOURCE.E18') {
                            return this.validateHasValues(nodes);
                        } else {
                            return true;
                        }
                    }//,
                    // onSelect2Selecting: function(item, select2Config){
                    //     _.each(this.editedItem(), function(node){
                    //         if (node.entitytypeid() === select2Config.dataKey){
                    //             var labels = node.label().split(',');
                    //             if(node.label() === ''){
                    //                 node.label(item.value);
                    //             }else{
                    //                 if(item.value !== ''){
                    //                     labels.push(item.value);
                    //                 }
                    //                 node.label(labels.join());
                    //             }
                    //             //node.value(item.id);
                    //             node.entitytypeid(item.entitytypeid);
                    //         }
                    //     }, this);
                    //     this.trigger('change', 'changing', item);
                    //}
                }));
                this.addBranchList(new BranchList({
                    el: this.$el.find('#names-section')[0],
                    data: this.data,
                    dataKey: 'NAME.E41',
                    validateBranch: function (nodes) {
                        var valid = true;
                        var primaryname_count = 0;
                        var primaryname_conceptid = this.data['primaryname_conceptid'];
                        _.each(nodes, function (node) {
                            //if (node.entitytypeid === 'NAME.E41') {
                                if (node.value === ''){
                                    valid = false;
                                }
                            //}
                            if (node.entitytypeid === 'NAME_TYPE.E55') {
                                if (node.value === primaryname_conceptid){
                                    _.each(this.viewModel.branch_lists(), function (branch_list) {
                                        _.each(branch_list.nodes(), function (node1) {
                                            if (node1.entitytypeid() === 'NAME_TYPE.E55' && node1.value() === primaryname_conceptid) {
                                                primaryname_count = primaryname_count + 1;
                                            }
                                        }, this);
                                    }, this);
                                }
                            }
                        }, this);
                        if (primaryname_count>1) {
                            valid = false;
                        }
                        return valid;
                    }
                }));
                if (resourcetypeid.value == 'HERITAGE_RESOURCE.E18') {
                    this.addBranchList(new BranchList({
                        el: this.$el.find('#xref-section')[0],
                        data: this.data,
                        dataKey: 'EXTERNAL_RESOURCE.E1',
                        validateBranch: function(nodes){
                            return this.validateHasValues(nodes);
                        },
                        isUrl: function(value) {
                            return /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(value);
                        },
                        getLink: function(value) {
                            if (/^https?:\/\//.test(value)) {
                                return value;
                            } else {
                                return 'http://' + value;
                            }
                        }
                    }));
                }
            }      
        });
    }
);

define(['jquery', 'backbone', 'knockout', 'underscore', 'views/forms/sections/branch-list', 'plugins/knockout-select2', 'plugins/knockout-summernote',
    ], function ($, Backbone, ko, _, BranchList) {
    return Backbone.View.extend({
        
        events: function(){
            return {
                'click .save-edits': 'submit',
                'click .cancel-edits': 'cancel'
            }
        },

        constructor: function (options) {
            var self = this;
            this.branchLists = [];

            ko.observableArray.fn.get = function(entitytypeid, key) {
                var allItems = this();
                var ret = '';
                _.filter(allItems, function(node){
                    if ('entitytypeid' in node && entitytypeid.search(node.entitytypeid()) > -1){
                        ret = node[key]();
                        return true;
                    }
                }, this);
                return ret
            }

            Backbone.View.apply(this, arguments);
            
            return this;
        },

        initialize: function() {
            var self = this;
            this.form = this.$el;
            // parse then restringify JSON data to ensure whitespace is identical
            this._rawdata = ko.toJSON(JSON.parse(this.form.find('#formdata').val()));
            this.data = JSON.parse(this._rawdata);

            // $('input,select').change(function() {
            //     var isDirty = self.isDirty();
            //     self.trigger('change', isDirty);
            // });

            this.on('change', function(eventtype, item){
                $('.save-edits').removeClass('disabled');
                $('.cancel-edits').removeClass('disabled');                    
            });
            
            user_can_edit = $("#user_can_edit_document").val();
            if (user_can_edit == "False") {
                $("#resource_data_management_form :input").prop('readonly', true);
                $('.select2').addClass('disabled');
                $('.btn').addClass('disabled');
                $('.arches-CRUD-child').addClass('disabled');
                $('.arhces-HTML-editor').prop('hidden', true);
            }
            //$('#collapse-others-resource').collapse('hide');
            //console.log('Others-resource - collapsed');
            this.$el.find('.form-load-mask').hide();
            this.addBranchList(new BranchList({
                el: this.$el.find('#status-section')[0],
                data: this.data,
                dataKey: 'EW_STATUS.E55',
                singleEdit: true,
                validateBranch: function (nodes) {
                    return this.validateHasValues(nodes);
                }
            }));
            this.addBranchList(new BranchList({
                el: this.$el.find('#group-section')[0],
                data: this.data,
                dataKey: 'EW_GROUP.E62',
                singleEdit: true,
                validateBranch: function (nodes) {
                    return this.validateHasValues(nodes);
                }
            }));
        },

        addBranchList: function(branchList){
            var self = this;
            this.branchLists.push(branchList);
            this.listenTo(branchList, 'change', function(eventtype, item){
                self.trigger('change', eventtype, item);                 
            });
            return branchList;
        },

        isDirty: function () {
            // var viewModel = JSON.parse(ko.toJSON(this.viewModel));
            // for(branch in ko.toJS(this.viewModel)){
            //     if(branch !== 'domains' && branch !== 'defaults' && branch !== 'editing'){
            //         for(index in viewModel[branch]){
            //             for(item in viewModel[branch][index]){
            //                 if(item.indexOf('entityid') > 0){
            //                     if(viewModel[branch][index][item] === ''){
            //                         return true;
            //                         break;
            //                     }
            //                 }                            
            //             }
            //         }                    
            //     }
            // }
            return this.getData(true) !== this._rawdata;
        },

        getData: function(includeDomains){
            var data = {};
            _.each(this.branchLists, function(branchList){
                data[branchList.dataKey] = branchList.getData();
            }, this);  
            return ko.toJSON(data);
        },

        /* */
        validate: function(){
            var isValid = true
            _.each(this.branchLists, function(branchList){
                isValidBranch = branchList.validate();
		        isValid = isValid && isValidBranch;
		        if (!isValidBranch) {
                    var validationAlert = branchList.$el.find('.branch-invalid-alert');
                    console.log(validationAlert);
                    validationAlert.show(300);
                    setTimeout(function() {
                        validationAlert.fadeOut();
                    }, 5000);
                }
            }, this); 
            
            return isValid;
        },
        /*
        submit: function(evt){
            var validationAlert = this.$el.find('.branch-invalid-alert');
            evt.preventDefault();
            if (this.validate()){
                this.$el.find('.save-edits,.cancel-edits').addClass('disabled');
	            this.form.find('#formdata').val(this.getData());
                this.form.submit(); 
            } 
        },
        */
        /*
        validate: function(){
            var isValid = true
            _.each(this.branchLists, function(branchList){
                isValid = isValid && branchList.validate();
            }, this); 
            return isValid;
        },
        */

        /**
         * Displays alert message in a specified branchlist section of a form
         * @param {Object} 
         * @return {Boolean} 
         */ 
        showAlert: function(branchList) {
            var validationAlert = branchList.$el.find('.branch-invalid-alert');
            validationAlert.show(300);
            setTimeout(function() {
                validationAlert.fadeOut();
                }, 6500);
        },

        /**
         * Checks whether all branchlists where the required rule is true, have form data to submit.
         * @return {Boolean} 
         */ 
        checkForRequiredBranchlists: function() {
            var isValid = true
            _.each(this.branchLists, function(branchList){
                if (branchList.rules.required === true && branchList.getData().length === 0 && branchList.singleEdit === false) {
                    isValid = false;
                    this.showAlert(branchList);
                } else if (branchList.rules.required === true && branchList.singleEdit === true) {
                    if (branchList.getData().length === 0) {
                        isValid = false;
                    } else {
                        _.each(branchList.getData(), function(nodes) {
                            _.each(nodes, function(node) {
                                _.each(node, function(n) {
                                    if (n.value === '') {
                                        isValid = false;
                                        this.showAlert(branchList);
                                    }
                                }, this)
                            }, this)
                        }, this)
                    }
                }
            }, this); 
            return isValid;
        },
           
        /**
         * Performs form validation by calling methods that evaluate branchlist rules.
         * @return {Boolean} 
         */ 
        validateForm: function(){
            var isValid = true
            isValid = this.checkForRequiredBranchlists();
            return isValid;
        },

        /**
         * Ensures all of the branch lists in the form have rule properties so that rule based validation can be run on the entire form
         * @return {Boolean} 
         */
        checkForRules: function(){
            var hasRules = true;
            _.each(this.branchLists, function(branchList){
                if (!branchList.rules) {
                    hasRules = false;
                }
            }, this); 
            return hasRules;
        },

        submit: function(evt){
            evt.preventDefault();
            var rules = this.checkForRules();
            this.validationMethod = rules ? this.validateForm : this.validate; //the branchlists of some forms may not have rules. In those cases we use the default validate method
            if (this.validationMethod()){
                this.form.find('#formdata').val(this.getData());
                this.form.submit(); 
            }
        },

        cancel: function(evt){
            _.each(this.branchLists, function(branchList){
                branchList.undoAllEdits();
            }, this);  
        }
    });
});

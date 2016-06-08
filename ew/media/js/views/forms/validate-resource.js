define(['jquery', 
    'underscore', 
    'knockout', 
    'knockout-mapping', 
    'views/forms/base', 
    'views/forms/sections/branch-list',
    'bootstrap-datetimepicker',
    'summernote'], 
    function ($, _, ko, koMapping, BaseForm, BranchList) {
		return BaseForm.extend({
		    events: function(){
		        var events = BaseForm.prototype.events.apply(this);
                events['click .validate-resource-btn'] = 'validateResource';
                events['click #btn-send-mail,#btn-return-to-draft,#btn-publish'] = 'submit';
                events['click #btn-ready-for-approval'] = 'del_rej_desc_and_submit';
                
                return events;
		    },
			initialize: function() {
		        this.$el.find('.form-load-mask').hide();

				BaseForm.prototype.initialize.apply(this);                
		
				var self = this;
				
				console.log(this.data);
                this.descBL = this.addBranchList(new BranchList({
					el: this.$el.find('#description-section')[0],
					data: this.data,
					dataKey: 'EW_REJECT_DESCRIPTION.E62',
                    singleEdit: true
				}));
				self = this
				_.each(this.descBL.viewModel.branch_lists(), function(branch) {
	                 _.each(branch.nodes(), function (node) {
	                     console.log(node.value());
	                     if (node.entitytypeid() === "EW_REJECT_DESCRIPTION.E62" && node.value() != '') {
	                        self.$el.find('#lastRejectedDescription').removeClass('hidden');
					     }
				    });
            	});
                $('#btn-return-to-draft').removeClass('disabled');
			},
			validateResource: function() {
			    $.ajax({
			        method: 'GET',
			        url: '',
			        success: function() {
			            location.href = arches.urls.home;
			        }
			    });
			},
	        del_rej_desc_and_submit: function(evt){
	            self = this;
	            this.descBL.removeEditedBranch();
	            this.form.find('#formdata').val(this.getData());
                this.form.submit(); 
            }
		});
	}
);

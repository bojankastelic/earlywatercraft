define(['jquery', 'underscore', 'knockout-mapping', 'views/forms/base', 'views/forms/sections/branch-list'], function ($, _, koMapping, BaseForm, BranchList) {
    return BaseForm.extend({
        events: function(){
            var events = BaseForm.prototype.events.apply(this);
            events['change #select-laboratory'] = 'labChanged';
            return events;
        },
        initialize: function() {
            BaseForm.prototype.initialize.apply(this);
            var date_picker = $('.datetimepicker').datetimepicker({pickTime: false});
            date_picker.on('dp.change', function(evt){
                $(this).find('input').trigger('change'); 
            });
            this.addBranchList(new BranchList({
                data: this.data,
                dataKey: 'DATING_ASSIGNMENT.E17'
            }));
            this.addBranchList(new BranchList({
                el: this.$el.find('#period-section')[0],
                data: this.data,
                dataKey: 'HISTORICAL_PERIOD.E55',
                singleEdit: true
            }));   
            this.addBranchList(new BranchList({
                el: this.$el.find('#known-date-section')[0],
                data: this.data,
                dataKey: 'KNOWN_DATE.E50',
                singleEdit: true
            }));
            this.addBranchList(new BranchList({
                el: this.$el.find('#date-section')[0],
                data: this.data,
                dataKey: 'DATE.E60',
                singleEdit: true
            }));
            this.addBranchList(new BranchList({
                el: this.$el.find('#c14-section')[0],
                data: this.data,
                dataKey: 'C14_DATING_ASSIGNMENT.E16'//,
                //validateBranch: function (nodes) {
                //    return this.validateHasValues(nodes);
                //}
            }));  
            this.addBranchList(new BranchList({
                el: this.$el.find('#dc-section')[0],
                data: this.data,
                dataKey: 'DENDROCHRONOLOGICAL_DATING_ASSIGNMENT.E16'//,
                //validateBranch: function (nodes) {
                //    return this.validateHasValues(nodes);
                //}
        }));  
        },
        labChanged: function(evt) {
            //console.log('Sprememba kode');
            var valueLab = this.$el.find('#select-laboratory').val();
            var domains = koMapping.fromJS(this.data['C14_DATING_ASSIGNMENT.E16'].domains['C14_LABORATORY.E55']);
	    	self = this;
	    	_.each(domains(), function(item) {
				if (item.id() === valueLab) {
                	koda = item.code();
                	//console.log(koda);
                	self.$el.find('#lab-code').text(' ' + koda + '-');
                	self.$el.find('#c14_lab_code').val(koda);
                	self.$el.find('#c14_lab_code').change();
                	return;
                }
            });
        }
    });
});


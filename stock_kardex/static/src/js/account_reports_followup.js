odoo.define('stock_kardex.account_report_followup', function (require) {
'use strict';

var core = require('web.core');
var Pager = require('web.Pager');
var datepicker = require('web.datepicker');
var Dialog = require('web.Dialog');
var account_report = require('stock_kardex.stock_report');

var QWeb = core.qweb;

var account_report_followup = account_report.extend({
    events: _.defaults({
        'click .changeTrust': 'change_trust',
        'click .js_change_date': 'display_exp_note_modal',
        'click .followup-email': 'send_followup_email',
        'click .followup-letter': 'print_pdf',
        'click .o_account_reports_followup_skip': 'skip_partner',
        'click .o_account_reports_followup_done': 'done_partner',
        'click .o_account_reports_followup-auto': 'enable_auto',
        "change *[name='blocked']": 'on_change_blocked',
        'click .o_account_reports_followup-set-next-action': 'set_next_action',
    }, account_report.prototype.events),
    init: function(parent, action) {
        this._super.apply(this, arguments);
        this.ignore_session = 'both';
    },
    parse_reports_informations: function(values) {
        this.map_partner_manager = values.map_partner_manager;
        return this._super(values);
    },
    render: function() {
        if (this.report_options.partners_to_show){
            this.renderPager();
            this.render_searchview();
        }
        this._super();
    },
    renderPager: function() {
        var self = this;
        var pager = new Pager(this, this.report_options.total_pager, this.report_options.pager, 1);
        pager.appendTo($('<div>')); // render the pager
        this.$pager = pager.$el;
        pager.on('pager_changed', this, function (state) {
            self.report_options.pager = state.current_min;
            self.reload();
        });
        return this.$pager;
    },
    render_searchview: function() {
        this.$searchview = $(QWeb.render("accountReports.followupProgressbar", {options: this.report_options}));
    },
    change_trust: function(e) {
        var partner_id = $(e.target).parents('span.dropdown').data("partner");
        var newTrust = $(e.target).data("new-trust");
        if (!newTrust) {
            newTrust = $(e.target).parents('a.changeTrust').data("new-trust");
        }
        var color = 'grey';
        switch(newTrust) {
            case 'good':
                color = 'green';
                break;
            case 'bad':
                color = 'red';
                break;
        }
        return this._rpc({
                model: 'res.partner',
                method: 'write',
                args: [[parseInt(partner_id, 10)], {'trust': newTrust}],
            })
            .then(function () {
                $(e.target).parents('span.dropdown').find('i.oe-account_followup-trust').attr('style', 'color: ' + color + '; font-size: 0.8em;');
            });
    },
    display_done: function(e) {
        $(e.target).parents('.o_account_reports_body').find("div.o_account_reports_page").find(".alert.alert-info.alert-dismissible").remove();
        $(e.target).parents('.o_account_reports_body').find('#action-buttons').addClass('o_account_reports_followup_clicked');
        if ($(e.target).hasClass('btn-primary')){
            $(e.target).toggleClass('btn-primary btn-default');
        }
    },
    send_followup_email: function(e) {
        var self = this;
        var partner_id = $(e.target).data('partner');
        this.report_options['partner_id'] = partner_id;
        return this._rpc({
                model: this.report_model,
                method: 'send_email',
                args: [this.report_options],
            })
            .then(function (result) { // send the email server side
                self.display_done(e);
                $(e.target).parents("div.o_account_reports_page").prepend(QWeb.render("emailSent")); // If all went well, notify the user
            });
    },
    print_pdf: function(e) {
        this.display_done(e);
    },
    done_partner: function(e) {
        var partner_id = $(e.target).data("partner");
        var self = this;
        return this._rpc({
                model: 'res.partner',
                method: 'update_next_action',
                args: [[parseInt(partner_id)]],
            })
            .then(function () { // Update in db and restart report
                if (self.report_options.progressbar) {
                    self.report_options.progressbar[0] += 1;
                }
                self.reload();
            });
    },
    on_change_blocked: function(e) {
        var checkbox = $(e.target).is(":checked");
        var target_id = $(e.target).parents('tr').find('td[data-id]').data('id');
        return this._rpc({
                model: 'account.move.line',
                method: 'write_blocked',
                args: [[parseInt(target_id)], checkbox],
            })
            .then(function(result){
                if (checkbox) {
                    $(e.target).parents('tr').addClass('o_account_followup_blocked');
                }
                else {
                    $(e.target).parents('tr').removeClass('o_account_followup_blocked');
                }
            }); // Write the change in db
    },
    // Opens the modal to select a next action
    set_next_action: function(e) {
        var self = this;
        var partner_id = $(e.target).data('partner');
        var $content = $(QWeb.render("nextActionForm", {target_id: partner_id}));
        var nextActionDatePicker = new datepicker.DateWidget(this);
        nextActionDatePicker.appendTo($content.find('div.o_account_reports_next_action_date_picker'));
        nextActionDatePicker.setValue(moment());

        var changeDate = function (e) {
            var dt = new Date();
            switch($(e.target).data('time')) { // Depending on which button is clicked, change the date accordingly
                case 'one-week':
                    dt.setDate(dt.getDate() + 7);
                    break;
                case 'two-weeks':
                    dt.setDate(dt.getDate() + 14);
                    break;
                case 'one-month':
                    dt.setMonth(dt.getMonth() + 1);
                    break;
                case 'two-months':
                    dt.setMonth(dt.getMonth() + 2);
                    break;
            }
            nextActionDatePicker.setValue(moment(dt));
        };
        $content.find('.o_account_reports_followup_next_action_date_button').bind('click', changeDate);

        var save = function () {
            var note = $content.find(".o_account_reports_next_action_note").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
            var date = nextActionDatePicker.getValue();
            var target_id = $content.find("#target_id").val();
            if (self.$el.find('.o_account_reports_followup-manual').hasClass('btn-default')){
                self.toggle_auto_manual(e);
            }
            return this._rpc({
                model: self.report_model,
                method: 'change_next_action',
                args: [parseInt(target_id), date, note],
            });
        };
        new Dialog(this, {size: 'medium', $content: $content, buttons: [{text: 'Save', classes: 'btn-primary', close: true, click: save}, {text: 'Cancel', close: true}]}).open();
    },
    enable_auto: function(e) {
        var partner_id = $(e.target).data('partner');
        if ($(e.target).parents('.alert').length > 0) {
            $(e.target).hide();
        }
        if ($(e.target).parents('.o_account_reports_body').find('.o_account_reports_followup-auto:last').hasClass('btn-default')){
            this.toggle_auto_manual(e);
            return this._rpc({
                model: this.report_model,
                method: 'change_next_action',
                args: [parseInt(partner_id), this.format_date(new moment()), ''],
            });
        }
    },
    toggle_auto_manual: function(e) {
        $(e.target).parents('.o_account_reports_body').find('.o_account_reports_followup-manual').toggleClass('btn-default btn-info'); // Change the highlighted buttons
        $(e.target).parents('.o_account_reports_body').find('.o_account_reports_followup-auto:last').toggleClass('btn-default btn-info'); // Change the highlighted buttons
    },
    display_exp_note_modal: function(e) {
        var self = this;
        var target_id = $(e.target).data('id');
        var $content = $(QWeb.render("paymentDateForm", {target_id: target_id}));
        var paymentDatePicker = new datepicker.DateWidget(this);
        paymentDatePicker.appendTo($content.find('div.o_account_reports_payment_date_picker'));
        var save = function () {
            var note = $content.find("#internalNote").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
            var date = paymentDatePicker.getValue();
            return this._rpc({
                    model: 'account.move.line',
                    method: 'write',
                    args: [[parseInt($content.find("#target_id").val())], {expected_pay_date: date, internal_note: note}],
                })
                .then(function () {
                    return self.reload();
                });
        };
        new Dialog(this, {title: 'Odoo', size: 'medium', $content: $content, buttons: [{text: 'Save', classes: 'btn-primary', close: true, click: save}, {text: 'Cancel', close: true}]}).open();
    },
    skip_partner: function(e) {
        var partner_id = $(e.target).data('id');
        this.report_options.skipped_partners.push(partner_id);
        this.reload();
    },
});
core.action_registry.add("account_report_followup", account_report_followup);
return account_report_followup;
});

odoo.define('payment_pagarme.payment_form', function (require) {
'use strict';

var core = require('web.core');
var PaymentForm = require('payment.payment_form');

var _t = core._t;

PaymentForm.include({

    events: _.extend({}, PaymentForm.prototype.events, {
        'click input[name="acquirer_pagarme"]': '_onClickPagarmeRadio',
        'click #pagarme_pay_button': '_onClickPagarmePayButton',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initialize Pagar.me payment form
     * @private
     */
    _initPagarmePayment: function () {
        if (this.$('input[name="acquirer_pagarme"]').length === 0) {
            return;
        }

        // Get app ID from form data
        this.pagarmeAppId = this.$('input[name="pagarme_app_id"]').val();
        
        if (!this.pagarmeAppId) {
            this._displayError(_t('Pagar.me configuration error: missing App ID'));
            return;
        }

        // Show/hide card form based on selection
        this._togglePagarmeForm();
    },

    /**
     * Toggle Pagar.me form visibility
     * @private
     */
    _togglePagarmeForm: function () {
        var isPagarmeSelected = this.$('input[name="acquirer_pagarme"]').prop('checked');
        this.$('.pagarme_card_form').toggle(isPagarmeSelected);
        
        if (isPagarmeSelected) {
            this._showPagarmeCardForm();
        }
    },

    /**
     * Show Pagar.me card form
     * @private
     */
    _showPagarmeCardForm: function () {
        var $form = this.$('.pagarme_card_form');
        if ($form.length === 0) {
            // Create card form if it doesn't exist
            this._createPagarmeCardForm();
        }
    },

    /**
     * Create Pagar.me card form
     * @private
     */
    _createPagarmeCardForm: function () {
        var cardFormHtml = `
            <div class="pagarme_card_form" style="display: none;">
                <div class="row">
                    <div class="col-md-12">
                        <label for="pagarme_card_number">` + _t('Card Number') + `</label>
                        <input type="text" id="pagarme_card_number" class="form-control" 
                               placeholder="0000 0000 0000 0000" maxlength="19" required>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-8">
                        <label for="pagarme_card_holder">` + _t('Cardholder Name') + `</label>
                        <input type="text" id="pagarme_card_holder" class="form-control" 
                               placeholder="` + _t('Full name as on card') + `" required>
                    </div>
                    <div class="col-md-4">
                        <label for="pagarme_card_cvv">` + _t('CVV') + `</label>
                        <input type="text" id="pagarme_card_cvv" class="form-control" 
                               placeholder="123" maxlength="4" required>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-6">
                        <label for="pagarme_card_exp_month">` + _t('Expiry Month') + `</label>
                        <select id="pagarme_card_exp_month" class="form-control" required>
                            <option value="">` + _t('Month') + `</option>
                            <option value="01">01</option>
                            <option value="02">02</option>
                            <option value="03">03</option>
                            <option value="04">04</option>
                            <option value="05">05</option>
                            <option value="06">06</option>
                            <option value="07">07</option>
                            <option value="08">08</option>
                            <option value="09">09</option>
                            <option value="10">10</option>
                            <option value="11">11</option>
                            <option value="12">12</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label for="pagarme_card_exp_year">` + _t('Expiry Year') + `</label>
                        <select id="pagarme_card_exp_year" class="form-control" required>
                            <option value="">` + _t('Year') + `</option>
                        </select>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-12">
                        <button type="button" id="pagarme_pay_button" class="btn btn-primary btn-block">
                            ` + _t('Pay with Credit Card') + `
                        </button>
                    </div>
                </div>
                <div class="pagarme_error" style="display: none; color: red; margin-top: 10px;"></div>
            </div>
        `;
        
        this.$('input[name="acquirer_pagarme"]').closest('.card').append(cardFormHtml);
        this._initCardForm();
    },

    /**
     * Initialize card form with validation and formatting
     * @private
     */
    _initCardForm: function () {
        // Populate year options
        var currentYear = new Date().getFullYear();
        var $yearSelect = this.$('#pagarme_card_exp_year');
        for (var i = 0; i < 10; i++) {
            var year = currentYear + i;
            $yearSelect.append('<option value="' + year + '">' + year + '</option>');
        }

        // Format card number
        this.$('#pagarme_card_number').on('input', function () {
            var value = this.value.replace(/\D/g, '');
            var formattedValue = value.replace(/(\d{4})(?=\d)/g, '$1 ');
            this.value = formattedValue;
        });

        // Only allow numbers for CVV
        this.$('#pagarme_card_cvv').on('input', function () {
            this.value = this.value.replace(/\D/g, '');
        });
    },

    /**
     * Tokenize card with Pagar.me API
     * @private
     */
    _tokenizeCard: function () {
        var self = this;
        var cardData = {
            card: {
                holder_name: this.$('#pagarme_card_holder').val(),
                number: this.$('#pagarme_card_number').val().replace(/\s/g, ''),
                exp_month: this.$('#pagarme_card_exp_month').val(),
                exp_year: this.$('#pagarme_card_exp_year').val(),
                cvv: this.$('#pagarme_card_cvv').val()
            }
        };

        // Validate card data
        if (!this._validateCardData(cardData.card)) {
            return Promise.reject(_t('Please fill all card fields correctly'));
        }

        // Make request to Pagar.me tokenization endpoint
        return $.ajax({
            url: 'https://api.pagar.me/core/v5/tokens?appId=' + this.pagarmeAppId,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(cardData),
            timeout: 30000
        }).then(function (response) {
            if (response && response.id) {
                return response.id;
            } else {
                throw new Error(_t('Invalid response from Pagar.me'));
            }
        }).fail(function (xhr) {
            var errorMsg = _t('Card tokenization failed');
            if (xhr.responseJSON && xhr.responseJSON.errors) {
                var errors = xhr.responseJSON.errors;
                if (errors.length > 0) {
                    errorMsg = errors[0].message || errorMsg;
                }
            }
            throw new Error(errorMsg);
        });
    },

    /**
     * Validate card data
     * @private
     */
    _validateCardData: function (card) {
        if (!card.holder_name || card.holder_name.length < 2) {
            this._showPagarmeError(_t('Please enter a valid cardholder name'));
            return false;
        }
        
        if (!card.number || card.number.length < 13) {
            this._showPagarmeError(_t('Please enter a valid card number'));
            return false;
        }
        
        if (!card.exp_month || !card.exp_year) {
            this._showPagarmeError(_t('Please enter a valid expiry date'));
            return false;
        }
        
        if (!card.cvv || card.cvv.length < 3) {
            this._showPagarmeError(_t('Please enter a valid CVV'));
            return false;
        }
        
        return true;
    },

    /**
     * Show error message
     * @private
     */
    _showPagarmeError: function (message) {
        this.$('.pagarme_error').text(message).show();
    },

    /**
     * Hide error message
     * @private
     */
    _hidePagarmeError: function () {
        this.$('.pagarme_error').hide();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handle click on Pagar.me radio button
     * @private
     */
    _onClickPagarmeRadio: function () {
        this._togglePagarmeForm();
    },

    /**
     * Handle click on Pagar.me pay button
     * @private
     */
    _onClickPagarmePayButton: function (ev) {
        ev.preventDefault();
        var self = this;
        
        this._hidePagarmeError();
        
        // Show loading state
        var $button = this.$('#pagarme_pay_button');
        var originalText = $button.text();
        $button.prop('disabled', true).text(_t('Processing...'));
        
        // Tokenize card
        this._tokenizeCard().then(function (token) {
            // Get transaction data
            var txId = self.$('input[name="tx_id"]').val();
            
            // Send token to backend
            return self._rpc({
                route: '/payment/pagarme/process',
                params: {
                    tx_id: txId,
                    token: token
                }
            });
        }).then(function (result) {
            if (result.success) {
                // Redirect to success page
                window.location.href = '/payment/status';
            } else {
                throw new Error(result.error || _t('Payment failed'));
            }
        }).catch(function (error) {
            self._showPagarmeError(error.message || error);
        }).finally(function () {
            // Restore button state
            $button.prop('disabled', false).text(originalText);
        });
    },

    //--------------------------------------------------------------------------
    // Override
    //--------------------------------------------------------------------------

    /**
     * Override start to initialize Pagar.me
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._initPagarmePayment();
        });
    },

});

});
/* Copyright 2024 KMEE
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

odoo.define('l10n_br_payment_pagarme.pagarme_form', function (require) {
    'use strict';

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var PaymentForm = require('payment.payment_form');

    var _t = core._t;

    PaymentForm.include({

        /**
         * @override
         */
        _prepareInlineForm: function (acquirerID, formData) {
            var result = this._super.apply(this, arguments);
            
            if (this.acquirerProviders[acquirerID] !== 'pagarme') {
                return result;
            }

            // Initialize Pagar.me form
            this._initPagarmeForm(acquirerID, formData);
            return result;
        },

        /**
         * Initialize Pagar.me payment form
         */
        _initPagarmeForm: function (acquirerID, formData) {
            var self = this;
            
            // Get Pagar.me configuration
            var encryptionKey = formData.encryption_key;
            var apiUrl = formData.api_url;
            
            if (!encryptionKey) {
                console.error('Pagar.me encryption key not found');
                return;
            }

            // Create card form
            var $form = this.$('[name="o_payment_form"][data-acquirer-id="' + acquirerID + '"]');
            var $cardContainer = $form.find('.o_pagarme_card_container');
            
            if ($cardContainer.length === 0) {
                $cardContainer = $('<div class="o_pagarme_card_container"></div>');
                $form.append($cardContainer);
            }

            // Build credit card form
            this._buildPagarmeCardForm($cardContainer, encryptionKey, apiUrl);
        },

        /**
         * Build Pagar.me credit card form
         */
        _buildPagarmeCardForm: function ($container, encryptionKey, apiUrl) {
            var cardFormHtml = `
                <div class="row">
                    <div class="col-md-12">
                        <div class="form-group">
                            <label for="pagarme_card_number">${_t('Card Number')}</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="pagarme_card_number" 
                                   placeholder="1234 5678 9012 3456"
                                   maxlength="19"
                                   autocomplete="cc-number">
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="pagarme_card_holder">${_t('Cardholder Name')}</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="pagarme_card_holder" 
                                   placeholder="${_t('Nome do Portador')}"
                                   autocomplete="cc-name">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="pagarme_card_expiry">${_t('Expiry Date')}</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="pagarme_card_expiry" 
                                   placeholder="MM/YY"
                                   maxlength="5"
                                   autocomplete="cc-exp">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="form-group">
                            <label for="pagarme_card_cvv">${_t('CVV')}</label>
                            <input type="text" 
                                   class="form-control" 
                                   id="pagarme_card_cvv" 
                                   placeholder="123"
                                   maxlength="4"
                                   autocomplete="cc-csc">
                        </div>
                    </div>
                </div>
                <input type="hidden" id="pagarme_card_token" name="card_token">
            `;
            
            $container.html(cardFormHtml);
            
            // Add input formatting
            this._addCardFormatting($container);
            
            // Store configuration for later use
            $container.data('encryption-key', encryptionKey);
            $container.data('api-url', apiUrl);
        },

        /**
         * Add formatting to card inputs
         */
        _addCardFormatting: function ($container) {
            // Format card number
            $container.find('#pagarme_card_number').on('input', function () {
                var value = this.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
                var formattedValue = value.match(/.{1,4}/g)?.join(' ') || value;
                this.value = formattedValue;
            });

            // Format expiry date
            $container.find('#pagarme_card_expiry').on('input', function () {
                var value = this.value.replace(/\D/g, '');
                if (value.length >= 2) {
                    value = value.substring(0, 2) + '/' + value.substring(2, 4);
                }
                this.value = value;
            });

            // CVV numeric only
            $container.find('#pagarme_card_cvv').on('input', function () {
                this.value = this.value.replace(/\D/g, '');
            });
        },

        /**
         * @override
         */
        _processDirectPayment: function (acquirerID, formData) {
            if (this.acquirerProviders[acquirerID] !== 'pagarme') {
                return this._super.apply(this, arguments);
            }

            return this._processPagarmePayment(acquirerID, formData);
        },

        /**
         * Process Pagar.me payment by tokenizing card
         */
        _processPagarmePayment: function (acquirerID, formData) {
            var self = this;
            var $form = this.$('[name="o_payment_form"][data-acquirer-id="' + acquirerID + '"]');
            var $cardContainer = $form.find('.o_pagarme_card_container');
            
            // Get card data
            var cardData = {
                number: $cardContainer.find('#pagarme_card_number').val().replace(/\s/g, ''),
                holder_name: $cardContainer.find('#pagarme_card_holder').val(),
                exp_month: $cardContainer.find('#pagarme_card_expiry').val().split('/')[0],
                exp_year: '20' + $cardContainer.find('#pagarme_card_expiry').val().split('/')[1],
                cvv: $cardContainer.find('#pagarme_card_cvv').val()
            };

            // Validate card data
            if (!this._validateCardData(cardData)) {
                return Promise.reject();
            }

            // Tokenize card with Pagar.me API
            return this._tokenizeCard(cardData, $cardContainer.data('api-url'), $cardContainer.data('encryption-key'))
                .then(function (token) {
                    // Store token in hidden field
                    $cardContainer.find('#pagarme_card_token').val(token);
                    
                    // Proceed with form submission
                    return self._super.call(self, acquirerID, formData);
                })
                .catch(function (error) {
                    console.error('Pagar.me tokenization failed:', error);
                    Dialog.alert(self, _t('Payment processing failed. Please verify your card information and try again.'));
                    return Promise.reject();
                });
        },

        /**
         * Validate card data
         */
        _validateCardData: function (cardData) {
            if (!cardData.number || cardData.number.length < 13) {
                Dialog.alert(this, _t('Please enter a valid card number.'));
                return false;
            }
            
            if (!cardData.holder_name || cardData.holder_name.length < 2) {
                Dialog.alert(this, _t('Please enter the cardholder name.'));
                return false;
            }
            
            if (!cardData.exp_month || !cardData.exp_year || 
                cardData.exp_month.length !== 2 || cardData.exp_year.length !== 4) {
                Dialog.alert(this, _t('Please enter a valid expiry date.'));
                return false;
            }
            
            if (!cardData.cvv || cardData.cvv.length < 3) {
                Dialog.alert(this, _t('Please enter a valid CVV.'));
                return false;
            }
            
            return true;
        },

        /**
         * Tokenize card with Pagar.me API
         */
        _tokenizeCard: function (cardData, apiUrl, encryptionKey) {
            return new Promise(function (resolve, reject) {
                $.ajax({
                    url: apiUrl + '/tokens',
                    type: 'POST',
                    headers: {
                        'Authorization': 'Basic ' + btoa(encryptionKey + ':'),
                        'Content-Type': 'application/json'
                    },
                    data: JSON.stringify({
                        card: cardData
                    }),
                    success: function (response) {
                        if (response.id) {
                            resolve(response.id);
                        } else {
                            reject('Invalid response from Pagar.me');
                        }
                    },
                    error: function (xhr, status, error) {
                        console.error('Pagar.me tokenization error:', xhr.responseText);
                        reject(error);
                    }
                });
            });
        }
    });
});
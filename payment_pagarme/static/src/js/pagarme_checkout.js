/* Copyright 2024 KMEE INFORMATICA LTDA
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
 */

odoo.define('payment_pagarme.checkout', function (require) {
    'use strict';

    var core = require('web.core');
    var PaymentFormMixin = require('payment.payment_form_mixin');

    var _t = core._t;

    /**
     * Pagar.me Payment Form Mixin
     * Handles transparent checkout for Pagar.me payments
     */
    var PagarmePaymentForm = PaymentFormMixin.extend({
        events: _.extend({}, PaymentFormMixin.prototype.events, {
            'input input[name="pagarme_card_number"]': '_onCardNumberInput',
            'input input[name="pagarme_customer_document"]': '_onDocumentInput', 
            'input input[name="pagarme_zipcode"]': '_onZipcodeInput',
            'change select[name="pagarme_installments"]': '_onInstallmentsChange',
            'submit .o_payment_form': '_onSubmit',
        }),

        /**
         * @override
         */
        start: function () {
            var def = this._super.apply(this, arguments);
            if (this._isProviderPagarme()) {
                this._initializeForm();
            }
            return def;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Check if provider is Pagar.me
         * @private
         * @returns {Boolean}
         */
        _isProviderPagarme: function () {
            return this.$('input[name="provider_code"]').val() === 'pagarme';
        },

        /**
         * Handle form submission for Pagar.me payments
         * @private
         * @param {Event} ev
         */
        _onSubmit: function (ev) {
            if (!this._isProviderPagarme()) {
                return;
            }
            
            ev.preventDefault();
            
            if (!this._validatePagarmeForm()) {
                return;
            }
            
            this._processPagarmePayment();
        },

        /**
         * Process Pagar.me payment
         * @private
         */
        _processPagarmePayment: function () {
            var self = this;
            var paymentData = this._preparePagarmePaymentData();
            
            this._showLoading();
            
            this._rpc({
                route: '/payment/pagarme/process_payment',
                params: paymentData
            }).then(function (result) {
                self._hideLoading();
                
                if (result.status === 'success') {
                    if (result.redirect_url) {
                        window.location.href = result.redirect_url;
                    } else {
                        window.location.reload();
                    }
                } else {
                    self._displayError(result.message || _t('Erro no processamento do pagamento'));
                }
            }).catch(function (error) {
                self._hideLoading();
                self._displayError(_t('Erro de comunicação com o servidor'));
                console.error('Pagar.me payment error:', error);
            });
        },

        /**
         * Initialize the payment form
         * @private
         */
        _initializeForm: function () {
            // Populate year options for card expiry
            this._populateYearOptions();
            
            // Load available installments
            this._loadInstallments();
            
            // Initialize input masks
            this._initializeInputMasks();
            
            // Initialize card brand detection
            this._initializeCardBrandDetection();
        },

        /**
         * Populate year options for card expiry
         * @private
         */
        _populateYearOptions: function () {
            var $yearSelect = this.$('select[name="pagarme_card_exp_year"]');
            if ($yearSelect.length === 0) return;
            
            var currentYear = new Date().getFullYear();
            
            for (var i = 0; i <= 10; i++) {
                var year = currentYear + i;
                $yearSelect.append($('<option>', {
                    value: year.toString().slice(-2),
                    text: year
                }));
            }
        },

        /**
         * Load available installments for the current amount
         * @private
         */
        _loadInstallments: function () {
            var self = this;
            var amount = this.$('input[name="amount"]').val();
            
            if (!amount) {
                return;
            }

            this._rpc({
                route: '/payment/pagarme/get_installments',
                params: {
                    amount: parseFloat(amount),
                }
            }).then(function (result) {
                if (result.status === 'success') {
                    self._updateInstallmentOptions(result.installments);
                }
            }).catch(function (error) {
                console.error('Error loading installments:', error);
            });
        },

        /**
         * Update installment options in the select
         * @private
         * @param {Array} installments - Available installment options
         */
        _updateInstallmentOptions: function (installments) {
            var $installmentsSelect = this.$('select[name="pagarme_installments"]');
            $installmentsSelect.empty();
            
            installments.forEach(function (option) {
                $installmentsSelect.append($('<option>', {
                    value: option.installments,
                    text: option.label,
                    'data-amount': option.installment_amount,
                    'data-total': option.total_amount,
                }));
            });
        },

        /**
         * Initialize input masks for better UX
         * @private
         */
        _initializeInputMasks: function () {
            // Card number mask
            this._applyMask('input[name="pagarme_card_number"]', '0000 0000 0000 0000');
            
            // Document mask (CPF/CNPJ)
            this._applyDocumentMask('input[name="pagarme_customer_document"]');
            
            // Phone mask
            this._applyMask('input[name="pagarme_customer_phone"]', '(00) 00000-0000');
            
            // Zipcode mask
            this._applyMask('input[name="pagarme_zipcode"]', '00000-000');
            
            // CVV mask
            this._applyMask('input[name="pagarme_card_cvv"]', '0000');
        },

        /**
         * Apply input mask to element
         * @private
         * @param {String} selector - Element selector
         * @param {String} mask - Mask pattern
         */
        _applyMask: function (selector, mask) {
            // Simple mask implementation
            var $input = this.$(selector);
            if ($input.length === 0) return;
            
            $input.on('input', function () {
                var value = this.value.replace(/\D/g, '');
                var maskedValue = '';
                var maskIndex = 0;
                
                for (var i = 0; i < value.length && maskIndex < mask.length; i++) {
                    while (maskIndex < mask.length && mask[maskIndex] !== '0') {
                        maskedValue += mask[maskIndex];
                        maskIndex++;
                    }
                    if (maskIndex < mask.length) {
                        maskedValue += value[i];
                        maskIndex++;
                    }
                }
                
                this.value = maskedValue;
            });
        },

        /**
         * Apply document mask (CPF/CNPJ)
         * @private
         * @param {String} selector - Element selector
         */
        _applyDocumentMask: function (selector) {
            var $input = this.$(selector);
            if ($input.length === 0) return;
            
            $input.on('input', function () {
                var value = this.value.replace(/\D/g, '');
                var maskedValue = '';
                
                if (value.length <= 11) {
                    // CPF mask: 000.000.000-00
                    maskedValue = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
                } else {
                    // CNPJ mask: 00.000.000/0000-00
                    maskedValue = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
                }
                
                this.value = maskedValue;
            });
        },

        /**
         * Initialize card brand detection
         * @private
         */
        _initializeCardBrandDetection: function () {
            var self = this;
            var cardBrands = {
                visa: /^4[0-9]{0,15}$/,
                mastercard: /^5[1-5][0-9]{0,14}$/,
                amex: /^3[47][0-9]{0,13}$/,
                elo: /^((((636368)|(438935)|(504175)|(451416)|(636297))\d{0,10})|((5067)|(4576)|(4011))\d{0,12})$/,
            };
            
            this.$('input[name="pagarme_card_number"]').on('input', function () {
                var cardNumber = this.value.replace(/\s/g, '');
                var detectedBrand = null;
                
                for (var brand in cardBrands) {
                    if (cardBrands[brand].test(cardNumber)) {
                        detectedBrand = brand;
                        break;
                    }
                }
                
                self._updateCardBrandDisplay(detectedBrand);
            });
        },

        /**
         * Update card brand display
         * @private
         * @param {String} brand - Detected card brand
         */
        _updateCardBrandDisplay: function (brand) {
            this.$('.card-icon').removeClass('active');
            if (brand) {
                this.$('.card-icon[alt*="' + brand + '"]').addClass('active');
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Handle card number input
         * @private
         * @param {Event} ev
         */
        _onCardNumberInput: function (ev) {
            // Card brand detection is handled by _initializeCardBrandDetection
        },

        /**
         * Handle document input and validation
         * @private
         * @param {Event} ev
         */
        _onDocumentInput: function (ev) {
            var self = this;
            var document = ev.target.value.replace(/\D/g, '');
            
            if (document.length >= 11) {
                this._rpc({
                    route: '/payment/pagarme/validate_document',
                    params: {
                        document: document,
                    }
                }).then(function (result) {
                    if (result.status === 'success') {
                        self._markFieldValid(ev.target);
                    } else {
                        self._markFieldInvalid(ev.target, result.message);
                    }
                });
            }
        },

        /**
         * Handle zipcode input and address lookup
         * @private
         * @param {Event} ev
         */
        _onZipcodeInput: function (ev) {
            var zipcode = ev.target.value.replace(/\D/g, '');
            
            if (zipcode.length === 8) {
                this._lookupAddress(zipcode);
            }
        },

        /**
         * Handle installments change
         * @private
         * @param {Event} ev
         */
        _onInstallmentsChange: function (ev) {
            var $option = this.$(ev.target).find('option:selected');
            var installmentAmount = $option.data('amount');
            var totalAmount = $option.data('total');
            
            // Update display if needed
            this._updateInstallmentDisplay(installmentAmount, totalAmount);
        },

        //--------------------------------------------------------------------------
        // Validation
        //--------------------------------------------------------------------------

        /**
         * Validate the Pagar.me form
         * @private
         * @returns {Boolean}
         */
        _validatePagarmeForm: function () {
            var isValid = true;
            
            // Validate required fields
            this.$('input[required], select[required]').each(function () {
                if (!this.value.trim()) {
                    isValid = false;
                    $(this).addClass('is-invalid');
                } else {
                    $(this).removeClass('is-invalid');
                }
            });
            
            // Validate card number
            if (!this._validateCardNumber()) {
                isValid = false;
            }
            
            // Validate document
            if (!this._validateDocument()) {
                isValid = false;
            }
            
            return isValid;
        },

        /**
         * Validate card number
         * @private
         * @returns {Boolean}
         */
        _validateCardNumber: function () {
            var cardNumber = this.$('input[name="pagarme_card_number"]').val().replace(/\s/g, '');
            
            // Luhn algorithm validation
            var sum = 0;
            var alternate = false;
            
            for (var i = cardNumber.length - 1; i >= 0; i--) {
                var n = parseInt(cardNumber.charAt(i), 10);
                
                if (alternate) {
                    n *= 2;
                    if (n > 9) {
                        n = (n % 10) + 1;
                    }
                }
                
                sum += n;
                alternate = !alternate;
            }
            
            var isValid = (sum % 10) === 0 && cardNumber.length >= 13;
            
            if (!isValid) {
                this._markFieldInvalid('input[name="pagarme_card_number"]', 'Número do cartão inválido');
            } else {
                this._markFieldValid('input[name="pagarme_card_number"]');
            }
            
            return isValid;
        },

        /**
         * Validate document (CPF/CNPJ)
         * @private
         * @returns {Boolean}
         */
        _validateDocument: function () {
            var document = this.$('input[name="pagarme_customer_document"]').val().replace(/\D/g, '');
            var isValid = false;
            
            if (document.length === 11) {
                isValid = this._validateCPF(document);
            } else if (document.length === 14) {
                isValid = this._validateCNPJ(document);
            }
            
            if (!isValid) {
                this._markFieldInvalid('input[name="pagarme_customer_document"]', 'CPF/CNPJ inválido');
            } else {
                this._markFieldValid('input[name="pagarme_customer_document"]');
            }
            
            return isValid;
        },

        /**
         * Validate CPF
         * @private
         * @param {String} cpf
         * @returns {Boolean}
         */
        _validateCPF: function (cpf) {
            if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
                return false;
            }
            
            var sum = 0;
            for (var i = 0; i < 9; i++) {
                sum += parseInt(cpf.charAt(i)) * (10 - i);
            }
            var remainder = (sum * 10) % 11;
            if (remainder === 10 || remainder === 11) remainder = 0;
            if (remainder !== parseInt(cpf.charAt(9))) return false;
            
            sum = 0;
            for (var i = 0; i < 10; i++) {
                sum += parseInt(cpf.charAt(i)) * (11 - i);
            }
            remainder = (sum * 10) % 11;
            if (remainder === 10 || remainder === 11) remainder = 0;
            if (remainder !== parseInt(cpf.charAt(10))) return false;
            
            return true;
        },

        /**
         * Validate CNPJ
         * @private
         * @param {String} cnpj
         * @returns {Boolean}
         */
        _validateCNPJ: function (cnpj) {
            if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) {
                return false;
            }
            
            var length = cnpj.length - 2;
            var numbers = cnpj.substring(0, length);
            var digits = cnpj.substring(length);
            var sum = 0;
            var pos = length - 7;
            
            for (var i = length; i >= 1; i--) {
                sum += numbers.charAt(length - i) * pos--;
                if (pos < 2) pos = 9;
            }
            
            var result = sum % 11 < 2 ? 0 : 11 - sum % 11;
            if (result !== parseInt(digits.charAt(0))) return false;
            
            length = length + 1;
            numbers = cnpj.substring(0, length);
            sum = 0;
            pos = length - 7;
            
            for (var i = length; i >= 1; i--) {
                sum += numbers.charAt(length - i) * pos--;
                if (pos < 2) pos = 9;
            }
            
            result = sum % 11 < 2 ? 0 : 11 - sum % 11;
            if (result !== parseInt(digits.charAt(1))) return false;
            
            return true;
        },

        //--------------------------------------------------------------------------
        // Payment Processing
        //--------------------------------------------------------------------------

        /**
         * Prepare payment data for API
         * @private
         * @returns {Object}
         */
        _preparePagarmePaymentData: function () {
            // Get reference from form
            var reference = this.$('input[name="reference"]').val();
            
            // Collect card data
            var cardData = {
                card_number: this.$('input[name="pagarme_card_number"]').val().replace(/\s/g, ''),
                card_holder_name: this.$('input[name="pagarme_card_holder_name"]').val(),
                card_exp_month: this.$('select[name="pagarme_card_exp_month"]').val(),
                card_exp_year: this.$('select[name="pagarme_card_exp_year"]').val(),
                card_cvv: this.$('input[name="pagarme_card_cvv"]').val(),
                installments: parseInt(this.$('select[name="pagarme_installments"]').val()),
            };

            // Collect customer data
            var customerData = {
                customer_name: this.$('input[name="pagarme_customer_name"]').val(),
                customer_email: this.$('input[name="pagarme_customer_email"]').val(),
                customer_document: this.$('input[name="pagarme_customer_document"]').val(),
                customer_phone: this.$('input[name="pagarme_customer_phone"]').val(),
            };

            // Collect billing address
            var billingData = {
                billing_street: this.$('input[name="pagarme_billing_street"]').val(),
                billing_street_number: this.$('input[name="pagarme_billing_street_number"]').val(),
                billing_neighborhood: this.$('input[name="pagarme_billing_neighborhood"]').val(),
                billing_city: this.$('input[name="pagarme_billing_city"]').val(),
                billing_state: this.$('input[name="pagarme_billing_state"]').val(),
                billing_zipcode: this.$('input[name="pagarme_zipcode"]').val(),
            };

            return {
                reference: reference,
                provider_code: 'pagarme',
                payment_method_code: 'pagarme',
                ...cardData,
                ...customerData,
                ...billingData
            };
        },

        //--------------------------------------------------------------------------
        // UI Helpers
        //--------------------------------------------------------------------------

        /**
         * Show loading state
         * @private
         */
        _showLoading: function () {
            this.$('.o_payment_submit_button').prop('disabled', true).text(_t('Processando...'));
        },

        /**
         * Hide loading state
         * @private
         */
        _hideLoading: function () {
            this.$('.o_payment_submit_button').prop('disabled', false).text(_t('Pagar Agora'));
        },

        /**
         * Display error message
         * @private
         * @param {String} message
         */
        _displayError: function (message) {
            this.displayNotification({
                type: 'warning',
                title: _t('Erro no Pagamento'),
                message: message,
                sticky: false,
            });
        },

        /**
         * Mark field as valid
         * @private
         * @param {String|Element} field
         */
        _markFieldValid: function (field) {
            this.$(field).removeClass('is-invalid').addClass('is-valid');
        },

        /**
         * Mark field as invalid
         * @private
         * @param {String|Element} field
         * @param {String} message
         */
        _markFieldInvalid: function (field, message) {
            var $field = this.$(field);
            $field.removeClass('is-valid').addClass('is-invalid');
            
            var $feedback = $field.siblings('.invalid-feedback');
            if ($feedback.length && message) {
                $feedback.text(message);
            }
        },

        /**
         * Lookup address by zipcode
         * @private
         * @param {String} zipcode
         */
        _lookupAddress: function (zipcode) {
            // This could integrate with a CEP lookup service
            // For now, it's a placeholder for future implementation
            console.log('Looking up address for zipcode:', zipcode);
        },

        /**
         * Update installment display
         * @private
         * @param {Number} installmentAmount
         * @param {Number} totalAmount
         */
        _updateInstallmentDisplay: function (installmentAmount, totalAmount) {
            // Update any display elements showing installment information
            // This is a placeholder for future enhancements
        },
    });

    // Register the mixin
    PaymentFormMixin.include(PagarmePaymentForm);

    return PagarmePaymentForm;
});
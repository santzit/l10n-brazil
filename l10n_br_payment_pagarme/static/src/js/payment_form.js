/** @odoo-module */

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';
import { loadJS } from "@web/core/assets";

const pagarmeMixin = {

    /**
     * Handle direct payment for Pagar.me using Tokenize.js
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} code - The code of the payment option
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {undefined}
     */
    _processDirectPayment: function (code, paymentOptionId, processingValues) {
        if (code !== 'pagarme') {
            return this._super(...arguments);
        }

        // Load Pagar.me Tokenize.js library
        return loadJS('https://assets.pagar.me/tokenize/1.0.0/tokenize.min.js')
            .then(() => {
                return this._processPaymentPagarme(paymentOptionId, processingValues);
            })
            .catch((error) => {
                this._displayError(
                    this._t("Unable to load Pagar.me payment library. Please try again."),
                    this._t("Payment Provider Error")
                );
            });
    },

    /**
     * Process Pagar.me payment using tokenization
     *
     * @private
     * @param {number} paymentOptionId - The id of the payment option handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {Promise}
     */
    _processPaymentPagarme: function (paymentOptionId, processingValues) {
        const cardData = this._getCardData();
        
        if (!this._validateCardData(cardData)) {
            return Promise.reject("Invalid card data");
        }

        // Create tokenize instance
        const tokenize = new window.Tokenize(processingValues.app_id);
        
        return new Promise((resolve, reject) => {
            tokenize.card(cardData, (error, token) => {
                if (error) {
                    this._displayError(
                        error.message || this._t("Card tokenization failed. Please check your card details."),
                        this._t("Payment Error")
                    );
                    reject(error);
                } else {
                    // Submit the transaction with the token
                    this._submitTransaction(paymentOptionId, { pagarme_token: token });
                    resolve(token);
                }
            });
        });
    },

    /**
     * Extract card data from the form
     *
     * @private
     * @return {object} Card data object
     */
    _getCardData: function () {
        return {
            card_number: this.$('.card_number').val().replace(/\s/g, ''),
            card_holder_name: this.$('.card_holder_name').val(),
            card_expiration_date: this._formatExpirationDate(),
            card_cvv: this.$('.card_cvv').val(),
        };
    },

    /**
     * Format expiration date for Pagar.me (MMYY format)
     *
     * @private
     * @return {string} Formatted expiration date
     */
    _formatExpirationDate: function () {
        const month = this.$('.card_expiry_month').val();
        const year = this.$('.card_expiry_year').val();
        
        if (month && year) {
            return month.padStart(2, '0') + year.slice(-2);
        }
        return '';
    },

    /**
     * Validate card data
     *
     * @private
     * @param {object} cardData - The card data to validate
     * @return {boolean} True if valid
     */
    _validateCardData: function (cardData) {
        if (!cardData.card_number || cardData.card_number.length < 13) {
            this._displayError(this._t("Please enter a valid card number."));
            return false;
        }
        
        if (!cardData.card_holder_name) {
            this._displayError(this._t("Please enter the cardholder name."));
            return false;
        }
        
        if (!cardData.card_expiration_date || cardData.card_expiration_date.length !== 4) {
            this._displayError(this._t("Please enter a valid expiration date."));
            return false;
        }
        
        if (!cardData.card_cvv || cardData.card_cvv.length < 3) {
            this._displayError(this._t("Please enter a valid CVV."));
            return false;
        }
        
        return true;
    },

    /**
     * Submit transaction with token to backend
     *
     * @private
     * @param {number} paymentOptionId - The payment option id
     * @param {object} tokenData - The token data
     */
    _submitTransaction: function (paymentOptionId, tokenData) {
        const processingValues = Object.assign({}, this.txContext, tokenData);
        
        this._rpc({
            route: '/payment/transaction',
            params: {
                'acquirer_id': paymentOptionId,
                'amount': processingValues.amount,
                'currency_id': processingValues.currency_id,
                'partner_id': processingValues.partner_id,
                'reference': processingValues.reference,
                'pagarme_token': tokenData.pagarme_token,
            },
        }).then((result) => {
            if (result.success) {
                window.location = result.redirect_url || '/payment/status';
            } else {
                this._displayError(
                    result.error || this._t("Payment processing failed. Please try again."),
                    this._t("Payment Error")
                );
            }
        }).catch((error) => {
            this._displayError(
                this._t("Unable to process payment. Please try again."),
                this._t("Server Error")
            );
        });
    },
};

checkoutForm.include(pagarmeMixin);
manageForm.include(pagarmeMixin);
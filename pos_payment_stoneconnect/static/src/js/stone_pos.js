odoo.define('pos_payment_stone.stone_pos', function(require){
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const rpc = require('web.rpc');

    PaymentScreen.include({
        async _finalizeValidation() {
            const payment_method = this.currentOrder.selected_paymentline.payment_method;
            if (payment_method.use_stone_terminal) {
                // Call backend to send payment to Stone terminal
                const result = await rpc.query({
                    model: 'pos.payment.method',
                    method: 'send_payment_to_terminal',
                    args: [payment_method.id, this.currentOrder.get_total_with_tax(), this.currentOrder.name],
                });
                if (result.status === 'approved') {
                    // Continue with order
                    return this._super();
                } else {
                    this.showPopup('ErrorPopup', {
                        title: 'Payment Failed',
                        body: result.message,
                    });
                    return;
                }
            } else {
                return this._super();
            }
        },
    });
});

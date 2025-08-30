# Copyright 2024 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""
Pagar.me API Constants and Configuration

This module contains all the constants and configuration needed for 
integrating with the Pagar.me payment gateway API.

Pagar.me API Documentation: https://docs.pagar.me/
"""

# API Base URLs
PAGARME_API_BASE_URL_PRODUCTION = "https://api.pagar.me"
PAGARME_API_BASE_URL_SANDBOX = "https://api.pagar.me"

# API Versioning
PAGARME_API_VERSION = "core/v5"

# Timeout for API requests (in seconds)
PAGARME_API_TIMEOUT = 30

# Supported Payment Methods
PAGARME_PAYMENT_METHODS = [
    ("credit_card", "Credit Card"),
    ("debit_card", "Debit Card"), 
    ("boleto", "Boleto Bancário"),
    ("pix", "PIX"),
    ("voucher", "Voucher"),
]

# Transaction Status Mapping
PAGARME_TRANSACTION_STATUS = {
    "processing": "pending",
    "authorized": "authorized", 
    "paid": "done",
    "refunded": "refunded",
    "waiting_payment": "pending",
    "pending_refund": "pending",
    "refused": "canceled",
    "chargedback": "canceled",
    "analyzing": "pending",
}

# PIX Key Types
PAGARME_PIX_KEY_TYPES = [
    ("email", "Email"),
    ("cpf", "CPF"),
    ("cnpj", "CNPJ"),
    ("phone", "Phone"),
    ("random", "Random Key"),
]

# Boleto Payment Instructions
PAGARME_BOLETO_INSTRUCTIONS = [
    ("1", "Pay only with cash or checking account"),
    ("2", "Pay only at the bank branch"),
    ("3", "Pay only via electronic banking"),
]

# Card Brands Supported
PAGARME_SUPPORTED_CARD_BRANDS = [
    "visa",
    "mastercard", 
    "amex",
    "elo",
    "hipercard",
    "diners",
    "discover",
]

# Webhook Event Types
PAGARME_WEBHOOK_EVENTS = [
    "transaction.created",
    "transaction.waiting_payment", 
    "transaction.processing",
    "transaction.authorized",
    "transaction.paid",
    "transaction.refunded",
    "transaction.pending_refund",
    "transaction.refused",
    "transaction.chargedback",
    "order.created",
    "order.paid",
    "order.canceled",
    "charge.created",
    "charge.paid",
    "charge.pending",
    "charge.failed",
    "charge.canceled",
]

# Anti-fraud Rules
PAGARME_ANTIFRAUD_RULES = [
    ("automatic", "Automatic Analysis"),
    ("manual", "Manual Review"),
    ("disabled", "Disabled"),
]

# Installment Configuration
PAGARME_MAX_INSTALLMENTS = 12
PAGARME_MIN_INSTALLMENT_AMOUNT = 5.00  # R$ 5.00

# Error Codes Mapping
PAGARME_ERROR_CODES = {
    "001": "General error",
    "002": "Invalid transaction amount",
    "003": "Invalid card data",
    "004": "Expired card",
    "005": "Insufficient funds",
    "006": "Transaction not authorized",
    "007": "Invalid payment method",
    "008": "Transaction already processed",
    "009": "Invalid API key",
    "010": "Rate limit exceeded",
}

# Split Payment Configuration
PAGARME_SPLIT_RULES_TYPES = [
    ("percentage", "Percentage"),
    ("flat", "Fixed Amount"),
]

# Subscription Intervals
PAGARME_SUBSCRIPTION_INTERVALS = [
    ("day", "Daily"),
    ("week", "Weekly"),
    ("month", "Monthly"),
    ("year", "Yearly"),
]

# Customer Document Types
PAGARME_DOCUMENT_TYPES = [
    ("cpf", "CPF"),
    ("cnpj", "CNPJ"),
    ("passport", "Passport"),
]

# Address Types
PAGARME_ADDRESS_TYPES = [
    ("billing", "Billing Address"),
    ("shipping", "Shipping Address"),
]

def get_pagarme_api_url(env, endpoint=""):
    """
    Get the appropriate Pagar.me API URL based on environment configuration.
    
    Args:
        env: Odoo environment
        endpoint: API endpoint to append
        
    Returns:
        str: Complete API URL
    """
    # Check if we're in sandbox mode
    # This should be configurable in the payment provider settings
    is_sandbox = env.context.get('pagarme_sandbox', True)
    
    base_url = PAGARME_API_BASE_URL_SANDBOX if is_sandbox else PAGARME_API_BASE_URL_PRODUCTION
    
    if endpoint:
        return f"{base_url}/{PAGARME_API_VERSION}/{endpoint}"
    else:
        return f"{base_url}/{PAGARME_API_VERSION}"

def get_pagarme_headers(api_key):
    """
    Get standard headers for Pagar.me API requests.
    
    Args:
        api_key: Pagar.me API key
        
    Returns:
        dict: Headers for API requests
    """
    return {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Odoo-PagarMe/1.0",
    }
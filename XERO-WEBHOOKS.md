# SmartBiz Payment & Xero Webhook Mapping

## PayFast notify -> Xero flow

Endpoint: `POST /payfast/notify`

Validation:
- Verify `signature` using HMAC-MD5 with `PAYFAST_MERCHANT_KEY`
- Extract `m_payment_id`, `pf_payment_id`, `amount_gross`, `payment_status`

Local update:
- Update booking `payfast_payment_id`, `payfast_pf_payment_id`
- Insert `payment_confirmed` event

Xero action:
- If `payment_status` indicates success, call internal invoice creation for booking
- If `payment_status` indicates failure/cancel, do not create invoice

## Xero webhook/event mapping

Recommended Xero webhooks:
- `INVOICE.CREATED` -> log booking payment event
- `INVOICE.PAID` -> mark booking payment confirmed if not already
- `CREDITNOTE.CREATED` -> mark booking refunded
- `CREDITNOTE.APPROVED` -> finalize refund state

## Refund rule

- Refund window: 5 days after booking `created_at`
- Trigger: technician no-show or failed job
- Action: create Xero credit note, update booking status to `refunded`

## Technician completion release

- Technician completes via `/technician/complete/{booking_id}`
- If payment exists, mark booking `technician_completed`
- This signals release of payment hold in Xero accounting context

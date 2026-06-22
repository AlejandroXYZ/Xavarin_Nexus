from app.schemas.translators_schemas.whatsapp import WhatsAppPayload


def payload_whatsaap_message() -> WhatsAppPayload:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "100001234567866",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "584120000088",
                                "phone_number_id": "102938475610288",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Superman"},
                                    "wa_id": "584141234588",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "584141234588",
                                    "id": "wamid.cBgLNTgx345xMjM0NTY3FQIAEhgUM0EwQkE1QjEwQjYxQTU5QTQ2RHZa",
                                    "timestamp": "171832066",
                                    "text": {"body": "Dónde se ubican?"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    whatsapp_message = WhatsAppPayload(**payload)
    return whatsapp_message

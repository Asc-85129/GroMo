import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

client = Client(account_sid, auth_token)

def initiate_call(to_phone: str, twiml_url: str):
    call = client.calls.create(
        to=to_phone,
        from_=twilio_number,
        url=twiml_url
    )
    return call.sid

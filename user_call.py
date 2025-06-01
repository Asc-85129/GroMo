from app.twilio_client import initiate_call
from dotenv import load_dotenv
load_dotenv()

ngrok_url = " https://d319-2405-201-2002-e05e-b878-9b57-8854-fa2c.ngrok-free.app"  # Replace with your actual ngrok URL
to_phone = "+919427159397"  # Replace with the target phone number (in E.164 format)

call_sid = initiate_call(to_phone, f"{ngrok_url}/twiml")
print("Call SID:", call_sid)

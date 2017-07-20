import os
import time

from flask import Flask
from flask import Response
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from twilio import twiml
from twilio.rest import Client
from zenpy import Zenpy
from zenpy.lib.api_objects import Comment, CustomField, Ticket, User
from twilio.twiml.voice_response import VoiceResponse, Gather, Record, Queue, Conference, Dial

# Pull in configuration from system environment variables
#TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
#TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
#TWILIO_NUMBER = os.environ.get('TWILIO_NUMBER')

#	TEST CREDS CHANGE TO LIVE WHEN READY
#accountSID = "AC7fa0bf86bf41b5b04d0b6229e8305a5f"
#authToken = "def5c79c96be3f3e76fd0732e3e57aa6"

#	LIVE CREDS-REQUIRED FOR TRANSCRIPTIONS
accountSID = "AC048c894d221603a92a2b8641d6eba672"
authToken = "47cad688e4154db2e9b6127a2ca468ab"

#	Refers to Twilio API client
client = Client(accountSID, authToken)

zenCreds = {
    'email' : 'alex@quadquestions.com',
    'token' : 'bLHi3Fm4bVqYbAbe67lG1Ad2IHxszD7wIwBxwH99',
    'subdomain': 'quadquestions'
}

#	Refers to ZenDesk API client
zenpy_client = Zenpy(**zenCreds)

#	location of greeting mp3 file
greeting_mp3 = "https://quadquestions.com/phone_system/MP3s/quadquestions_greeting.mp3"

#	location of hold mp3 file
hold_mp3 = "https://quadquestions.com/phone_system/MP3s/Please_hold.mp3"

#	location of after hours mp3 file
afterHours_mp3 = "https://quadquestions.com/phone_system/MP3s/quadquestions_after_hours.mp3"

# Create a Flask web app
app = Flask(__name__)

# Handle a POST request to make an outbound call. This is called via ajax
# on our web page

#	Root URL for the app. Calls will start here.

@app.route('/i')
def index():
    return render_template('index.html')

@app.route("/", methods=['GET', 'POST'])
def voiceGreeting():
    currentDay = time.strftime("%A")
    currentTime = int(time.strftime("%H"))

    if((currentDay == 'Saturday') or (currentDay == 'Sunday') or (currentTime >= 18) or (currentTime < 10)):
    	resp = VoiceResponse()
    	resp.play(afterHours_mp3)
    	resp.redirect("/voicemail-handle")
    	return str(resp)
    else:
    	resp = VoiceResponse()
    	resp.play(greeting_mp3)
    	press = Gather(numDigit=1, action="/key-handle", method="POST")
    	resp.append(press)
    return str(resp)

#	Handles key presses from the user end

@app.route("/key-handle", methods=['GET', 'POST'])
def key_handle():
	digitPressed = request.form['Digits']
	resp = VoiceResponse()
	if digitPressed == "1":
		resp.redirect("/voicemail-handle")
		return str(resp)
	elif digitPressed != "1":
		resp.enqueue("Hold Queue", wait_url="/callQ-handle")
		return str(resp)

@app.route("/callQ-handle", methods=['GET', 'POST'])
def callQ_handle():
	resp = VoiceResponse()
	conferences = client.conferences.list(status="in-progress", friendly_name="TEST")
	if(conferences == [])
		resp.redirect("/pop-first")
	resp.play(hold_mp3, loop=1)
	return str(resp)

@app.route("/pop-first", methods=['GET', 'POST'])
def pop_first():
	resp = VoiceResponse()
	queueSID = client.queues.list(friendly_name="Hold Queue")[0].sid
	client.queues(queueSID).members("Front").update(url="/conf-handle", method = "POST")
	return str(resp)


@app.route("/conf-handle", methods=['GET', 'POST'])
def conf_handle():
	resp = VoiceResponse()
	dial = Dial()
	dial.conference("TEST", wait_url="/call-agent",
									status="end", 
									end_conference_on_exit=True,
									status_callback="/pop-first")
	resp.append(dial)
	return str(resp)

@app.route("/conf-mod", methods=['GET', 'POST'])
def conf_mod():
	resp = VoiceResponse()
	dial = Dial(hangup_on_star=True, action='/gather-mod')
	dial.conference("TEST", wait_url="/hold-handle")
	resp.append(dial)
	return str(resp)

@app.route("/gather-mod", methods=['GET', 'POST'])
def gather_mod():
	resp = VoiceResponse()
	conferences = client.conferences.list(status="in-progress", friendly_name="TEST")
	confID = client.conferences.list()[0].sid
	print(request.method)
#	if (request.form['Digits'] == "*"):
#		print("*")
#		resp.redirect("/conf-mod")
#	else:
#		print("!*")
#		Gather(numDigit=1, action="/gather-mod", method="POST")
	return str(resp)


@app.route("/voicemail-handle", methods=['GET', 'POST'])
def leave_vm():
	resp = VoiceResponse()
	resp.say('Please leave a message at the beep. \n Press the star key when complete.')
	resp.record(
		playBeep = True,
		max_length = 120,
		finish_on_key = '*',
		transcribe = True,
		action = "/vm-exit",
		transcribe_callback = "/transcribe-handle"
		)
	return str(resp)

@app.route("/transcribe-handle", methods=['POST'])
def transcribe_handle():
	text = request.form["TranscriptionText"]
	zenpy_client.tickets.create(Ticket(subject="VoiceMail", description=text))
	return text

@app.route("/vm-exit", methods=['GET', 'POST'])
def vm_exit():
	resp = VoiceResponse()
	resp.say("Thank you for leaving a voicemail. We will get back to you as soon as we can.")
	time.sleep(30)
	resp.hangup()
	return str(resp)

@app.route("/hold-handle", methods=['GET', 'POST'])
def hold_handle():
	resp = VoiceResponse()
	resp.play(hold_mp3, loop=0)
	return str(resp)
	
@app.route("/call-agent", methods=['GET', 'POST'])
def call_agent():
	resp = VoiceResponse()
	call = client.calls.create(to="+17204412178",
                           from_="+19704091327",
                           url="http://91c9adb2.ngrok.io/conf-mod")
	resp.redirect("/hold-handle")
	return str(resp)

if __name__ == '__main__':
    # Note that in production, you would want to disable debugging
    app.run(debug=True)
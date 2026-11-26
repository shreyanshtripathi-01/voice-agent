# Integration knowledge

## CRM
Qualified leads and booked appointments are written to a local SQLite CRM in the prototype. The production adapter maps the same fields to Salesforce, HubSpot or Zoho through their REST APIs, with retry and idempotency keys.

## Calendar
Appointment slots are checked before booking so two callers never receive the same confirmation. Confirmed meetings can be pushed to Google Calendar or Outlook and a reminder is sent to the prospect.

## Telephony
The prototype uses the browser microphone and speakers. A production deployment connects the same agent to Twilio or a SIP trunk through a media stream, keeping the conversation logic unchanged.

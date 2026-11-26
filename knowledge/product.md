# Product knowledge

## Capabilities
Ava, the Fortivex AI sales voice agent, listens and speaks in real time. It transcribes the caller with speech-to-text, understands intent, retrieves answers from the company knowledge base, and replies with text-to-speech. It remembers the whole conversation, tracks lead qualification, and books meetings into the CRM.

## Languages
The agent supports English, Hindi and Spanish in this prototype. The browser supplies the speech recognition language and the matching text-to-speech voice. The intent rules include Hindi and Spanish keywords, so a caller can switch languages mid-call.

## Knowledge retrieval
Answers to product questions come from a local markdown knowledge base. Documents are split into sections, converted to TF-IDF vectors at startup, and the closest sections are cited in the agent answer. This is the RAG layer and it works offline with no API key.

## Call summary
At the end of a call the system produces an extractive summary of the prospect's statements, the qualified BANT fields, the sentiment trend, objections heard, and a recommended next action. The summary is stored against the lead for later review.

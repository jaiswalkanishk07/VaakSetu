export const healthcareUseCase = {
  verticalLabel: "Healthcare & Emergency",
  subtitle:
    "VaakSetu listens to multilingual patient-doctor conversations in real time, extracts structured clinical data, and flags emergencies — eliminating manual post-call documentation.",

  transcript: [
    {
      role: "patient",
      text: "Doctor sahab, mujhe do din se bahut tez bukhar aa raha hai aur sar mein dard bhi hai.",
      meta: "Hindi · Patient · ASR Confidence 96%",
    },
    {
      role: "agent",
      text: "I understand. Can you tell me if you have any other symptoms — cough, body pain, or difficulty breathing?",
      meta: "VaakSetu Agent · Auto-follow-up",
    },
    {
      role: "patient",
      text: "Haan, thoda cough bhi hai aur body pain bhi. Breathing mein koi problem nahi hai.",
      meta: "Hinglish · Code-mixed · ASR Confidence 93%",
    },
    {
      role: "agent",
      text: "Thank you. Are you currently taking any medications or do you have known allergies?",
      meta: "VaakSetu Agent · Field Collection",
    },
    {
      role: "patient",
      text: "Paracetamol le raha hoon, allergy koi nahi hai.",
      meta: "Hindi · Patient · ASR Confidence 97%",
    },
  ],

  structuredTitle: "Extracted Clinical Record",
  structuredRows: [
    { label: "Patient Name", value: "Rajesh Kumar" },
    { label: "Age / Gender", value: "34 / Male" },
    { label: "Symptoms", value: "High Fever, Headache, Cough, Body Pain" },
    { label: "Duration", value: "2 Days" },
    { label: "Current Medication", value: "Paracetamol" },
    { label: "Allergies", value: "None Reported" },
    { label: "Breathing Difficulty", value: "No" },
    { label: "Risk Level", value: "Moderate" },
  ],

  highlight: {
    title: "Emergency Escalation",
    body: "VaakSetu continuously monitors conversations for critical keywords like \"chest pain\", \"saans nahi aa rahi\", or \"behosh\". If detected, an automatic escalation is triggered to alert the supervising clinician within seconds.",
  },

  features: [
    {
      title: "Multilingual ASR",
      desc: "Powered by Sarvam STT, VaakSetu accurately transcribes Hindi, English, and code-mixed Hinglish speech with speaker-role awareness across every turn.",
    },
    {
      title: "Auto Field Extraction",
      desc: "Symptoms, medications, allergies, and risk indicators are extracted in real time — no manual data entry needed after the consultation ends.",
    },
    {
      title: "Emergency Detection",
      desc: "Configurable escalation triggers scan every utterance for emergency phrases, automatically flagging high-risk cases for immediate clinical attention.",
    },
  ],
};

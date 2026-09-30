export const bankingUseCase = {
  verticalLabel: "Financial Services & Loan Recovery",
  subtitle:
    "VaakSetu autonomously conducts outbound loan-recovery calls via Twilio, captures payment commitments in real time, and generates compliance-ready audit logs — replacing expensive manual call centers.",

  transcript: [
    {
      role: "assistant",
      text: "Namaste, kya main Priya Sharma ji se baat kar sakta hoon? Main VaakSetu AI se bol raha hoon, ABC Finance ki taraf se.",
      meta: "VaakSetu Agent · Outbound · Hindi",
    },
    {
      role: "customer",
      text: "Haan bol rahi hoon. Kya kaam hai?",
      meta: "Customer · Hindi · ASR Confidence 95%",
    },
    {
      role: "assistant",
      text: "Aapke loan account LN-2024-78341 ka ₹12,500 ka EMI 15 din overdue hai. Kya aap payment date confirm kar sakti hain?",
      meta: "VaakSetu Agent · Field Collection",
    },
    {
      role: "customer",
      text: "Haan, salary delay ho gayi thi. Main 25 tareekh tak kar doongi payment.",
      meta: "Customer · Hinglish · ASR Confidence 92%",
    },
    {
      role: "assistant",
      text: "Dhanyavaad Priya ji. 25 June tak ₹12,500 ka payment note kar liya hai. Koi aur query hai?",
      meta: "VaakSetu Agent · Confirmation",
    },
  ],

  structuredTitle: "Extracted Recovery Record",
  structuredRows: [
    { label: "Customer Name", value: "Priya Sharma" },
    { label: "Loan Account", value: "LN-2024-78341" },
    { label: "Overdue Amount", value: "₹12,500" },
    { label: "Days Overdue", value: "15" },
    { label: "Payment Status", value: "Commitment Received" },
    { label: "Promised Date", value: "25 June 2025" },
    { label: "Delay Reason", value: "Salary Delay" },
    { label: "Confidence", value: "94%" },
  ],

  compliance: {
    bullets: [
      "Every outbound call is fully transcribed and stored with timestamped speaker attribution, ensuring complete audit trail compliance for RBI and internal governance frameworks.",
      "Automated escalation triggers detect threatening language, legal keywords, or fraud indicators in real time — pausing the conversation and routing to a human supervisor instantly.",
    ],
  },
};

"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Phone, Loader2, CheckCircle, AlertCircle } from "lucide-react";

export default function CallPage() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [domain, setDomain] = useState("healthcare");
  const [status, setStatus] = useState("idle"); // idle, calling, success, error
  const [message, setMessage] = useState("");

  const handleCall = async (e) => {
    e.preventDefault();
    if (!phoneNumber) return;
    
    setStatus("calling");
    setMessage("");

    try {
      const response = await fetch("http://localhost:8000/api/calls/outbound", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          to_number: phoneNumber,
          domain: domain,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setStatus("success");
        setMessage(`Calling ${phoneNumber}... Please answer your phone!`);
      } else {
        setStatus("error");
        setMessage(data.detail || "Failed to initiate call.");
      }
    } catch (error) {
      setStatus("error");
      setMessage("Network error. Make sure the backend is running on port 8000.");
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-6 relative">
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,rgba(249,115,22,0.1)_0%,transparent_50%)]" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="glass-card border border-border rounded-3xl p-8 md:p-10 shadow-2xl bg-background/60 backdrop-blur-3xl overflow-hidden">
          
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-saffron/10 text-saffron mb-4 ring-1 ring-saffron/20 shadow-[0_0_30px_rgba(249,115,22,0.2)]">
              <Phone size={28} />
            </div>
            <h1 className="text-3xl font-display text-foreground mb-2">Live AI Calling</h1>
            <p className="text-sm text-muted font-mono">
              Experience the power of VaakSetu's voice agents directly on your phone.
            </p>
          </div>

          <form onSubmit={handleCall} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-mono uppercase tracking-widest text-muted ml-1">Phone Number</label>
              <input
                type="tel"
                placeholder="+91 98765 43210"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full bg-surface/50 border border-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted/50 focus:outline-none focus:border-saffron focus:ring-1 focus:ring-saffron transition-all font-mono"
                required
              />
              <p className="text-[10px] text-muted ml-1 uppercase">Include country code (e.g., +91 or +1)</p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-mono uppercase tracking-widest text-muted ml-1">AI Domain Agent</label>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="w-full bg-surface/50 border border-border rounded-xl px-4 py-3 text-foreground focus:outline-none focus:border-saffron focus:ring-1 focus:ring-saffron transition-all appearance-none cursor-pointer"
              >
                <option value="healthcare">🏥 Healthcare (Symptoms, Prescriptions)</option>
                <option value="finance">💰 Finance (Investments, Portfolios)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={status === "calling" || !phoneNumber}
              className={`w-full py-4 rounded-xl flex items-center justify-center space-x-2 font-bold transition-all
                ${status === "calling" 
                  ? "bg-surface text-muted cursor-not-allowed" 
                  : "bg-saffron text-black hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(249,115,22,0.4)]"
                }
              `}
            >
              {status === "calling" ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Connecting...</span>
                </>
              ) : (
                <>
                  <Phone size={18} />
                  <span>Call Me Now</span>
                </>
              )}
            </button>
          </form>

          {/* Status Messages */}
          {status === "success" && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="mt-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 flex items-start space-x-3 text-green-400"
            >
              <CheckCircle size={20} className="shrink-0 mt-0.5" />
              <p className="text-sm font-medium">{message}</p>
            </motion.div>
          )}

          {status === "error" && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start space-x-3 text-red-400"
            >
              <AlertCircle size={20} className="shrink-0 mt-0.5" />
              <p className="text-sm font-medium">{message}</p>
            </motion.div>
          )}

        </div>
      </motion.div>
    </div>
  );
}

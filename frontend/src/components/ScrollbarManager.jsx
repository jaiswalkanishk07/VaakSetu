"use client";
import { useEffect } from "react";

export default function ScrollbarManager() {
  useEffect(() => {
    let timeout = null;
    const root = document.documentElement; // <html> — owns the page scrollbar in Chrome

    const onScroll = () => {
      root.classList.add("is-scrolling");
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        root.classList.remove("is-scrolling");
      }, 800);
    };

    window.addEventListener("scroll", onScroll, { passive: true, capture: true });
    return () => {
      window.removeEventListener("scroll", onScroll, { capture: true });
      clearTimeout(timeout);
    };
  }, []);

  return null;
}

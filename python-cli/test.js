// popup.js - Generalized Version for All Sites
"use strict";

const SERVER   = "http://localhost:8000";
const DOWNLOAD = `${SERVER}/add-download`;

// UI State
let state = {
  url: "",
  title: "Untitled Video",
  currentType: "video",
  qualityIdx: 3, // Default 1080p
  formatIdx: 0   // Default MP4
};

// ১. ট্যাব থেকে তথ্য সংগ্রহ করা
async function getActiveTabInfo() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    state.url = tab.url;
    state.title = tab.title || "Unknown Page";
    updateUI();
  }
}

// ২. সার্ভারে ডাউনলোড রিকোয়েস্ট পাঠানো
async function sendToPyFlow() {
  const btn = document.getElementById("dlBtn");
  btn.disabled = true;
  btn.innerText = "Sending...";

  const payload = {
    url: state.url,
    download_type: state.currentType,
    quality: VIDEO_QUALITIES[state.qualityIdx], // অথবা আপনার ম্যাপিং অনুযায়ী
    format: VIDEO_FORMATS[state.formatIdx].toLowerCase(),
    title: state.title
  };

  try {
    const response = await fetch(DOWNLOAD, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (data.status === "success") {
      showToast("✅ Added to Queue!");
    } else {
      showToast("❌ Server Error");
    }
  } catch (error) {
    showToast("⚠️ Server is offline");
  } finally {
    btn.disabled = false;
    btn.innerText = "Send to PyFlow";
  }
}

// ইনিশিয়ালাইজেশন
document.addEventListener("DOMContentLoaded", () => {
  getActiveTabInfo();
  document.getElementById("dlBtn").addEventListener("click", sendToPyFlow);
  // অন্যান্য বাটন লিসেনার এখানে থাকবে...
});

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.innerText = msg;
  toast.style.opacity = "1";
  setTimeout(() => { toast.style.opacity = "0"; }, 3000);
}
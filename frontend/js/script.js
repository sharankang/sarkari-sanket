const billForm = document.getElementById('bill-form');
const billNameInput = document.getElementById('billName');
const languageToggle = document.getElementById('language-toggle');
const langEn = document.getElementById('lang-en');
const langHi = document.getElementById('lang-hi');
const submitButton = document.getElementById('submit-button');
const errorMessage = document.getElementById('error-message');
const resultsWrapper = document.getElementById('results-wrapper');
const summaryTitle = document.getElementById('summary-title');
const summaryContent = document.getElementById('summary-content');
const sentimentBarWrapper = document.getElementById('sentiment-bar-wrapper');
const sentimentBar = document.getElementById('sentiment-bar');
const sentimentNote = document.getElementById('sentiment-note');
const sourceInfo = document.getElementById('source-info');
const historyList = document.getElementById("history-list");
const noHistory = document.getElementById("no-history");

function scrollToForm() {
  const formSection = document.getElementById("bill-form");
  if (formSection) {
    formSection.scrollIntoView({ behavior: "smooth" });
  }
}

languageToggle.addEventListener('change', () => {
  if (languageToggle.checked) {
    langEn.classList.remove('text-gray-800');
    langEn.classList.add('text-gray-400');
    langHi.classList.add('text-gray-800');
    langHi.classList.remove('text-gray-400');
  } else {
    langEn.classList.add('text-gray-800');
    langEn.classList.remove('text-gray-400');
    langHi.classList.remove('text-gray-800');
    langHi.classList.add('text-gray-400');
  }
});

document.addEventListener("DOMContentLoaded", () => {
  loadHistory();
});

function saveToHistory(billName, summary, sentiment, source) {
  let history = JSON.parse(localStorage.getItem("billHistory")) || [];

  //keep only last 5 items
  if (history.length >= 5) history.shift();

  history.push({
    billName,
    summary,
    sentiment,
    source,
    date: new Date().toLocaleString(),
  });

  localStorage.setItem("billHistory", JSON.stringify(history));
  loadHistory();
}

function loadHistory() {
  let history = JSON.parse(localStorage.getItem("billHistory")) || [];
  historyList.innerHTML = "";

  if (history.length === 0) {
    noHistory.style.display = "block";
    return;
  } else {
    noHistory.style.display = "none";
  }

  history.slice().reverse().forEach((item, index) => {
    const card = document.createElement("div");
    card.className =
      "bg-white rounded-xl shadow-md p-5 hover:shadow-xl transition";

    card.innerHTML = `
      <h3 class="text-lg font-bold text-gray-800 mb-2">🔎 ${item.billName}</h3>
      <p class="text-sm text-gray-500 mb-2">${item.date}</p>
      <p class="text-gray-700 text-sm mb-3">${item.summary.substring(0, 150)}...</p>
      <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm" onclick="restoreHistory(${history.length - 1 - index})">View Again</button>
    `;

    historyList.appendChild(card);
  });
}

function restoreHistory(index) {
  let history = JSON.parse(localStorage.getItem("billHistory")) || [];
  const item = history[index];
  if (!item) return;

  resultsWrapper.classList.remove("hidden");
  summaryTitle.textContent = `Summary (From History)`;
  summaryContent.innerHTML = item.summary;

  if (item.source) {
    sourceInfo.innerHTML = `Information sourced from: <a href="${item.source}" target="_blank" class="text-blue-600 hover:underline">${item.source}</a>`;
  } else {
    sourceInfo.innerHTML = "";
  }

  if (item.sentiment.startsWith("Positive")) {
    sentimentNote.classList.add("hidden");
    sentimentBarWrapper.classList.remove("hidden");

    const [p, n, nu] = item.sentiment.match(/\d+/g) || [0, 0, 0];
    sentimentBar.innerHTML = `
      <div class="flex justify-center items-center h-full bg-green-500 text-white text-xs font-bold" style="width: ${p}%">${p}%</div>
      <div class="flex justify-center items-center h-full bg-red-500 text-white text-xs font-bold" style="width: ${n}%">${n}%</div>
      <div class="flex justify-center items-center h-full bg-gray-400 text-white text-xs font-bold" style="width: ${nu}%">${nu}%</div>
    `;
  } else {
    sentimentBarWrapper.classList.add("hidden");
    sentimentNote.textContent = item.sentiment;
    sentimentNote.classList.remove("hidden");
  }
}

window.restoreHistory = restoreHistory;

billForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const selectedLanguage = languageToggle.checked ? 'Hinglish' : 'English';

  submitButton.disabled = true;
  submitButton.innerHTML = `<div class="loader"></div><span class="ml-3">Analyzing...</span>`;
  errorMessage.textContent = '';
  resultsWrapper.classList.add('hidden');
  
  try {
    const response = await fetch('https://sarkari-sanket-backend.onrender.com/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bill_name: billNameInput.value, language: selectedLanguage }),
    });

    const data = await response.json();

    if (!response.ok) {
      errorMessage.textContent = data.error || 'An unknown error occurred.';
      throw new Error(data.error);
    }
    
    resultsWrapper.classList.remove('hidden');
    summaryTitle.textContent = `Summary (${selectedLanguage})`;

    if (data.source_url) {
      sourceInfo.innerHTML = `Information sourced from: <a href="${data.source_url}" target="_blank" class="text-blue-600 hover:underline">${data.source_url}</a>`;
    }

    let summaryHtml = data.summary
      .replace(/### (.*?)\n/g, '<h3 class="text-2xl font-bold mt-6 mb-2">$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    summaryContent.innerHTML = summaryHtml;
    
    if (data.sentiment.note || data.sentiment.error) {
      sentimentBarWrapper.classList.add('hidden');
      sentimentNote.textContent = data.sentiment.note || data.sentiment.error;
      sentimentNote.classList.remove('hidden');
    } else {
      sentimentBarWrapper.classList.remove('hidden');
      sentimentNote.classList.add('hidden');
      const { positive, negative, neutral } = data.sentiment;
      sentimentBar.innerHTML = `
        <div class="flex justify-center items-center h-full bg-green-500 text-white text-xs font-bold" style="width: ${positive}%">${positive}%</div>
        <div class="flex justify-center items-center h-full bg-red-500 text-white text-xs font-bold" style="width: ${negative}%">${negative}%</div>
        <div class="flex justify-center items-center h-full bg-gray-400 text-white text-xs font-bold" style="width: ${neutral}%">${neutral}%</div>
      `;
    }

    saveToHistory(
      billNameInput.value,
      summaryHtml,
      data.sentiment.note || `Positive: ${data.sentiment.positive}%, Negative: ${data.sentiment.negative}%, Neutral: ${data.sentiment.neutral}%`,
      data.source_url || ""
    );

  } catch (error) {
    console.error("Fetch error:", error);
    if (!errorMessage.textContent) {
      errorMessage.textContent = 'Failed to analyze the bill. Please check the backend server.';
    }
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = 'Analyze Bill';
  }
});

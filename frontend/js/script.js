const billForm = document.getElementById('bill-form');
const billNameInput = document.getElementById('billName');
const languageToggle = document.getElementById('language-toggle');
const langEn = document.getElementById('lang-en');
const langHi = document.getElementById('lang-hi');
const submitButton = document.getElementById('submit-button');
const errorMessage = document.getElementById('error-message');
const resultsWrapper = document.getElementById('results-wrapper');
const summarySection = document.getElementById('summary-section');
const summaryTitle = document.getElementById('summary-title');
const summaryContent = document.getElementById('summary-content');
const sentimentSection = document.getElementById('sentiment-section');
const sentimentBarWrapper = document.getElementById('sentiment-bar-wrapper');
const sentimentBar = document.getElementById('sentiment-bar');
const sentimentNote = document.getElementById('sentiment-note');
const sourceInfo = document.getElementById('source-info');

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
        let summaryHtml = data.summary.replace(/### (.*?)\n/g, '<h3 class="text-2xl font-bold mt-6 mb-2">$1</h3>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        summaryContent.innerHTML = summaryHtml;
        
        if (data.sentiment.note || data.sentiment.error) {
            sentimentBarWrapper.classList.add('hidden');
            sentimentNote.textContent = data.sentiment.note || data.sentiment.error;
            sentimentNote.classList.remove('hidden');
        } else {
            sentimentBarWrapper.classList.remove('hidden');
            sentimentNote.classList.add('hidden');
            const { positive, negative, neutral } = data.sentiment;
            sentimentBar.innerHTML = `<div class="flex justify-center items-center h-full bg-green-500 text-white text-xs font-bold" style="width: ${positive}%">${positive}%</div><div class="flex justify-center items-center h-full bg-red-500 text-white text-xs font-bold" style="width: ${negative}%">${negative}%</div><div class="flex justify-center items-center h-full bg-gray-400 text-white text-xs font-bold" style="width: ${neutral}%">${neutral}%</div>`;
        }
        
    } catch (error) {
        console.error("Fetch error:", error);
        if(!errorMessage.textContent) {
            errorMessage.textContent = 'Failed to analyze the bill. Please check the backend server.';
        }
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = 'Analyze Bill';
    }
});

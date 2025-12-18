//Firebase Configuration
const firebaseConfig = {
  apiKey: "AIzaSyAgoz11nRfs5RVK8i_S5AI8rnzpFEDGP_w",
  authDomain: "sarkarisanket-543fb.firebaseapp.com",
  projectId: "sarkarisanket-543fb",
  storageBucket: "sarkarisanket-543fb.firebasestorage.app",
  messagingSenderId: "131068643687",
  appId: "1:131068643687:web:12b8299cc8174fc822c7c2",
  measurementId: "G-2J0T810FSS"
};

//Initialize Firebase
const firebaseApp = firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();

//Initialize Firebase Messaging for Push Notifications
let messaging = null;
try {
    messaging = firebase.messaging();
} catch (e) {
    console.warn("Firebase Messaging not initialized. Ensure scripts are in index.html.");
}

//Global State
let currentUser = null;
let currentToken = null;
let lastAnalyzedBillText = ""; 
const backendUrl = 'http://127.0.0.1:5000'; //local testing

//DOM References - Main Form & Results
const billForm = document.getElementById('bill-form');
const billNameInput = document.getElementById('billName');
const billFileInput = document.getElementById('billFile');
const languageToggle = document.getElementById('language-toggle');
const langEn = document.getElementById('lang-en');
const langHi = document.getElementById('lang-hi');
const submitButton = document.getElementById('submit-button');
const errorMessage = document.getElementById('error-message');

const resultsWrapper = document.getElementById('results-wrapper');
const summaryTitle = document.getElementById('summary-title');
const summaryContent = document.getElementById('summary-content');
const sourceInfo = document.getElementById('source-info');
const sentimentBar = document.getElementById('sentiment-bar');
const sentimentNote = document.getElementById('sentiment-note');

const impactSection = document.getElementById('impact-section');
const impactGrid = document.getElementById('impact-grid');
const chatbotSection = document.getElementById('chatbot-section');
const chatBox = document.getElementById('chat-box');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
const newsSection = document.getElementById('news-section');
const newsFeed = document.getElementById('news-feed');

//DOM References - Auth & Modals
const loginBtn = document.getElementById('login-btn');
const signupBtn = document.getElementById('signup-btn');
const logoutBtn = document.getElementById('logout-btn');
const authLinks = document.getElementById('auth-links');
const userInfo = document.getElementById('user-info');
const userEmail = document.getElementById('user-email');

const loginModal = document.getElementById('login-modal');
const signupModal = document.getElementById('signup-modal');
const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const loginError = document.getElementById('login-error');
const signupError = document.getElementById('signup-error');

const menuBtn = document.getElementById("menu-btn");
const mobileMenu = document.getElementById("mobile-menu");

//DOM References - Dashboard & Profile
const profileSection = document.getElementById("profile-section");
const profileForm = document.getElementById("profile-form");
const profileSaveBtn = document.getElementById("profile-save-btn");
const profileMessage = document.getElementById("profile-message");
const schemeResults = document.getElementById("scheme-results");
const schemeLoader = document.getElementById("scheme-loader");
const schemeList = document.getElementById("scheme-list");

const profileState = document.getElementById("profile-state");
const profileAge = document.getElementById("profile-age");
const profileSex = document.getElementById("profile-sex");
const profileOccupation = document.getElementById("profile-occupation");
const profileIncome = document.getElementById("profile-income");
const profileCategory = document.getElementById("profile-category");
const profileMaritalStatus = document.getElementById("profile-marital-status");
const onlyGirlChildField = document.getElementById("only-girl-child-field");
const profileOnlyGirlChild = document.getElementById("profile-only-girl-child");
const parentalStatusField = document.getElementById("parental-status-field");
const profileParentalStatus = document.getElementById("profile-parental-status");

const historyList = document.getElementById("history-list");
const noHistory = document.getElementById("no-history");

const navHistory = document.getElementById("nav-history");
const navProfile = document.getElementById("nav-profile");

const compareForm = document.getElementById("compare-form");
const compareBillName = document.getElementById("compareBillName");
const olderYear = document.getElementById("olderYear");
const compareLanguage = document.getElementById("compareLanguage");
const compareButton = document.getElementById("compare-button");
const compareError = document.getElementById("compare-error");
const compareResults = document.getElementById("compare-results");
const compareContent = document.getElementById("compare-content");

//Navigation & Scroll
function scrollToForm() {
    const formSection = document.getElementById("analyze");
    if (formSection) formSection.scrollIntoView({ behavior: "smooth" });
}

if (menuBtn) {
    menuBtn.addEventListener("click", () => mobileMenu.classList.toggle("hidden"));
}

//Push Notifications
function requestNotificationPermission() {
    if (!messaging || !currentUser) return;
    Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
            messaging.getToken({ vapidKey: 'YOUR_PUBLIC_VAPID_KEY' }).then((token) => {
                db.collection('users').doc(currentUser.uid).update({ fcmToken: token });
            });
        }
    });
}

// Language Toggle
if (languageToggle) {
    languageToggle.addEventListener('change', () => {
        if (languageToggle.checked) {
            langEn.classList.add('text-gray-400'); langEn.classList.remove('text-gray-800');
            langHi.classList.add('text-gray-800'); langHi.classList.remove('text-gray-400');
        } else {
            langEn.classList.add('text-gray-800'); langEn.classList.remove('text-gray-400');
            langHi.classList.add('text-gray-400'); langHi.classList.remove('text-gray-800');
        }
    });
}

//Dashboard Conditional
function checkConditionalFields() {
    const sex = profileSex.value;
    const ageValue = profileAge.value;
    const age = ageValue ? parseInt(ageValue, 10) : 0;
    
    if (sex === 'female') {
        onlyGirlChildField.classList.remove('hidden');
    } else {
        onlyGirlChildField.classList.add('hidden');
    }
    
    if (age > 0 && age < 18) {
        parentalStatusField.classList.remove('hidden');
    } else {
        parentalStatusField.classList.add('hidden');
    }
}

if (profileSex) profileSex.addEventListener('change', checkConditionalFields);
if (profileAge) profileAge.addEventListener('input', checkConditionalFields);

// Authentication
if (loginBtn) loginBtn.addEventListener('click', () => loginModal.classList.remove('hidden'));
if (signupBtn) signupBtn.addEventListener('click', () => signupModal.classList.remove('hidden'));
document.getElementById('close-login-modal').addEventListener('click', () => { loginModal.classList.add('hidden'); loginError.textContent = ""; });
document.getElementById('close-signup-modal').addEventListener('click', () => { signupModal.classList.add('hidden'); signupError.textContent = ""; });

if (logoutBtn) logoutBtn.addEventListener('click', () => {
    auth.signOut();
});

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.textContent = "";
    try {
        await auth.signInWithEmailAndPassword(document.getElementById('login-email').value, document.getElementById('login-password').value);
        loginModal.classList.add('hidden');
        loginForm.reset();
    } catch (err) { loginError.textContent = "Error: " + err.message; }
});

signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    signupError.textContent = "";
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    try {
        const res = await fetch(`${backendUrl}/api/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);
        
        await auth.signInWithEmailAndPassword(email, password);
        signupModal.classList.add('hidden');
        signupForm.reset();
    } catch (err) { signupError.textContent = "Error: " + err.message; }
});

auth.onAuthStateChanged(async (user) => {
    if (user) {
        currentUser = user;
        currentToken = await user.getIdToken();
        authLinks.classList.add('hidden');
        userInfo.classList.remove('hidden');
        userEmail.textContent = user.email;
        profileSection.classList.remove('hidden');
        loadHistory();
        loadProfile();
        requestNotificationPermission();
    } else {
        currentUser = null; currentToken = null;
        authLinks.classList.remove('hidden');
        userInfo.classList.add('hidden');
        profileSection.classList.add('hidden');
        noHistory.style.display = "block";
    }
});

//Dashboard persistence
async function loadProfile() {
    if (!currentUser || !currentToken) return;
    try {
        const response = await fetch(`${backendUrl}/api/get-profile`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        const profile = await response.json();
        if (response.ok && profile) {
            profileState.value = profile.state || "";
            profileAge.value = profile.age || "";
            profileSex.value = profile.sex || "male";
            profileOccupation.value = profile.occupation || "";
            profileIncome.value = profile.income || "";
            profileCategory.value = profile.category || "general";
            profileMaritalStatus.value = profile.marital_status || "single";
            profileOnlyGirlChild.value = profile.is_only_girl_child || "no";
            profileParentalStatus.value = profile.parental_status || "both_alive";
            checkConditionalFields();
        }
    } catch (err) { console.error("Profile load error:", err); }
}

if (profileForm) {
    profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        profileSaveBtn.disabled = true;
        profileSaveBtn.textContent = "Saving Full Profile...";
        const data = {
            state: profileState.value,
            age: profileAge.value,
            sex: profileSex.value,
            occupation: profileOccupation.value,
            income: profileIncome.value,
            category: profileCategory.value,
            marital_status: profileMaritalStatus.value,
            is_only_girl_child: profileOnlyGirlChild.value,
            parental_status: profileParentalStatus.value,
        };
        try {
            const res = await fetch(`${backendUrl}/api/update-profile`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${currentToken}` },
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error("Failed to save profile");
            profileMessage.textContent = "Profile Saved! Finding matching schemes...";
            profileMessage.className = "text-green-600 font-bold text-center mt-4";
            findSchemes();
        } catch (err) { 
            profileMessage.textContent = "Error saving profile."; 
            profileMessage.className = "text-red-600 font-bold text-center mt-4"; 
        } finally { 
            profileSaveBtn.disabled = false; 
            profileSaveBtn.textContent = "Save Full Profile"; 
        }
    });
}

//Bill Analysis & UI Logic
if (billForm) {
  billForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = submitButton;
    btn.disabled = true; btn.innerHTML = `<div class="loader"></div> <span class="ml-2">Processing...</span>`;
    errorMessage.textContent = '';
    
    const formData = new FormData();
    formData.append('bill_name', billNameInput.value);
    formData.append('language', languageToggle.checked ? 'Hinglish' : 'English');
    if (billFileInput.files[0]) formData.append('bill_file', billFileInput.files[0]);

    try {
      const response = await fetch(`${backendUrl}/api/analyze`, { 
          method: 'POST', 
          headers: currentToken ? { 'Authorization': `Bearer ${currentToken}` } : {},
          body: formData 
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);

      lastAnalyzedBillText = data.bill_text;
      resultsWrapper.classList.remove('hidden');

      //Summary
      summaryTitle.textContent = `Summary (${languageToggle.checked ? 'Hinglish' : 'English'})`;
      summaryContent.innerHTML = data.summary.replace(/### (.*?)\n/g, '<h3 class="text-xl font-bold mt-6 text-blue-900 border-b pb-2 mb-4">$1</h3>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

      if (data.source_url) {
        sourceInfo.innerHTML = `Sourced from: <a href="${data.source_url}" target="_blank" class="text-blue-600 underline">${data.source_url}</a>`;
      }

      //Sentiment + Impact 
      const { positive, negative, neutral } = data.sentiment;
      sentimentBar.innerHTML = `<div class="h-full bg-green-500" style="width:${positive}%"></div><div class="h-full bg-red-500" style="width:${negative}%"></div><div class="h-full bg-gray-300" style="width:${neutral}%\"></div>`;
      document.getElementById('sentiment-note').textContent = `Analysis results: ${positive}% Positive public sentiment.`;

      const relevant = Object.entries(data.impact_scores).filter(([_, v]) => v.score > 20); // Selective impact logic
      if (relevant.length > 0) {
          impactSection.classList.remove('hidden');
          impactGrid.innerHTML = relevant.map(([k, v]) => `
              <div class="p-4 border rounded-xl bg-gray-50 text-center">
                  <div class="text-[10px] uppercase font-bold text-gray-400 mb-1">${k}</div>
                  <div class="text-3xl font-black text-blue-600">${v.score}</div>
                  <p class="text-[9px] text-gray-400 mt-1 leading-tight">${v.reason}</p>
              </div>
          `).join('');
      } else { impactSection.classList.add('hidden'); }

      //Chatbot + News
      if (data.news && data.news.length > 0) {
          newsSection.classList.remove('hidden');
          newsFeed.innerHTML = data.news.map(item => `
              <div class="border-b border-gray-100 pb-3 mb-3 text-left">
                  <a href="${item.link}" target="_blank" class="text-sm font-bold text-blue-600 hover:underline block">${item.title}</a>
                  <p class="text-[11px] text-gray-400 mt-1 leading-snug">${item.snippet}</p>
              </div>
          `).join('');
      }

      saveToHistory();
    } catch (err) { errorMessage.textContent = err.message; }
    finally { btn.disabled = false; btn.innerHTML = 'Analyze Bill'; }
  });
}

//Chatbot- Sarkari Mitra
if (chatSend) {
    chatSend.addEventListener('click', async () => {
        const query = chatInput.value.trim();
        if (!query || !lastAnalyzedBillText) return;

        chatBox.innerHTML += `<div class="text-right mb-4"><span class="bg-blue-500 text-white p-3 rounded-xl text-xs inline-block shadow-sm">You: ${query}</span></div>`;
        chatInput.value = "";
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const res = await fetch(`${backendUrl}/api/chat`, { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ bill_text: lastAnalyzedBillText, query, language: 'English' }) 
            });
            const d = await res.json();
            chatBox.innerHTML += `<div class="text-left mb-4"><span class="bg-gray-100 p-3 rounded-xl text-xs inline-block border shadow-sm">Mitra: ${d.answer}</span></div>`;
            chatBox.scrollTop = chatBox.scrollHeight;
        } catch (err) { console.error("Chat error:", err); }
    });
}

//Comparison logic
if (compareForm) {
    compareForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        compareButton.disabled = true;
        compareButton.innerHTML = "Simplifying differences...";
        compareError.textContent = "";
        try {
            const res = await fetch(`${backendUrl}/api/compare`, { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ 
                    bill_name: compareBillName.value, 
                    older_year: olderYear.value, 
                    language: compareLanguage.value 
                }) 
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            compareResults.classList.remove('hidden');
            compareContent.innerHTML = data.comparison.replace(/### (.*?)\n/g, '<h3 class="text-lg font-bold mt-4 text-green-700 border-b pb-1">$1</h3>').replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        } catch (err) { compareError.textContent = err.message; }
        finally { compareButton.disabled = false; compareButton.innerHTML = "Compare Now"; }
    });
}

//Scheme discovery
async function findSchemes() {
    schemeResults.classList.remove("hidden"); schemeLoader.classList.remove("hidden"); schemeList.innerHTML = "";
    try {
        const response = await fetch(`${backendUrl}/api/find-schemes`, { headers: { 'Authorization': `Bearer ${currentToken}` } });
        const data = await response.json();
        const schemes = JSON.parse(data.schemes);
        if (schemes.length === 0) schemeList.innerHTML = `<p class="text-center text-gray-500 text-xs">No matching schemes found for your current profile.</p>`;
        else {
            schemes.forEach(scheme => {
                const card = document.createElement('div'); card.className = "scheme-card bg-white p-5 rounded-lg shadow border-l-4 border-blue-600 mb-4";
                card.innerHTML = `<h4 class="font-bold text-blue-800 text-sm">${scheme.scheme_name}</h4><p class="text-xs mt-2 text-gray-700">${scheme.summary}</p><a href="${scheme.link}" target="_blank" class="text-blue-600 text-[10px] underline mt-3 inline-block font-bold">Learn More</a>`;
                schemeList.appendChild(card);
            });
        }
    } catch (err) { console.error("Scheme fetch error:", err); }
    finally { schemeLoader.classList.add("hidden"); }
}

//History management
async function loadHistory() {
    if (!currentUser || !currentToken) return;
    try {
        const res = await fetch(`${backendUrl}/api/get-history`, { headers: { 'Authorization': `Bearer ${currentToken}` } });
        const history = await res.json();
        historyList.innerHTML = "";
        if (history.length > 0) {
            noHistory.style.display = "none";
            history.forEach(item => {
                const card = document.createElement("div"); 
                card.className = "bg-white p-5 rounded-xl border shadow-sm text-center transition hover:shadow-md";
                card.innerHTML = `
                    <h3 class="font-bold text-sm">🔎 ${item.billName}</h3>
                    <p class="text-[10px] text-gray-400 mb-2">${item.date}</p>
                    <button class="bg-blue-600 text-white px-3 py-1 rounded text-[10px] font-bold" onclick="restoreHistory('${item.id}')">View Analysis</button>
                `;
                historyList.appendChild(card);
            });
        } else { noHistory.style.display = "block"; }
    } catch (err) { console.error("History Error:", err); }
}

async function saveToHistory() {
    if (!currentUser) return;
    loadHistory();
}

async function restoreHistory(docId) {
    if (!currentToken) return;
    try {
        const res = await fetch(`${backendUrl}/api/get-history`, { headers: { 'Authorization': `Bearer ${currentToken}` } });
        const history = await res.json();
        const item = history.find(h => h.id === docId);
        if (item) {
            scrollToForm();
            resultsWrapper.classList.remove("hidden");
            summaryTitle.textContent = `Summary (History: ${item.billName})`;
            summaryContent.innerHTML = (item.summary || "").replace(/### (.*?)\n/g, '<h3 class="text-xl font-bold mt-6 text-blue-900 border-b pb-2 mb-4">$1</h3>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        }
    } catch (e) { console.error("Restore error:", e); }
}
window.restoreHistory = restoreHistory;
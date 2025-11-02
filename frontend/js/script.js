
const firebaseConfig = {
  apiKey: "AIzaSyAgoz11nRfs5RVK8i_S5AI8rnzpFEDGP_w",
  authDomain: "sarkarisanket-543fb.firebaseapp.com",
  projectId: "sarkarisanket-543fb",
  storageBucket: "sarkarisanket-543fb.firebasestorage.app",
  messagingSenderId: "131068643687",
  appId: "1:131068643687:web:12b8299cc8174fc822c7c2",
  measurementId: "G-2J0T810FSS"
};

// Initialize Firebase
const firebaseApp = firebase.initializeApp(firebaseConfig);

const auth = firebase.auth();
const db = firebase.firestore();

let currentUser = null;
let currentToken = null;
const backendUrl = 'http://127.0.0.1:5000'; // for local testing
// const backendUrl = 'https://sarkari-sanket-backend.onrender.com'; // for live deployment

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
const sentimentBarWrapper = document.getElementById('sentiment-bar-wrapper');
const sentimentBar = document.getElementById('sentiment-bar');
const sentimentNote = document.getElementById('sentiment-note');
const sourceInfo = document.getElementById('source-info');
const historyList = document.getElementById("history-list");
const noHistory = document.getElementById("no-history");
const compareForm = document.getElementById("compare-form");
const compareBillName = document.getElementById("compareBillName");
const olderYear = document.getElementById("olderYear");
const compareLanguage = document.getElementById("compareLanguage");
const compareButton = document.getElementById("compare-button");
const compareError = document.getElementById("compare-error");
const compareResults = document.getElementById("compare-results");
const compareContent = document.getElementById("compare-content");
const navHistory = document.getElementById("nav-history");
const navProfile = document.getElementById("nav-profile");

//Auth Element References 
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
const closeLoginModal = document.getElementById('close-login-modal');
const closeSignupModal = document.getElementById('close-signup-modal');
const loginError = document.getElementById('login-error');
const signupError = document.getElementById('signup-error');
const menuBtn = document.getElementById("menu-btn");
const mobileMenu = document.getElementById("mobile-menu");

//Profile & Scheme References
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


// ========== Homepage Scroll Function ==========
function scrollToForm() {
  const formSection = document.getElementById("analyze");
  if (formSection) {
    formSection.scrollIntoView({ behavior: "smooth" });
  }
}

//Language Toggle
if (languageToggle) {
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
}

// Auth UI Functions
function showLoginUI() {
    authLinks.classList.remove('hidden');
    userInfo.classList.add('hidden');
    
    navProfile.classList.add('hidden'); // Hide profile link
    profileSection.classList.add('hidden'); // Hide profile section
    
    navHistory.classList.remove('text-gray-400', 'pointer-events-none');
    noHistory.textContent = "Login to see your search history.";
    historyList.innerHTML = "";
    noHistory.style.display = "block";
}

function showLoggedInUI(user) {
    authLinks.classList.add('hidden');
    userInfo.classList.remove('hidden');
    
    navProfile.classList.remove('hidden'); // Show profile link
    profileSection.classList.remove('hidden'); // Show profile section
    
    navHistory.classList.remove('text-gray-400', 'pointer-events-none');
    userEmail.textContent = user.email;
    noHistory.textContent = "No history yet. Analyze a bill to see it here.";
    
    loadHistory();
    loadProfile();
}

if (loginBtn) {
    loginBtn.addEventListener('click', () => { loginModal.classList.remove('hidden'); });
    signupBtn.addEventListener('click', () => { signupModal.classList.remove('hidden'); });
    closeLoginModal.addEventListener('click', () => { loginModal.classList.add('hidden'); loginForm.reset(); loginError.textContent = ""; });
    closeSignupModal.addEventListener('click', () => { signupModal.classList.add('hidden'); signupForm.reset(); signupError.textContent = ""; });

    logoutBtn.addEventListener('click', () => {
        auth.signOut();
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginError.textContent = "";
        try {
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            await auth.signInWithEmailAndPassword(email, password);
            loginModal.classList.add('hidden');
            loginForm.reset();
        } catch (error) {
            loginError.textContent = "Error: " + error.message;
        }
    });

    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        signupError.textContent = "";
        try {
            const email = document.getElementById('signup-email').value;
            const password = document.getElementById('signup-password').value;
            
            const response = await fetch(`${backendUrl}/api/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error);
            }
            
            await auth.signInWithEmailAndPassword(email, password);
            signupModal.classList.add('hidden');
            signupForm.reset();
            
        } catch (error) {
            signupError.textContent = "Error: " + error.message;
        }
    });
}

auth.onAuthStateChanged(async (user) => {
    if (user) {
        currentUser = user;
        currentToken = await user.getIdToken();
        showLoggedInUI(user);
    } else {
        currentUser = null;
        currentToken = null;
        showLoginUI();
    }
});

async function saveToHistory() {
    if (!currentUser) return;
    console.log("Analysis complete, reloading history from server...");
    loadHistory();
}

async function loadHistory() {
    if (!currentUser || !currentToken) {
        historyList.innerHTML = "";
        noHistory.style.display = "block";
        return;
    }
    try {
        const response = await fetch(`${backendUrl}/api/get-history`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        const history = await response.json();
        if (!response.ok) throw new Error(history.error);
        
        historyList.innerHTML = "";
        if (history.length === 0) {
            noHistory.style.display = "block";
        } else {
            noHistory.style.display = "none";
            history.forEach((item) => {
                const card = document.createElement("div");
                card.className = "bg-white rounded-xl shadow-md p-5 hover:shadow-xl transition";
                let summaryPreview = (item.summary || "").replace(/<[^>]*>/g, '').substring(0, 150) + "...";
                card.innerHTML = `
                    <h3 class="text-lg font-bold text-gray-800 mb-2">🔎 ${item.billName}</h3>
                    <p class="text-sm text-gray-500 mb-2">${item.date}</p>
                    <p class="text-gray-700 text-sm mb-3">${summaryPreview}</p>
                    <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm" onclick="restoreHistory('${item.id}')">View Again</button>
                `;
                historyList.appendChild(card);
            });
        }
    } catch(err) {
        console.error("Error loading history:", err);
        noHistory.textContent = "Could not load history.";
        noHistory.style.display = "block";
    }
}

async function restoreHistory(docId) {
    if (!currentToken) return;
    let history = await (await fetch(`${backendUrl}/api/get-history`, {
        headers: { 'Authorization': `Bearer ${currentToken}` }
    })).json();
    
    const item = history.find(h => h.id === docId);
    if (!item) return;
    
    scrollToForm();
    resultsWrapper.classList.remove("hidden");
    summaryTitle.textContent = `Summary (From History: ${item.billName})`;
    
    let summaryHtml = (item.summary || "")
        .replace(/### (.*?)\n/g, '<h3 class="text-2xl font-bold mt-6 mb-2">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    summaryContent.innerHTML = summaryHtml;

    if (item.source) {
        sourceInfo.innerHTML = `Information sourced from: <a href="${item.source}" target="_blank" class="text-blue-600 hover:underline">${item.source}</a>`;
    } else {
        sourceInfo.innerHTML = "Information sourced from history.";
    }

    if (typeof item.sentiment === 'string') {
        sentimentBarWrapper.classList.add('hidden');
        sentimentNote.textContent = item.sentiment;
        sentimentNote.classList.remove('hidden');
    } else if (typeof item.sentiment === 'object' && item.sentiment !== null) {
        sentimentNote.classList.add('hidden');
        sentimentBarWrapper.classList.remove('hidden');
        const { positive, negative, neutral } = item.sentiment;
        sentimentBar.innerHTML = `
          <div class="flex justify-center items-center h-full bg-green-500 text-white text-xs font-bold" style="width: ${positive}%">${positive}%</div>
          <div class="flex justify-center items-center h-full bg-red-500 text-white text-xs font-bold" style="width: ${negative}%">${negative}%</div>
          <div class="flex justify-center items-center h-full bg-gray-400 text-white text-xs font-bold" style="width: ${neutral}%">${neutral}%</div>
        `;
    } else {
        sentimentBarWrapper.classList.add('hidden');
        sentimentNote.textContent = "Sentiment data not available for this entry.";
        sentimentNote.classList.remove('hidden');
    }
}
window.restoreHistory = restoreHistory;

if (compareForm) {
  compareForm.addEventListener("submit", async (e) => {
    e.preventDefault(); //stops the page from refreshing
    compareButton.disabled = true;
    compareButton.textContent = "Comparing...";
    compareError.textContent = "";
    compareResults.classList.add("hidden");
    try {
      const response = await fetch(`${backendUrl}/api/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bill_name: compareBillName.value,
          older_year: olderYear.value,
          language: compareLanguage.value,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        compareError.textContent = data.error || "An unknown error occurred.";
        throw new Error(data.error);
      }
      compareResults.classList.remove("hidden");
      let comparisonHtml = data.comparison
        .replace(/### (.*?)\n/g, '<h3 class="text-xl font-bold mt-4 mb-2">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      compareContent.innerHTML = comparisonHtml;
    } catch (err) {
      console.error("Comparison fetch error:", err);
      compareError.textContent = "Failed to compare bills. Please try again.";
    } finally {
      compareButton.disabled = false;
      compareButton.textContent = "Compare";
    }
  });
}

if (billForm) {
  billForm.addEventListener('submit', async (e) => {
    e.preventDefault(); //stops the page from refreshing
    const selectedLanguage = languageToggle.checked ? 'Hinglish' : 'English';
    const billName = billNameInput.value;
    const billFile = billFileInput.files[0];

    if (!billName && !billFile) {
        errorMessage.textContent = 'Please enter a bill name or upload a PDF file.';
        return;
    }
    submitButton.disabled = true;
    submitButton.innerHTML = `<div class="loader"></div><span class="ml-3">Analyzing...</span>`;
    errorMessage.textContent = '';
    resultsWrapper.classList.add('hidden');
    
    const formData = new FormData();
    formData.append('bill_name', billName);
    formData.append('language', selectedLanguage);
    if (billFile) {
        formData.append('bill_file', billFile);
    }
    
    try {
      const headers = {};
      if (currentToken) {
          headers['Authorization'] = `Bearer ${currentToken}`;
      }

      const response = await fetch(`${backendUrl}/api/analyze`, {
        method: 'POST',
        headers: headers,
        body: formData,
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
      saveToHistory();

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
}

function checkConditionalFields() {
    if (profileSex.value === 'female') {
        onlyGirlChildField.classList.remove('hidden');
    } else {
        onlyGirlChildField.classList.add('hidden');
    }
    
    const age = parseInt(profileAge.value, 10);
    if (age > 0 && age < 18) {
        parentalStatusField.classList.remove('hidden');
    } else {
        parentalStatusField.classList.add('hidden');
    }
}

if (profileSex) {
    profileSex.addEventListener('change', checkConditionalFields);
}
if (profileAge) {
    profileAge.addEventListener('input', checkConditionalFields);
}

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
            profileMaritalStatus.value = profile.marital_status || "na";
            profileOnlyGirlChild.value = profile.is_only_girl_child || "no";
            profileParentalStatus.value = profile.parental_status || "both_alive";
            
            checkConditionalFields();
        }
    } catch (err) {
        console.error("Error loading profile:", err);
    }
}

if (profileForm) {
    profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        profileSaveBtn.disabled = true;
        profileSaveBtn.textContent = "Saving...";
        profileMessage.textContent = "";
        
        const profileData = {
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
            const response = await fetch(`${backendUrl}/api/update-profile`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${currentToken}`
                },
                body: JSON.stringify(profileData)
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            
            profileMessage.textContent = "Profile saved! Finding your schemes...";
            profileMessage.classList.remove('text-red-600');
            profileMessage.classList.add('text-green-600');

            findSchemes();

        } catch (err) {
            profileMessage.textContent = `Error: ${err.message}`;
            profileMessage.classList.remove('text-green-600');
            profileMessage.classList.add('text-red-600');
        } finally {
            profileSaveBtn.disabled = false;
            profileSaveBtn.textContent = "Save Profile & Find Schemes";
        }
    });
}

async function findSchemes() {
    schemeResults.classList.remove("hidden");
    schemeLoader.classList.remove("hidden");
    schemeList.innerHTML = ""; // Clear old results

    try {
        const response = await fetch(`${backendUrl}/api/find-schemes`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);

        const schemes = JSON.parse(data.schemes);

        if (schemes.length === 0) {
            schemeList.innerHTML = `<p class="text-center text-gray-600">No specific schemes found matching your exact profile from our sources. Try broadening your profile.</p>`;
        } else {
            schemes.forEach(scheme => {
                const card = document.createElement('div');
                card.className = "scheme-card";
                card.innerHTML = `
                    <h4 class="text-xl font-bold text-blue-800 mb-2">${scheme.scheme_name}</h4>
                    <p class="text-gray-700 mb-3">${scheme.summary}</p>
                    <p class="text-gray-600 text-sm mb-4"><strong>Eligibility:</strong> ${scheme.eligibility}</p>
                    <a href="${scheme.link || '#'}" target="_blank" class="text-blue-600 font-medium hover:underline">Learn More</a>
                `;
                schemeList.appendChild(card);
            });
        }
    } catch (err) {
        console.error("Error finding schemes:", err);
        schemeList.innerHTML = `<p class="text-center text-red-600">Error finding schemes: ${err.message}</p>`;
    } finally {
        schemeLoader.classList.add("hidden");
    }
}

if (menuBtn) {
    menuBtn.addEventListener("click", () => {
      mobileMenu.classList.toggle("hidden");
    });
}
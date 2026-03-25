document.addEventListener('DOMContentLoaded', function () {
  // -------------------------------
  // MENU TOGGLE (Mobile menu open/close)
  // -------------------------------
// MENU TOGGLE (Mobile menu open/close) - Line 7 civarı
const menuToggle = document.getElementById('menuToggle');
const menuPanel = document.getElementById('menuPanel');
const mainContent = document.getElementById('mainContent'); // 👈 Bu satırı ekleyin
const body = document.body;

if (menuToggle && menuPanel && mainContent) { // 👈 mainContent kontrolü ekleyin
    menuToggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const isOpen = menuPanel.classList.contains('open');
        if (isOpen) {
            menuPanel.classList.remove('open');
            mainContent.classList.remove('menu-pushed'); // 👈 Bu satırı ekleyin
            body.classList.remove('menu-open');
            menuToggle.innerHTML = '☰';
        } else {
            menuPanel.classList.add('open');
            mainContent.classList.add('menu-pushed'); // 👈 Bu satırı ekleyin
            body.classList.add('menu-open');
            menuToggle.innerHTML = '✕';
        }
    });

    // Close menu when clicking outside
    document.addEventListener('click', function (e) {
        if (!menuPanel.contains(e.target) && !menuToggle.contains(e.target)) {
            if (menuPanel.classList.contains('open')) {
                menuPanel.classList.remove('open');
                mainContent.classList.remove('menu-pushed'); // 👈 Bu satırı ekleyin
                body.classList.remove('menu-open');
                menuToggle.innerHTML = '☰';
            }
        }
    });

    // Close menu when clicking on links
    menuPanel.addEventListener('click', function (e) {
        if (e.target.tagName === 'A') {
            menuPanel.classList.remove('open');
            mainContent.classList.remove('menu-pushed'); // 👈 Bu satırı ekleyin
            body.classList.remove('menu-open');
            menuToggle.innerHTML = '☰';
        }
    });

    // Close menu with ESC key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && menuPanel.classList.contains('open')) {
            menuPanel.classList.remove('open');
            mainContent.classList.remove('menu-pushed'); // 👈 Bu satırı ekleyin
            body.classList.remove('menu-open');
            menuToggle.innerHTML = '☰';
        }
    });
}

  // -------------------------------
  // MENU ACTIVE CLASS
  // -------------------------------
  const currentPath = window.location.pathname;
  const menuLinks = document.querySelectorAll('nav a, .menu-panel a');
  menuLinks.forEach(link => {
      if (link.getAttribute('href') === currentPath) {
          link.classList.add('active');
      }
  });

  // -------------------------------
  // FLASH MESSAGES (auto-hide)
  // -------------------------------
  const flashMessages = document.querySelectorAll('.flash-message');
  flashMessages.forEach(function (message) {
      setTimeout(function () {
          if (message.parentElement) {
              message.style.animation = 'slideOutRight 0.3s ease-in forwards';
              setTimeout(function () {
                  if (message.parentElement) {
                      message.remove();
                  }
              }, 300);
          }
      }, 5000);
  });

  document.querySelectorAll('.flash-close').forEach(function (btn) {
      btn.addEventListener('click', function () {
          this.parentElement.remove();
      });
  });

  document.querySelectorAll('.flash-message').forEach(function (msg) {
      msg.addEventListener('click', function () {
          this.remove();
      });
  });

  // -------------------------------
  // COOKIE BANNER
  // -------------------------------
  const cookieBanner = document.getElementById('cookieBanner');
  if (cookieBanner) {
      setTimeout(function () {
          cookieBanner.classList.add('show');
      }, 1000);

      const acceptAllBtn = document.getElementById('acceptAllBtn');
      if (acceptAllBtn) {
          acceptAllBtn.addEventListener('click', function () {
              fetch('/api/cookie-consent', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                      essential: true,
                      analytics: true,
                      marketing: true,
                      functional: true
                  })
              })
              .then(res => res.json())
              .then(data => {
                  if (data.success) {
                      cookieBanner.style.animation = 'slideDown 0.3s ease-in forwards';
                      setTimeout(function () {
                          cookieBanner.remove();
                      }, 300);
                  }
              })
              .catch(err => console.error('Cookie consent error:', err));
          });
      }
  }

  // -------------------------------
  // USER MENU (dropdown)
  // -------------------------------
  const userMenuToggle = document.getElementById('userMenuToggle');
  if (userMenuToggle) {
      userMenuToggle.addEventListener('click', function () {
          const dropdown = document.getElementById('userDropdown');
          if (dropdown) {
              dropdown.classList.toggle('show');
          }
      });
  }

  // Close user menu when clicking outside
  document.addEventListener('click', function (e) {
      const userMenu = document.querySelector('.user-menu');
      const dropdown = document.getElementById('userDropdown');
      if (userMenu && dropdown && !userMenu.contains(e.target)) {
          dropdown.classList.remove('show');
      }
  });

  // -------------------------------
  // CONFIRM BUTTONS (CSP-safe)
  // -------------------------------
    document.querySelectorAll("form[data-confirm]").forEach(form => {
        form.addEventListener("submit", e => {
            const confirmMsg = form.dataset.confirm;
            if (confirmMsg && !confirm(confirmMsg)) {
                e.preventDefault();
                return false;
            }
        });
    });



  // -------------------------------
  // UNIVERSAL HANDLERS WITH NULL CHECKS
  // -------------------------------

  // File upload trigger
  document.querySelectorAll("[data-trigger-file]").forEach(el => {
      el.addEventListener("click", () => {
          const fileId = el.getAttribute("data-trigger-file");
          const fileInput = document.getElementById(fileId);
          if (fileInput) fileInput.click();
      });
  });

  // Browser info + current URL auto-fill
  const browserInfoEl = document.getElementById("browser_info");
  const errorUrlEl = document.getElementById("error_url");
  if (browserInfoEl) browserInfoEl.value = navigator.userAgent;
  if (errorUrlEl) errorUrlEl.value = window.location.href;

  // Resend verification button
  const resendBtn = document.getElementById("resendVerificationBtn");
  if (resendBtn) {
      resendBtn.addEventListener("click", () => {
          if (typeof resendVerification === "function") {
              resendVerification();
          }
      });
  }

  // Download data button
  const downloadBtn = document.getElementById("downloadBtn");
  if (downloadBtn) {
      downloadBtn.addEventListener("click", () => {
          if (typeof requestDataDownload === "function") {
              requestDataDownload();
          }
      });
  }

  // Delete account button
  const deleteBtn = document.getElementById("deleteBtn");
  if (deleteBtn) {
      deleteBtn.addEventListener("click", () => {
          if (typeof deleteAccount === "function") {
              deleteAccount();
          }
      });
  }

  // Clear history button
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");
  if (clearHistoryBtn) {
      clearHistoryBtn.addEventListener("click", () => {
          if (typeof clearHistory === "function") {
              clearHistory();
          }
      });
  }

  // Delete chat buttons
  document.querySelectorAll(".delete-chat-btn").forEach(btn => {
      btn.addEventListener("click", () => {
          const chatId = btn.dataset.chatId;
          if (chatId && typeof deleteChat === "function") {
              deleteChat(chatId);
          }
      });
  });

  // Accept/Reject All buttons
  document.querySelectorAll(".accept-all-btn, [data-action='accept-all']").forEach(btn => {
      btn.addEventListener("click", () => {
          if (typeof acceptAll === "function") {
              acceptAll();
          }
      });
  });

  document.querySelectorAll(".reject-all-btn, [data-action='reject-all']").forEach(btn => {
      btn.addEventListener("click", () => {
          if (typeof rejectAll === "function") {
              rejectAll();
          }
      });
  });

  // Complaint type selection
  document.querySelectorAll(".complaint-type").forEach(el => {
      el.addEventListener("click", () => {
          const type = el.getAttribute("data-type") || el.dataset.type;
          const input = el.querySelector("input[type=radio]") || el.querySelector(`input[value="${type}"]`);
          if (input) {
              input.checked = true;
          }
          if (typeof selectComplaintType === "function") {
              selectComplaintType(type);
          }
      });
  });

  // Remove file buttons
  document.querySelectorAll("[data-action='remove-file']").forEach(btn => {
      btn.addEventListener("click", () => {
          const index = btn.getAttribute("data-index");
          if (typeof removeFile === "function") {
              removeFile(index);
          }
      });
  });

  // Copy code buttons
  document.querySelectorAll("[data-action='copy-code']").forEach(btn => {
      btn.addEventListener("click", () => {
          const codeContent = btn.closest(".code-block")?.querySelector(".code-content");
          if (codeContent) {
              navigator.clipboard.writeText(codeContent.innerText)
                  .then(() => {
                      if (typeof copyCode === "function") {
                          copyCode(btn);
                      }
                  })
                  .catch(err => console.error("Copy failed:", err));
          }
      });
  });

  // Tab functionality
  document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
          const tabName = btn.dataset.tab;
          const tabContent = document.getElementById(tabName + "-tab");
          
          if (tabContent) {
              // Hide all tab contents
              document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
              // Show selected tab
              tabContent.style.display = "block";

              // Update tab buttons
              document.querySelectorAll(".tab-btn").forEach(b => {
                  b.style.color = "#9ca3af";
                  b.style.borderBottomColor = "transparent";
                  b.classList.remove("active");
              });
              btn.style.color = "white";
              btn.style.borderBottomColor = "#667eea";
              btn.classList.add("active");
          }
      });
  });

  // Priority selection (with null check)
  document.querySelectorAll('.priority-option').forEach(option => {
      option.addEventListener('click', function() {
          document.querySelectorAll('.priority-option').forEach(opt => opt.classList.remove('selected'));
          this.classList.add('selected');
          const priorityInput = document.getElementById('priority');
          if (priorityInput) {
              priorityInput.value = this.dataset.priority;
          }
      });
  });

  // File upload feedback (with null check)
  const fileUpload = document.getElementById('file_upload');
  if (fileUpload) {
      fileUpload.addEventListener('change', function() {
          const fileName = this.files[0]?.name;
          if (fileName) {
              const fileSize = this.files[0]?.size;
              if (fileSize > 5242880) { // 5MB
                  alert('File size cannot exceed 5MB / Dosya boyutu 5MB\'dan büyük olamaz');
                  this.value = '';
                  return;
              }
              
              const fileUploadContainer = document.querySelector('.file-upload');
              if (fileUploadContainer) {
                  fileUploadContainer.innerHTML = `
                      <div style="font-size: 2rem; margin-bottom: 10px;">✅</div>
                      <div style="color: #22c55e; margin-bottom: 5px;">File Selected / Dosya Seçildi</div>
                      <div style="color: #999; font-size: 0.9rem;">${fileName}</div>
                  `;
              }
          }
      });
  }

  // Error report form submission (with null check)
  const errorForm = document.getElementById('errorReportForm');
  if (errorForm) {
      errorForm.addEventListener('submit', function(e) {
          e.preventDefault();
          
          const priorityInput = document.getElementById('priority');
          const priority = priorityInput ? priorityInput.value : '';
          if (!priority) {
              alert('Please select priority level / Lütfen öncelik seviyesini seçin');
              return;
          }
          
          const submitBtn = document.querySelector('.submit-btn');
          if (submitBtn) {
              submitBtn.disabled = true;
              submitBtn.textContent = 'Submitting... / Gönderiliyor...';
          }
          
          const formData = new FormData(this);
          
          fetch('/api/submit-error-report', {
              method: 'POST',
              body: formData
          })
          .then(response => response.json())
          .then(data => {
              if (data.success) {
                  alert(`Error report submitted successfully! Tracking ID: ${data.ticket_id} / Hata raporu başarıyla gönderildi! Takip numarası: ${data.ticket_id}`);
                  // Use relative URL instead of template syntax
                  window.location.href = '/dashboard';
              } else {
                  alert('Error / Hata: ' + data.error);
                  if (submitBtn) {
                      submitBtn.disabled = false;
                      submitBtn.textContent = '🚀 Submit Error Report / Hata Raporunu Gönder';
                  }
              }
          })
          .catch(error => {
              alert('An error occurred during submission / Gönderim sırasında hata oluştu');
              if (submitBtn) {
                  submitBtn.disabled = false;
                  submitBtn.textContent = '🚀 Submit Error Report / Hata Raporunu Gönder';
              }
          });
      });
  }
});

// -------------------------------
// JQUERY EVENT DELEGATION (if jQuery is available)
// -------------------------------
if (typeof $ !== 'undefined') {
    // Remove file (delegation)
    $(document).on('click', '.remove-file', function() {
        const index = $(this).closest('.uploaded-file').data('index');
        if (typeof removeFile === "function") {
            removeFile(index);
        }
    });

    // Copy code (delegation)
    $(document).on('click', '.copy-btn', function() {
        const codeContent = $(this).closest('.code-block').find('.code-content').text();
        navigator.clipboard.writeText(codeContent).then(() => {
            const btn = $(this);
            const original = btn.html();
            btn.html('<i class="bi bi-check"></i> Copied!');
            setTimeout(() => btn.html(original), 2000);
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('contactForm');
  
  // Contact form sadece varsa çalıştır
  if (!form) return;
  
  const submitBtn = document.getElementById('submitBtn');
  const btnText = document.querySelector('.btn-text');
  const btnLoading = document.querySelector('.btn-loading');
  
  // Gerekli elementler yoksa işlemi durdur
  if (!submitBtn) return;
  
  // Form validation
  function validateField(field) {
    if (!field) return true;
    
    const formGroup = field.closest('.form-group');
    if (!formGroup) return true;
    
    const errorDiv = formGroup.querySelector('.form-error');
    
    // Remove previous error state
    formGroup.classList.remove('has-error');
    
    let isValid = true;
    
    // Required field check
    if (field.hasAttribute('required') && !field.value.trim()) {
      isValid = false;
    }
    
    // Pattern check
    if (field.hasAttribute('pattern') && field.value.trim()) {
      const pattern = new RegExp(field.getAttribute('pattern'));
      if (!pattern.test(field.value)) {
        isValid = false;
      }
    }
    
    // Length checks
    if (field.hasAttribute('minlength') && field.value.length > 0) {
      if (field.value.length < parseInt(field.getAttribute('minlength'))) {
        isValid = false;
      }
    }
    
    // Email specific validation
    if (field.type === 'email' && field.value.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(field.value)) {
        isValid = false;
      }
    }
    
    if (!isValid) {
      formGroup.classList.add('has-error');
    }
    
    return isValid;
  }
  
  // Real-time validation
  const inputs = form.querySelectorAll('input[required], textarea[required]');
  
  if (inputs.length > 0) {
    inputs.forEach(input => {
      input.addEventListener('blur', () => validateField(input));
      input.addEventListener('input', () => {
        const formGroup = input.closest('.form-group');
        if (formGroup && formGroup.classList.contains('has-error')) {
          validateField(input);
        }
      });
    });
  }
  
  // Form submit
  form.addEventListener('submit', function(e) {
    let formIsValid = true;
    
    // Validate all required fields
    inputs.forEach(input => {
      if (!validateField(input)) {
        formIsValid = false;
      }
    });
    
    if (!formIsValid) {
      e.preventDefault();
      alert('Please fill in all required fields correctly.');
      return false;
    }
    
    // Suspicious content check - null check ekle
    const nameField = document.getElementById('name');
    const emailField = document.getElementById('email');
    const messageField = document.getElementById('message');
    
    const name = nameField ? nameField.value : '';
    const email = emailField ? emailField.value : '';
    const message = messageField ? messageField.value : '';
    
    const suspiciousPatterns = [
      /<script/i,
      /javascript:/i,
      /<iframe/i,
      /onclick=/i,
      /onerror=/i,
      /onload=/i,
      /<a\s+href/i
    ];
    
    const allText = (name + ' ' + email + ' ' + message).toLowerCase();
    
    for (let pattern of suspiciousPatterns) {
      if (pattern.test(allText)) {
        e.preventDefault();
        alert('Your message could not be sent for security reasons. Please do not use HTML codes.');
        return false;
      }
    }
    
    // Double submit prevention
    if (submitBtn.disabled) {
      e.preventDefault();
      return false;
    }
    
    // Show loading state - null check ile
    submitBtn.disabled = true;
    if (btnText) btnText.style.display = 'none';
    if (btnLoading) btnLoading.style.display = 'inline';
    
    // Re-enable button after 30 seconds (in case of network issues)
    setTimeout(function() {
      if (submitBtn) {
        submitBtn.disabled = false;
        if (btnText) btnText.style.display = 'inline';
        if (btnLoading) btnLoading.style.display = 'none';
      }
    }, 30000);
  });
  
  // Input sanitization - tüm sayfalarda çalışabilir
  const textInputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
  
  if (textInputs.length > 0) {
    textInputs.forEach(function(input) {
      input.addEventListener('paste', function(e) {
        setTimeout(function() {
          let value = input.value;
          // Remove HTML tags
          value = value.replace(/<[^>]*>/g, '');
          // Remove suspicious characters
          value = value.replace(/[<>'"&]/g, '');
          input.value = value;
        }, 10);
      });
      
      input.addEventListener('input', function(e) {
        let value = e.target.value;
        // Prevent HTML tags in real-time
        if (/<[^>]*>/.test(value)) {
          e.target.value = value.replace(/<[^>]*>/g, '');
        }
      });
    });
  }
});

document.addEventListener('DOMContentLoaded', function() {
  // Resend verification function - sadece gerekli sayfalarda çalışır
  function resendVerification() {
    // User email elementini kontrol et
    const userEmailMeta = document.querySelector('meta[name="user-email"]');
    const userEmail = userEmailMeta ? userEmailMeta.content : null;
    
    if (!userEmail) {
      alert('User email not found / Kullanıcı email bulunamadı');
      return;
    }
    
    fetch('/resend-verification', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'email=' + encodeURIComponent(userEmail)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert('Verification email sent! Check your email / Doğrulama maili gönderildi! Email adresinizi kontrol edin.');
      } else {
        alert('An error occurred. Please try again later / Bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred. Please try again later / Bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
    });
  }

  // Global olarak erişilebilir yap
  window.resendVerification = resendVerification;

  // Resend verification button event listener (zaten var ama güvenlik için tekrar)
  const resendBtn = document.getElementById("resendVerificationBtn");
  if (resendBtn) {
    resendBtn.addEventListener("click", () => {
      resendVerification();
    });
  }
});


// -------------------------------
// CHANGE PASSWORD FORM HANDLER
// -------------------------------
// Change password form functionality - only runs if form exists
const changePasswordForm = document.getElementById('changePasswordForm');
if (changePasswordForm) {
    const newPasswordInput = document.getElementById('new_password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const changePasswordBtn = document.getElementById('changePasswordBtn');
    const strengthIndicator = document.getElementById('password-strength');
    const matchIndicator = document.getElementById('password-match');
    
    // Language detection for messages - check for lang meta tag or default to 'tr'
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    // Password strength messages
    const strengthMessages = {
        en: {
            0: { text: 'Very Weak', color: '#ef4444' },
            1: { text: 'Weak', color: '#f59e0b' },
            2: { text: 'Fair', color: '#f59e0b' },
            3: { text: 'Good', color: '#22c55e' },
            4: { text: 'Strong', color: '#22c55e' },
            5: { text: 'Very Strong', color: '#22c55e' }
        },
        tr: {
            0: { text: 'Çok Zayıf', color: '#ef4444' },
            1: { text: 'Zayıf', color: '#f59e0b' },
            2: { text: 'Orta', color: '#f59e0b' },
            3: { text: 'İyi', color: '#22c55e' },
            4: { text: 'Güçlü', color: '#22c55e' },
            5: { text: 'Çok Güçlü', color: '#22c55e' }
        }
    };
    
    // Password match messages
    const matchMessages = {
        en: { match: 'Passwords match', noMatch: 'Passwords do not match' },
        tr: { match: 'Şifreler eşleşiyor', noMatch: 'Şifreler eşleşmiyor' }
    };
    
    // Error messages
    const errorMessages = {
        en: {
            noMatch: 'Passwords do not match!',
            weakPassword: 'Password is too weak. Please choose a stronger password.',
            changing: 'Changing...'
        },
        tr: {
            noMatch: 'Şifreler eşleşmiyor!',
            weakPassword: 'Şifre çok zayıf. Lütfen daha güçlü bir şifre seçin.',
            changing: 'Değiştiriliyor...'
        }
    };
    
    // Password strength checker function
    function checkPasswordStrength(password) {
        if (!strengthIndicator) return 0;
        
        let strength = 0;
        if (password.length >= 8) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^A-Za-z0-9]/.test(password)) strength++;
        
        const lang = isEnglish ? 'en' : 'tr';
        const strengthLevel = strengthMessages[lang][strength];
        
        if (password.length > 0) {
            strengthIndicator.textContent = strengthLevel.text;
            strengthIndicator.style.color = strengthLevel.color;
            strengthIndicator.style.display = 'block';
        } else {
            strengthIndicator.style.display = 'none';
        }
        
        return strength;
    }
    
    // Password match checker function
    function checkPasswordMatch() {
        if (!matchIndicator || !newPasswordInput || !confirmPasswordInput) return;
        
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        const lang = isEnglish ? 'en' : 'tr';
        
        if (confirmPassword.length > 0) {
            if (newPassword === confirmPassword) {
                matchIndicator.textContent = matchMessages[lang].match;
                matchIndicator.style.color = '#22c55e';
            } else {
                matchIndicator.textContent = matchMessages[lang].noMatch;
                matchIndicator.style.color = '#ef4444';
            }
            matchIndicator.style.display = 'block';
        } else {
            matchIndicator.style.display = 'none';
        }
    }
    
    // Event listeners - only if elements exist
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            checkPasswordStrength(this.value);
            if (confirmPasswordInput && confirmPasswordInput.value) {
                checkPasswordMatch();
            }
        });
    }
    
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    }
    
    // Form validation and submission
    changePasswordForm.addEventListener('submit', function(e) {
        const currentPassword = document.getElementById('current_password');
        const newPassword = document.getElementById('new_password');
        const confirmPassword = document.getElementById('confirm_password');
        
        // Check if all required elements exist
        if (!currentPassword || !newPassword || !confirmPassword) {
            return; // Let default form validation handle this
        }
        
        const lang = isEnglish ? 'en' : 'tr';
        
        // Check if passwords match
        if (newPassword.value !== confirmPassword.value) {
            e.preventDefault();
            alert(errorMessages[lang].noMatch);
            return false;
        }
        
        // Check password strength
        const strength = checkPasswordStrength(newPassword.value);
        if (strength < 3) {
            e.preventDefault();
            alert(errorMessages[lang].weakPassword);
            return false;
        }
        
        // Prevent double submission
        if (changePasswordBtn) {
            changePasswordBtn.disabled = true;
            const originalText = changePasswordBtn.textContent;
            changePasswordBtn.textContent = errorMessages[lang].changing;
            
            // Re-enable button after 30 seconds (safety measure)
            setTimeout(function() {
                if (changePasswordBtn) {
                    changePasswordBtn.disabled = false;
                    changePasswordBtn.textContent = originalText;
                }
            }, 30000);
        }
    });
    
    // Input sanitization for security - consistent with base.js pattern
    const passwordInputs = changePasswordForm.querySelectorAll('input[type="password"]');
    if (passwordInputs.length > 0) {
        passwordInputs.forEach(function(input) {
            input.addEventListener('paste', function(e) {
                setTimeout(function() {
                    // Remove any HTML tags or suspicious characters
                    let value = input.value;
                    value = value.replace(/<[^>]*>/g, '');
                    value = value.replace(/[<>"'&]/g, '');
                    input.value = value;
                }, 10);
            });
        });
    }
}

// -------------------------------
// DATA DOWNLOAD FUNCTIONALITY
// -------------------------------
// Data download functionality - only runs if download button exists
const downloadDataBtn = document.getElementById('downloadBtn');

if (downloadDataBtn) {
    // Language detection
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    // Messages for different languages
    const downloadMessages = {
        en: {
            confirm: 'Are you sure you want to download all your data?',
            preparing: 'Preparing...',
            dataCollection: 'Starting data collection process...',
            completed: '✅ Completed',
            error: '❌ Error: ',
            connectionError: '❌ Connection error occurred',
            retry: '📥 Try Again',
            success: '✅ Data preparation completed!<br><strong>Download link has been sent to your email.</strong><br><small>Request ID: ',
            preparing_long: 'Data preparation in progress...',
        },
        tr: {
            confirm: 'Tüm verilerinizi indirmek istediğinizden emin misiniz?',
            preparing: 'Hazırlanıyor...',
            dataCollection: 'Veri toplama işlemi başlatılıyor...',
            completed: '✅ Tamamlandı',
            error: '❌ Hata: ',
            connectionError: '❌ Bağlantı hatası oluştu',
            retry: '📥 Tekrar Dene',
            success: '✅ Veri hazırlama tamamlandı!<br><strong>İndirme linki email adresinize gönderildi.</strong><br><small>Talep ID: ',
            preparing_long: 'Veri hazırlama işlemi devam ediyor...',
        }
    };
    
    const msg = isEnglish ? downloadMessages.en : downloadMessages.tr;
}

// Request data download function (global scope)
function requestDataDownload() {
    const btn = document.getElementById('downloadBtn');
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    const statusMessage = document.getElementById('statusMessage');
    
    if (!btn) return;
    
    // Language detection
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    // Messages
    const messages = {
        en: {
            confirm: 'Are you sure you want to download all your data?',
            preparing: 'Preparing...',
            dataCollection: 'Starting data collection process...',
            completed: '✅ Completed',
            error: '❌ Error: ',
            connectionError: '❌ Connection error occurred',
            retry: '📥 Try Again',
            success: '✅ Data preparation completed!<br><strong>Download link has been sent to your email.</strong><br><small>Request ID: ',
            btnStart: '📥 Start Data Download'
        },
        tr: {
            confirm: 'Tüm verilerinizi indirmek istediğinizden emin misiniz?',
            preparing: 'Hazırlanıyor...',
            dataCollection: 'Veri toplama işlemi başlatılıyor...',
            completed: '✅ Tamamlandı',
            error: '❌ Hata: ',
            connectionError: '❌ Bağlantı hatası oluştu',
            retry: '📥 Tekrar Dene',
            success: '✅ Veri hazırlama tamamlandı!<br><strong>İndirme linki email adresinize gönderildi.</strong><br><small>Talep ID: ',
            btnStart: '📥 Veri İndirmeyi Başlat'
        }
    };
    
    const msg = isEnglish ? messages.en : messages.tr;
    
    // Confirm dialog
    if (!confirm(msg.confirm)) {
        return;
    }
    
    // Disable button and show progress
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = msg.preparing;
    
    if (progressBar) {
        progressBar.style.display = 'block';
    }
    
    if (statusMessage) {
        statusMessage.style.display = 'block';
        statusMessage.textContent = msg.dataCollection;
    }
    
    // Progress simulation
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        if (progressFill) {
            progressFill.style.width = progress + '%';
        }
    }, 500);
    
    // Make the API request
    fetch('/api/request-data-download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            format: 'json',
            include_ai_data: true,
            include_logs: true
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        clearInterval(progressInterval);
        
        if (progressFill) {
            progressFill.style.width = '100%';
        }
        
        if (data.success) {
            if (statusMessage) {
                statusMessage.innerHTML = msg.success + data.request_id + '</small>';
            }
            btn.textContent = msg.completed;
            
            // Redirect after success
            setTimeout(() => {
                const dashboardUrl = document.querySelector('a[href*="dashboard"]')?.href || '/dashboard';
                window.location.href = dashboardUrl;
            }, 3000);
        } else {
            if (statusMessage) {
                statusMessage.textContent = msg.error + (data.error || 'Unknown error');
            }
            resetButton();
        }
    })
    .catch(error => {
        console.error('Download request error:', error);
        clearInterval(progressInterval);
        
        if (statusMessage) {
            statusMessage.textContent = msg.connectionError;
        }
        resetButton();
    });
    
    function resetButton() {
        btn.disabled = false;
        btn.textContent = msg.retry;
        
        // Reset to original text after a delay
        setTimeout(() => {
            if (btn && !btn.disabled) {
                btn.textContent = originalText;
            }
        }, 5000);
    }
    
    // Safety timeout - re-enable button after 60 seconds
    setTimeout(() => {
        if (btn && btn.disabled) {
            resetButton();
        }
    }, 60000);
}

// -------------------------------
// DELETE ACCOUNT FUNCTIONALITY
// -------------------------------
// Delete account page functionality - only runs if elements exist
const deleteAccountForm = {
  confirmationInput: document.getElementById('confirmationInput'),
  finalConfirmation: document.getElementById('finalConfirmation'),
  deleteBtn: document.getElementById('deleteBtn')
};

if (deleteAccountForm.confirmationInput && deleteAccountForm.finalConfirmation && deleteAccountForm.deleteBtn) {
  // Language detection
  const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
  const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
  const isEnglish = currentLang === 'en';
  
  // Confirmation text based on language
  const confirmationTexts = {
      en: 'DELETE MY ACCOUNT',
      tr: 'HESABIMI SIL'
  };
  
  const requiredText = isEnglish ? confirmationTexts.en : confirmationTexts.tr;
  
  // Messages for different languages
  const deleteMessages = {
      en: {
          finalWarning: 'FINAL WARNING: This action cannot be undone. Do you really want to delete your account?',
          deleting: 'Deleting...',
          success: 'Your account has been successfully deleted. Redirecting to homepage.',
          error: 'Error: ',
          connectionError: 'Connection error occurred',
          btnDelete: '🗑️ Permanently Delete Account'
      },
      tr: {
          finalWarning: 'SON UYARI: Bu işlem geri alınamaz. Hesabınızı gerçekten silmek istiyor musunuz?',
          deleting: 'Siliniyor...',
          success: 'Hesabınız başarıyla silindi. Ana sayfaya yönlendiriliyorsunuz.',
          error: 'Hata: ',
          connectionError: 'Bağlantı hatası oluştu',
          btnDelete: '🗑️ Hesabı Kalıcı Olarak Sil'
      }
  };
  
  const msg = isEnglish ? deleteMessages.en : deleteMessages.tr;
  
  // Check confirmation function
  function checkDeleteConfirmation() {
      const input = deleteAccountForm.confirmationInput;
      const checkbox = deleteAccountForm.finalConfirmation;
      const btn = deleteAccountForm.deleteBtn;
      
      if (!input || !checkbox || !btn) return;
      
      const textCorrect = input.value.trim().toUpperCase() === requiredText;
      const checkboxChecked = checkbox.checked;
      
      // Visual feedback for input
      if (textCorrect) {
          input.classList.add('valid');
      } else {
          input.classList.remove('valid');
      }
      
      // Enable/disable delete button
      btn.disabled = !(textCorrect && checkboxChecked);
  }
  
  // Event listeners for confirmation checks
  deleteAccountForm.confirmationInput.addEventListener('input', checkDeleteConfirmation);
  deleteAccountForm.finalConfirmation.addEventListener('change', checkDeleteConfirmation);
  
  // Convert input to uppercase for better UX
  deleteAccountForm.confirmationInput.addEventListener('input', function() {
      this.value = this.value.toUpperCase();
  });
}

// Delete account function (global scope for onclick)
function deleteAccount() {
  const btn = document.getElementById('deleteBtn');
  if (!btn || btn.disabled) return;
  
  // Language detection
  const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
  const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
  const isEnglish = currentLang === 'en';
  
  // Messages
  const messages = {
      en: {
          finalWarning: 'FINAL WARNING: This action cannot be undone. Do you really want to delete your account?',
          deleting: 'Deleting...',
          success: 'Your account has been successfully deleted. Redirecting to homepage.',
          error: 'Error: ',
          connectionError: 'Connection error occurred',
          btnDelete: '🗑️ Permanently Delete Account'
      },
      tr: {
          finalWarning: 'SON UYARI: Bu işlem geri alınamaz. Hesabınızı gerçekten silmek istiyor musunuz?',
          deleting: 'Siliniyor...',
          success: 'Hesabınız başarıyla silindi. Ana sayfaya yönlendiriliyorsunuz.',
          error: 'Hata: ',
          connectionError: 'Bağlantı hatası oluştu',
          btnDelete: '🗑️ Hesabı Kalıcı Olarak Sil'
      }
  };
  
  const msg = isEnglish ? messages.en : messages.tr;
  const confirmationText = isEnglish ? 'DELETE MY ACCOUNT' : 'HESABIMI SIL';
  
  // Final warning confirmation
  if (!confirm(msg.finalWarning)) {
      return;
  }
  
  // Disable button and show loading
  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = msg.deleting;
  
  // Additional visual feedback
  btn.style.background = 'linear-gradient(135deg, #6b7280, #4b5563)';
  
  // Make the delete request
  fetch('/api/delete-account', {
      method: 'DELETE',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          confirmation: confirmationText,
          final_confirmation: true
      })
  })
  .then(response => {
      if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
  })
  .then(data => {
      if (data.success) {
          alert(msg.success);
          
          // Redirect based on language
          const redirectUrl = isEnglish ? '/en' : '/';
          
          // Add delay to ensure user sees the success message
          setTimeout(() => {
              window.location.href = redirectUrl;
          }, 1000);
      } else {
          throw new Error(data.error || 'Unknown error');
      }
  })
  .catch(error => {
      console.error('Delete account error:', error);
      
      // Show appropriate error message
      if (error.message.includes('HTTP')) {
          alert(msg.connectionError);
      } else {
          alert(msg.error + error.message);
      }
      
      // Reset button state
      resetDeleteButton();
  });
  
  // Reset button function
  function resetDeleteButton() {
      if (btn) {
          btn.disabled = false;
          btn.textContent = originalText;
          btn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
          
          // Re-run confirmation check to ensure proper state
          const input = document.getElementById('confirmationInput');
          const checkbox = document.getElementById('finalConfirmation');
          
          if (input && checkbox) {
              const textCorrect = input.value.trim().toUpperCase() === confirmationText;
              const checkboxChecked = checkbox.checked;
              btn.disabled = !(textCorrect && checkboxChecked);
          }
      }
  }
  
  // Safety timeout - reset button after 60 seconds if still processing
  setTimeout(() => {
      if (btn && btn.disabled && btn.textContent === msg.deleting) {
          resetDeleteButton();
      }
  }, 60000);
}

// -------------------------------
// PRIVACY SETTINGS FUNCTIONALITY
// -------------------------------
// Privacy settings page functionality - only runs if form exists
const privacySettingsForm = document.getElementById('privacySettingsForm');

if (privacySettingsForm) {
    // Language detection
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    // Messages for different languages
    const privacyMessages = {
        en: {
            acceptAllConfirm: 'Accept all privacy settings? This will enable all data processing consents.',
            rejectAllConfirm: 'Reject all optional privacy settings? Essential services may be affected.',
            saving: 'Saving...',
            saved: 'Settings saved successfully!',
            error: 'Error saving settings: ',
            connectionError: 'Connection error occurred',
            acceptingAll: 'Accepting all...',
            rejectingAll: 'Rejecting all...',
            allAccepted: 'All settings accepted',
            allRejected: 'Optional settings rejected',
            btnSave: '💾 Save Settings',
            btnAcceptAll: '✅ Accept All',
            btnRejectAll: '❌ Reject All'
        },
        tr: {
            acceptAllConfirm: 'Tüm gizlilik ayarlarını kabul et? Bu tüm veri işleme onaylarını etkinleştirecek.',
            rejectAllConfirm: 'Tüm isteğe bağlı gizlilik ayarlarını reddet? Temel hizmetler etkilenebilir.',
            saving: 'Kaydediliyor...',
            saved: 'Ayarlar başarıyla kaydedildi!',
            error: 'Ayarları kaydetme hatası: ',
            connectionError: 'Bağlantı hatası oluştu',
            acceptingAll: 'Tümü kabul ediliyor...',
            rejectingAll: 'Tümü reddediliyor...',
            allAccepted: 'Tüm ayarlar kabul edildi',
            allRejected: 'İsteğe bağlı ayarlar reddedildi',
            btnSave: '💾 Ayarları Kaydet',
            btnAcceptAll: '✅ Tümünü Kabul Et',
            btnRejectAll: '❌ Tümünü Reddet'
        }
    };
    
    const msg = isEnglish ? privacyMessages.en : privacyMessages.tr;
    
    // Form submission handling
    const saveBtn = document.getElementById('saveSettingsBtn');
    
    privacySettingsForm.addEventListener('submit', function(e) {
        if (saveBtn) {
            saveBtn.disabled = true;
            const originalText = saveBtn.textContent;
            saveBtn.textContent = msg.saving;
            
            // Re-enable button after 30 seconds (safety measure)
            setTimeout(function() {
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }
            }, 30000);
        }
    });
    
    // Visual feedback for checkbox changes
    const checkboxes = privacySettingsForm.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const formCheck = this.closest('.form-check');
            if (formCheck) {
                if (this.checked) {
                    formCheck.style.background = 'rgba(34, 197, 94, 0.1)';
                    formCheck.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                } else {
                    formCheck.style.background = 'rgba(15, 20, 35, 0.5)';
                    formCheck.style.borderColor = 'transparent';
                }
            }
        });
        
        // Apply initial styling
        const formCheck = checkbox.closest('.form-check');
        if (formCheck && checkbox.checked) {
            formCheck.style.background = 'rgba(34, 197, 94, 0.1)';
            formCheck.style.borderColor = 'rgba(34, 197, 94, 0.3)';
        }
    });
    
    // Data retention period change handler
    const retentionSelect = document.getElementById('ai_data_retention_days');
    if (retentionSelect) {
        retentionSelect.addEventListener('change', function() {
            // Visual feedback for retention period change
            this.style.background = 'rgba(34, 197, 94, 0.1)';
            this.style.borderColor = 'rgba(34, 197, 94, 0.5)';
            
            setTimeout(() => {
                this.style.background = 'rgba(15, 20, 35, 0.8)';
                this.style.borderColor = 'rgba(255,255,255,0.2)';
            }, 2000);
        });
    }
}

// Accept All function (global scope for onclick)
function acceptAll() {
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    const confirmMessage = isEnglish 
        ? 'Accept all privacy settings? This will enable all data processing consents.'
        : 'Tüm gizlilik ayarlarını kabul et? Bu tüm veri işleme onaylarını etkinleştirecek.';
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    const acceptBtn = document.querySelector('.accept-all-btn');
    if (acceptBtn) {
        acceptBtn.disabled = true;
        const originalText = acceptBtn.textContent;
        acceptBtn.textContent = isEnglish ? '⏳ Accepting all...' : '⏳ Tümü kabul ediliyor...';
    }
    
    // Check all consent checkboxes
    const checkboxes = document.querySelectorAll('#privacySettingsForm input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change'));
    });
    
    // Set maximum retention period
    const retentionSelect = document.getElementById('ai_data_retention_days');
    if (retentionSelect) {
        retentionSelect.value = '365';
        retentionSelect.dispatchEvent(new Event('change'));
    }
    
    // Auto-submit form
    setTimeout(() => {
        const form = document.getElementById('privacySettingsForm');
        if (form) {
            form.submit();
        }
    }, 500);
    
    // Reset button after 5 seconds if form doesn't submit
    setTimeout(() => {
        if (acceptBtn && acceptBtn.disabled) {
            acceptBtn.disabled = false;
            acceptBtn.textContent = originalText;
        }
    }, 5000);
}

// Reject All function (global scope for onclick)
function rejectAll() {
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    const confirmMessage = isEnglish 
        ? 'Reject all optional privacy settings? Essential services may be affected.'
        : 'Tüm isteğe bağlı gizlilik ayarlarını reddet? Temel hizmetler etkilenebilir.';
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    const rejectBtn = document.querySelector('.reject-all-btn');
    if (rejectBtn) {
        rejectBtn.disabled = true;
        const originalText = rejectBtn.textContent;
        rejectBtn.textContent = isEnglish ? '⏳ Rejecting all...' : '⏳ Tümü reddediliyor...';
    }
    
    // Uncheck optional consent checkboxes (keep data_processing_consent checked as it's essential)
    const marketingConsent = document.getElementById('marketing_consent');
    const aiDataConsent = document.getElementById('ai_data_consent');
    
    if (marketingConsent) {
        marketingConsent.checked = false;
        marketingConsent.dispatchEvent(new Event('change'));
    }
    
    if (aiDataConsent) {
        aiDataConsent.checked = false;
        aiDataConsent.dispatchEvent(new Event('change'));
    }
    
    // Set minimum retention period
    const retentionSelect = document.getElementById('ai_data_retention_days');
    if (retentionSelect) {
        retentionSelect.value = '30';
        retentionSelect.dispatchEvent(new Event('change'));
    }
    
    // Auto-submit form
    setTimeout(() => {
        const form = document.getElementById('privacySettingsForm');
        if (form) {
            form.submit();
        }
    }, 500);
    
    // Reset button after 5 seconds if form doesn't submit
    setTimeout(() => {
        if (rejectBtn && rejectBtn.disabled) {
            rejectBtn.disabled = false;
            rejectBtn.textContent = originalText;
        }
    }, 5000);
}


// -------------------------------
// PROFILE SETTINGS FUNCTIONALITY
// -------------------------------
// Profile settings page functionality - only runs if form exists
const profileForm = document.getElementById('profileForm');

if (profileForm) {
    // Language detection
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    // Messages for different languages
    const profileMessages = {
        en: {
            saving: 'Saving...',
            saved: 'Profile updated successfully!',
            error: 'Error updating profile: ',
            connectionError: 'Connection error occurred',
            btnSave: '💾 Save Changes',
            invalidName: 'Name must be at least 2 characters long',
            invalidPhone: 'Please enter a valid phone number',
            namePattern: 'Name can only contain letters, spaces, and hyphens',
            phonePattern: 'Phone number format: +country area number'
        },
        tr: {
            saving: 'Kaydediliyor...',
            saved: 'Profil başarıyla güncellendi!',
            error: 'Profil güncelleme hatası: ',
            connectionError: 'Bağlantı hatası oluştu',
            btnSave: '💾 Değişiklikleri Kaydet',
            invalidName: 'İsim en az 2 karakter olmalıdır',
            invalidPhone: 'Lütfen geçerli bir telefon numarası girin',
            namePattern: 'İsim sadece harf, boşluk ve tire içerebilir',
            phonePattern: 'Telefon numarası formatı: +ülke alan numara'
        }
    };
    
    const msg = isEnglish ? profileMessages.en : profileMessages.tr;
    
    // Form validation patterns
    const namePattern = /^[a-zA-ZçÇğĞıİöÖşŞüÜ\s\-']{2,}$/;
    const phonePattern = /^[\+]?[0-9\s\-\(\)]{10,20}$/;
    
    // Real-time validation for name fields
    const nameFields = ['first_name', 'last_name'];
    nameFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', function() {
                validateNameField(this);
            });
            field.addEventListener('blur', function() {
                validateNameField(this);
            });
        }
    });
    
    // Real-time validation for phone field
    const phoneField = document.getElementById('phone');
    if (phoneField) {
        phoneField.addEventListener('input', function() {
            validatePhoneField(this);
        });
        phoneField.addEventListener('blur', function() {
            validatePhoneField(this);
        });
    }
    
    // Language change handler with visual feedback
    const languageSelect = document.getElementById('preferred_language');
    if (languageSelect) {
        languageSelect.addEventListener('change', function() {
            this.style.background = 'rgba(34, 197, 94, 0.15)';
            this.style.borderColor = 'rgba(34, 197, 94, 0.5)';
            
            setTimeout(() => {
                this.style.background = 'rgba(255,255,255,0.08)';
                this.style.borderColor = 'rgba(255,255,255,0.2)';
            }, 2000);
        });
    }
    
    // Name field validation function
    function validateNameField(field) {
        if (!field) return true;
        
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        if (value.length < 2) {
            isValid = false;
            errorMessage = msg.invalidName;
        } else if (!namePattern.test(value)) {
            isValid = false;
            errorMessage = msg.namePattern;
        }
        
        showFieldValidation(field, isValid, errorMessage);
        return isValid;
    }
    
    // Phone field validation function
    function validatePhoneField(field) {
        if (!field) return true;
        
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        // Phone is optional, so empty is valid
        if (value.length > 0 && !phonePattern.test(value)) {
            isValid = false;
            errorMessage = msg.phonePattern;
        }
        
        showFieldValidation(field, isValid, errorMessage);
        return isValid;
    }
    
    // Show field validation feedback
    function showFieldValidation(field, isValid, errorMessage) {
        if (!field) return;
        
        // Remove existing error message
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        if (!isValid && errorMessage) {
            // Add error styling
            field.style.borderColor = '#ef4444';
            field.style.background = 'rgba(239, 68, 68, 0.1)';
            
            // Add error message
            const errorDiv = document.createElement('small');
            errorDiv.className = 'field-error';
            errorDiv.style.cssText = 'color: #ef4444; font-size: 0.8rem; margin-top: 5px; display: block;';
            errorDiv.textContent = errorMessage;
            field.parentNode.appendChild(errorDiv);
        } else {
            // Remove error styling
            field.style.borderColor = isValid && field.value.trim() ? '#22c55e' : 'rgba(255,255,255,0.2)';
            field.style.background = isValid && field.value.trim() ? 'rgba(34, 197, 94, 0.1)' : 'rgba(255,255,255,0.08)';
        }
    }
    
    // Form submission handling
    const saveBtn = document.getElementById('saveProfileBtn');
    
    profileForm.addEventListener('submit', function(e) {
        let formIsValid = true;
        
        // Validate all fields before submission
        nameFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field && !validateNameField(field)) {
                formIsValid = false;
            }
        });
        
        if (phoneField && !validatePhoneField(phoneField)) {
            formIsValid = false;
        }
        
        if (!formIsValid) {
            e.preventDefault();
            
            // Focus first invalid field
            const firstError = profileForm.querySelector('.field-error');
            if (firstError) {
                const errorField = firstError.closest('.form-group').querySelector('input');
                if (errorField) {
                    errorField.focus();
                }
            }
            
            return false;
        }
        
        // Show loading state
        if (saveBtn) {
            saveBtn.disabled = true;
            const originalText = saveBtn.textContent;
            saveBtn.textContent = msg.saving;
            
            // Re-enable button after 30 seconds (safety measure)
            setTimeout(function() {
                if (saveBtn) {
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }
            }, 30000);
        }
    });
    
    // Avatar update when name changes
    const firstNameField = document.getElementById('first_name');
    const lastNameField = document.getElementById('last_name');
    const avatar = document.querySelector('.profile-avatar');
    
    function updateAvatar() {
        if (avatar && firstNameField && lastNameField) {
            const firstName = firstNameField.value.trim();
            const lastName = lastNameField.value.trim();
            
            if (firstName.length > 0 && lastName.length > 0) {
                avatar.textContent = firstName[0].toUpperCase() + lastName[0].toUpperCase();
            }
        }
    }
    
    if (firstNameField) {
        firstNameField.addEventListener('input', updateAvatar);
    }
    
    if (lastNameField) {
        lastNameField.addEventListener('input', updateAvatar);
    }
    
    // Input sanitization for security
    const textInputs = profileForm.querySelectorAll('input[type="text"], input[type="tel"]');
    textInputs.forEach(function(input) {
        input.addEventListener('paste', function(e) {
            setTimeout(function() {
                let value = input.value;
                // Remove HTML tags and suspicious characters
                value = value.replace(/<[^>]*>/g, '');
                value = value.replace(/[<>"'&]/g, '');
                input.value = value;
                
                // Re-validate after sanitization
                if (input.id === 'first_name' || input.id === 'last_name') {
                    validateNameField(input);
                } else if (input.id === 'phone') {
                    validatePhoneField(input);
                }
            }, 10);
        });
    });
}

// -------------------------------
// ERROR REPORT FUNCTIONALITY
// -------------------------------
// Error report functionality is already handled by the universal handlers in base.js
// Priority selection, file upload feedback, and form submission are covered

// Additional specific handlers for error report form
const errorReportForm = document.getElementById('errorReportForm');
if (errorReportForm) {
    // Language detection
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    // Messages for different languages
    const errorReportMessages = {
        en: {
            selectPriority: 'Please select priority level',
            submitting: 'Submitting...',
            submitted: 'Error report submitted successfully! Tracking ID: ',
            error: 'Error: ',
            connectionError: 'An error occurred during submission',
            fileTooLarge: 'File size cannot exceed 5MB',
            btnSubmit: '🚀 Submit Error Report',
            fileSelected: 'File Selected',
            uploadFile: 'Upload File'
        },
        tr: {
            selectPriority: 'Lütfen öncelik seviyesini seçin',
            submitting: 'Gönderiliyor...',
            submitted: 'Hata raporu başarıyla gönderildi! Takip numarası: ',
            error: 'Hata: ',
            connectionError: 'Gönderim sırasında hata oluştu',
            fileTooLarge: 'Dosya boyutu 5MB\'dan büyük olamaz',
            btnSubmit: '🚀 Hata Raporunu Gönder',
            fileSelected: 'Dosya Seçildi',
            uploadFile: 'Dosya Yükle'
        }
    };
    
    const msg = isEnglish ? errorReportMessages.en : errorReportMessages.tr;
    
    // Form validation before submission
    errorReportForm.addEventListener('submit', function(e) {
        const priorityInput = document.getElementById('priority');
        const submitBtn = errorReportForm.querySelector('.submit-btn');
        
        // Check priority selection
        if (!priorityInput || !priorityInput.value) {
            e.preventDefault();
            alert(msg.selectPriority);
            return false;
        }
        
        // Show loading state
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = msg.submitting;
        }
        
        // Re-enable button after 30 seconds (safety measure)
        setTimeout(function() {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = msg.btnSubmit;
            }
        }, 30000);
    });
    
    // Enhanced file upload feedback with language support
    const fileUpload = document.getElementById('file_upload');
    if (fileUpload) {
        fileUpload.addEventListener('change', function() {
            const fileName = this.files[0]?.name;
            const fileSize = this.files[0]?.size;
            const fileUploadContainer = document.querySelector('.file-upload');
            
            if (!fileName) return;
            
            if (fileSize > 5242880) { // 5MB
                alert(msg.fileTooLarge);
                this.value = '';
                return;
            }
            
            if (fileUploadContainer) {
                fileUploadContainer.classList.add('file-selected');
                fileUploadContainer.innerHTML = `
                    <div style="font-size: 2rem; margin-bottom: 10px;">✅</div>
                    <div style="color: #22c55e; margin-bottom: 5px;">${msg.fileSelected}</div>
                    <div style="color: #999; font-size: 0.9rem;">${fileName}</div>
                `;
            }
        });
    }
    
    // Character counter for description textarea
    const descriptionTextarea = document.getElementById('error_description');
    if (descriptionTextarea) {
        const maxLength = parseInt(descriptionTextarea.getAttribute('maxlength')) || 2000;
        
        // Create character counter element
        const counterDiv = document.createElement('div');
        counterDiv.style.cssText = 'text-align: right; color: #999; font-size: 0.8rem; margin-top: 5px;';
        descriptionTextarea.parentNode.appendChild(counterDiv);
        
        function updateCounter() {
            const currentLength = descriptionTextarea.value.length;
            const remaining = maxLength - currentLength;
            counterDiv.textContent = `${currentLength}/${maxLength}`;
            
            if (remaining < 100) {
                counterDiv.style.color = '#f59e0b';
            } else if (remaining < 50) {
                counterDiv.style.color = '#ef4444';
            } else {
                counterDiv.style.color = '#999';
            }
        }
        
        descriptionTextarea.addEventListener('input', updateCounter);
        updateCounter(); // Initial update
    }
    
    // Title field character counter
    const titleInput = document.getElementById('error_title');
    if (titleInput) {
        const maxLength = parseInt(titleInput.getAttribute('maxlength')) || 200;
        
        const counterDiv = document.createElement('div');
        counterDiv.style.cssText = 'text-align: right; color: #999; font-size: 0.8rem; margin-top: 5px;';
        titleInput.parentNode.appendChild(counterDiv);
        
        function updateTitleCounter() {
            const currentLength = titleInput.value.length;
            counterDiv.textContent = `${currentLength}/${maxLength}`;
            
            if (currentLength > maxLength * 0.9) {
                counterDiv.style.color = '#f59e0b';
            } else {
                counterDiv.style.color = '#999';
            }
        }
        
        titleInput.addEventListener('input', updateTitleCounter);
        updateTitleCounter();
    }
    
    // Form field validation styling
    const requiredFields = errorReportForm.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (this.value.trim()) {
                this.style.borderColor = '#22c55e';
            } else {
                this.style.borderColor = '#ef4444';
            }
        });
        
        field.addEventListener('input', function() {
            if (this.style.borderColor === 'rgb(239, 68, 68)' && this.value.trim()) {
                this.style.borderColor = 'rgba(255,255,255,0.2)';
            }
        });
    });
    
    // Auto-populate browser and URL information if not already filled
    const browserInfoField = document.getElementById('browser_info');
    const errorUrlField = document.getElementById('error_url');
    
    if (browserInfoField && !browserInfoField.value) {
        browserInfoField.value = navigator.userAgent;
    }
    
    if (errorUrlField && !errorUrlField.value) {
        errorUrlField.value = window.location.href;
    }
}

// -------------------------------
// COMPLETE BILINGUAL FUNCTIONS FOR BASE.JS
// -------------------------------

// Helper function for language detection and messages
function getLanguageAndMessages() {
  const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
  const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
  const isEnglish = currentLang === 'en';
  
  return {
      lang: currentLang,
      isEnglish: isEnglish,
      messages: {
          en: {
              // General messages
              success: 'Success!',
              error: 'Error occurred',
              loading: 'Loading...',
              saving: 'Saving...',
              deleting: 'Deleting...',
              processing: 'Processing...',
              confirm: 'Are you sure?',
              cancel: 'Cancel',
              ok: 'OK',
              
              // Verification
              verificationSent: 'Verification email sent! Check your email.',
              verificationError: 'An error occurred. Please try again later.',
              
              // Data download
              downloadConfirm: 'Are you sure you want to download all your data?',
              downloadPreparing: 'Preparing...',
              downloadSuccess: 'Data preparation completed! Download link has been sent to your email.',
              downloadError: 'Error: ',
              downloadConnectionError: 'Connection error occurred',
              
              // Account deletion
              deleteAccountConfirm: 'FINAL WARNING: This action cannot be undone. Do you really want to delete your account?',
              deleteAccountDeleting: 'Deleting...',
              deleteAccountSuccess: 'Your account has been successfully deleted. Redirecting to homepage.',
              deleteAccountError: 'Error: ',
              
              // Chat history
              clearHistoryConfirm: 'Are you sure you want to clear all chat history? This action cannot be undone.',
              deleteChatConfirm: 'Are you sure you want to delete this chat?',
              clearingHistory: 'Clearing history...',
              deletingChat: 'Deleting...',
              historyCleared: 'Chat history cleared successfully!',
              chatDeleted: 'Chat deleted successfully!',
              
              // Privacy settings
              acceptAllConfirm: 'Accept all privacy settings? This will enable all data processing consents.',
              rejectAllConfirm: 'Reject all optional privacy settings? Essential services may be affected.',
              acceptingAll: 'Accepting all...',
              rejectingAll: 'Rejecting all...',
              settingsSaved: 'Settings saved successfully!',
              
              // Profile settings
              profileSaving: 'Saving...',
              profileSaved: 'Profile updated successfully!',
              profileError: 'Error updating profile: ',
              invalidName: 'Name must be at least 2 characters long',
              invalidPhone: 'Please enter a valid phone number',
              namePattern: 'Name can only contain letters, spaces, and hyphens',
              phonePattern: 'Phone number format: +country area number',
              
              // Error reporting
              selectPriority: 'Please select priority level',
              reportSubmitting: 'Submitting...',
              reportSubmitted: 'Error report submitted successfully! Tracking ID: ',
              reportError: 'Error: ',
              reportConnectionError: 'An error occurred during submission',
              fileTooLarge: 'File size cannot exceed 5MB',
              fileSelected: 'File Selected',
              
              // Password change
              passwordsNoMatch: 'Passwords do not match!',
              passwordWeak: 'Password is too weak. Please choose a stronger password.',
              passwordChanging: 'Changing...',
              passwordStrength: {
                  0: { text: 'Very Weak', color: '#ef4444' },
                  1: { text: 'Weak', color: '#f59e0b' },
                  2: { text: 'Fair', color: '#f59e0b' },
                  3: { text: 'Good', color: '#22c55e' },
                  4: { text: 'Strong', color: '#22c55e' },
                  5: { text: 'Very Strong', color: '#22c55e' }
              },
              passwordMatch: 'Passwords match',
              passwordNoMatch: 'Passwords do not match'
          },
          tr: {
              // General messages
              success: 'Başarılı!',
              error: 'Hata oluştu',
              loading: 'Yükleniyor...',
              saving: 'Kaydediliyor...',
              deleting: 'Siliniyor...',
              processing: 'İşleniyor...',
              confirm: 'Emin misiniz?',
              cancel: 'İptal',
              ok: 'Tamam',
              
              // Verification
              verificationSent: 'Doğrulama maili gönderildi! Email adresinizi kontrol edin.',
              verificationError: 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.',
              
              // Data download
              downloadConfirm: 'Tüm verilerinizi indirmek istediğinizden emin misiniz?',
              downloadPreparing: 'Hazırlanıyor...',
              downloadSuccess: 'Veri hazırlama tamamlandı! İndirme linki email adresinize gönderildi.',
              downloadError: 'Hata: ',
              downloadConnectionError: 'Bağlantı hatası oluştu',
              
              // Account deletion
              deleteAccountConfirm: 'SON UYARI: Bu işlem geri alınamaz. Hesabınızı gerçekten silmek istiyor musunuz?',
              deleteAccountDeleting: 'Siliniyor...',
              deleteAccountSuccess: 'Hesabınız başarıyla silindi. Ana sayfaya yönlendiriliyorsunuz.',
              deleteAccountError: 'Hata: ',
              
              // Chat history
              clearHistoryConfirm: 'Tüm sohbet geçmişini silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.',
              deleteChatConfirm: 'Bu sohbeti silmek istediğinizden emin misiniz?',
              clearingHistory: 'Geçmiş temizleniyor...',
              deletingChat: 'Siliniyor...',
              historyCleared: 'Sohbet geçmişi başarıyla temizlendi!',
              chatDeleted: 'Sohbet başarıyla silindi!',
              
              // Privacy settings
              acceptAllConfirm: 'Tüm gizlilik ayarlarını kabul et? Bu tüm veri işleme onaylarını etkinleştirecek.',
              rejectAllConfirm: 'Tüm isteğe bağlı gizlilik ayarlarını reddet? Temel hizmetler etkilenebilir.',
              acceptingAll: 'Tümü kabul ediliyor...',
              rejectingAll: 'Tümü reddediliyor...',
              settingsSaved: 'Ayarlar başarıyla kaydedildi!',
              
              // Profile settings
              profileSaving: 'Kaydediliyor...',
              profileSaved: 'Profil başarıyla güncellendi!',
              profileError: 'Profil güncelleme hatası: ',
              invalidName: 'İsim en az 2 karakter olmalıdır',
              invalidPhone: 'Lütfen geçerli bir telefon numarası girin',
              namePattern: 'İsim sadece harf, boşluk ve tire içerebilir',
              phonePattern: 'Telefon numarası formatı: +ülke alan numara',
              
              // Error reporting
              selectPriority: 'Lütfen öncelik seviyesini seçin',
              reportSubmitting: 'Gönderiliyor...',
              reportSubmitted: 'Hata raporu başarıyla gönderildi! Takip numarası: ',
              reportError: 'Hata: ',
              reportConnectionError: 'Gönderim sırasında hata oluştu',
              fileTooLarge: 'Dosya boyutu 5MB\'dan büyük olamaz',
              fileSelected: 'Dosya Seçildi',
              
              // Password change
              passwordsNoMatch: 'Şifreler eşleşmiyor!',
              passwordWeak: 'Şifre çok zayıf. Lütfen daha güçlü bir şifre seçin.',
              passwordChanging: 'Değiştiriliyor...',
              passwordStrength: {
                  0: { text: 'Çok Zayıf', color: '#ef4444' },
                  1: { text: 'Zayıf', color: '#f59e0b' },
                  2: { text: 'Orta', color: '#f59e0b' },
                  3: { text: 'İyi', color: '#22c55e' },
                  4: { text: 'Güçlü', color: '#22c55e' },
                  5: { text: 'Çok Güçlü', color: '#22c55e' }
              },
              passwordMatch: 'Şifreler eşleşiyor',
              passwordNoMatch: 'Şifreler eşleşmiyor'
          }
      }
  };
}

// Updated resendVerification function with full language support
function resendVerification() {
  const { isEnglish, messages } = getLanguageAndMessages();
  const msg = isEnglish ? messages.en : messages.tr;
  
  const userEmailMeta = document.querySelector('meta[name="user-email"]');
  const userEmail = userEmailMeta ? userEmailMeta.content : null;
  
  if (!userEmail) {
      alert(isEnglish ? 'User email not found' : 'Kullanıcı email bulunamadı');
      return;
  }
  
  fetch('/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'email=' + encodeURIComponent(userEmail)
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          alert(msg.verificationSent);
      } else {
          alert(msg.verificationError);
      }
  })
  .catch(error => {
      console.error('Error:', error);
      alert(msg.verificationError);
  });
}

// Updated requestDataDownload function
function requestDataDownload() {
  const { isEnglish, messages } = getLanguageAndMessages();
  const msg = isEnglish ? messages.en : messages.tr;
  
  const btn = document.getElementById('downloadBtn');
  const progressBar = document.getElementById('progressBar');
  const progressFill = document.getElementById('progressFill');
  const statusMessage = document.getElementById('statusMessage');
  
  if (!btn) return;
  
  if (!confirm(msg.downloadConfirm)) return;
  
  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = msg.downloadPreparing;
  
  if (progressBar) progressBar.style.display = 'block';
  if (statusMessage) {
      statusMessage.style.display = 'block';
      statusMessage.textContent = isEnglish ? 'Starting data collection process...' : 'Veri toplama işlemi başlatılıyor...';
  }
  
  let progress = 0;
  const progressInterval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress > 90) progress = 90;
      if (progressFill) progressFill.style.width = progress + '%';
  }, 500);
  
  fetch('/api/request-data-download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
          format: 'json',
          include_ai_data: true,
          include_logs: true
      })
  })
  .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
  })
  .then(data => {
      clearInterval(progressInterval);
      if (progressFill) progressFill.style.width = '100%';
      
      if (data.success) {
          if (statusMessage) {
              statusMessage.innerHTML = msg.downloadSuccess + '<br><small>' + 
                  (isEnglish ? 'Request ID: ' : 'Talep ID: ') + data.request_id + '</small>';
          }
          btn.textContent = isEnglish ? '✅ Completed' : '✅ Tamamlandı';
          
          setTimeout(() => {
              const dashboardUrl = document.querySelector('a[href*="dashboard"]')?.href || '/dashboard';
              window.location.href = dashboardUrl;
          }, 3000);
      } else {
          throw new Error(data.error || 'Unknown error');
      }
  })
  .catch(error => {
      clearInterval(progressInterval);
      if (statusMessage) statusMessage.textContent = msg.downloadConnectionError;
      resetButton();
  });
  
  function resetButton() {
      btn.disabled = false;
      btn.textContent = isEnglish ? '📥 Try Again' : '📥 Tekrar Dene';
      setTimeout(() => {
          if (btn && !btn.disabled) btn.textContent = originalText;
      }, 5000);
  }
  
  setTimeout(() => {
      if (btn && btn.disabled) resetButton();
  }, 60000);
}

// Updated deleteAccount function
function deleteAccount() {
  const { isEnglish, messages } = getLanguageAndMessages();
  const msg = isEnglish ? messages.en : messages.tr;
  
  const btn = document.getElementById('deleteBtn');
  if (!btn || btn.disabled) return;
  
  const confirmationText = isEnglish ? 'DELETE MY ACCOUNT' : 'HESABIMI SIL';
  
  if (!confirm(msg.deleteAccountConfirm)) return;
  
  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = msg.deleteAccountDeleting;
  btn.style.background = 'linear-gradient(135deg, #6b7280, #4b5563)';
  
  fetch('/api/delete-account', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
          confirmation: confirmationText,
          final_confirmation: true
      })
  })
  .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
  })
  .then(data => {
      if (data.success) {
          alert(msg.deleteAccountSuccess);
          const redirectUrl = isEnglish ? '/en' : '/';
          setTimeout(() => window.location.href = redirectUrl, 1000);
      } else {
          throw new Error(data.error || 'Unknown error');
      }
  })
  .catch(error => {
      console.error('Delete account error:', error);
      alert(msg.deleteAccountError + error.message);
      resetDeleteButton();
  });
  
  function resetDeleteButton() {
      if (btn) {
          btn.disabled = false;
          btn.textContent = originalText;
          btn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
      }
  }
  
  setTimeout(() => {
      if (btn && btn.disabled && btn.textContent === msg.deleteAccountDeleting) {
          resetDeleteButton();
      }
  }, 60000);
}

// Updated clearHistory function
function clearHistory() {
  const { isEnglish, messages } = getLanguageAndMessages();
  const msg = isEnglish ? messages.en : messages.tr;
  
  if (!confirm(msg.clearHistoryConfirm)) return;
  
  const clearBtn = document.getElementById('clearHistoryBtn');
  if (clearBtn) {
      clearBtn.disabled = true;
      clearBtn.textContent = '⏳ ' + msg.clearingHistory;
  }
  
  fetch('/api/clear-chat-history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          alert(msg.historyCleared);
          location.reload();
      } else {
          throw new Error(data.error || 'Unknown error');
      }
  })
  .catch(error => {
      console.error('Error:', error);
      alert(msg.error);
      if (clearBtn) {
          clearBtn.disabled = false;
          clearBtn.textContent = isEnglish ? '🗑️ Clear All' : '🗑️ Tümünü Temizle';
      }
  });
}

// Updated deleteChat function
function deleteChat(chatId) {
  if (!chatId) return;
  
  const { isEnglish, messages } = getLanguageAndMessages();
  const msg = isEnglish ? messages.en : messages.tr;
  
  if (!confirm(msg.deleteChatConfirm)) return;
  
  const deleteBtn = document.querySelector(`[data-chat-id="${chatId}"]`);
  if (deleteBtn) {
      deleteBtn.disabled = true;
      deleteBtn.textContent = '⏳ ' + msg.deletingChat;
  }
  
  fetch(`/api/delete-chat/${chatId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          const chatItem = document.querySelector(`[data-chat-id="${chatId}"]`).closest('.chat-item');
          if (chatItem) {
              chatItem.style.animation = 'slideOutRight 0.3s ease-in forwards';
              setTimeout(() => chatItem.remove(), 300);
          }
          
          const tempMessage = document.createElement('div');
          tempMessage.style.cssText = `
              position: fixed; top: 20px; right: 20px; z-index: 1000;
              background: rgba(34, 197, 94, 0.9); color: white; padding: 15px 20px;
              border-radius: 8px; font-weight: 600;
          `;
          tempMessage.textContent = msg.chatDeleted;
          document.body.appendChild(tempMessage);
          setTimeout(() => tempMessage.remove(), 3000);
      } else {
          throw new Error(data.error || 'Unknown error');
      }
  })
  .catch(error => {
      console.error('Error:', error);
      alert(msg.error);
      if (deleteBtn) {
          deleteBtn.disabled = false;
          deleteBtn.textContent = isEnglish ? '🗑️ Delete' : '🗑️ Sil';
      }
  });
}

// Updated acceptAll function
function acceptAll() {
  const { isEnglish, messages } = getLanguageAndMessages();
  const msg = isEnglish ? messages.en : messages.tr;
  
  if (!confirm(msg.acceptAllConfirm)) return;
  
  const acceptBtn = document.querySelector('.accept-all-btn');
  if (acceptBtn) {
      acceptBtn.disabled = true;
      const originalText = acceptBtn.textContent;
      acceptBtn.textContent = '⏳ ' + msg.acceptingAll;
  }
  
  const checkboxes = document.querySelectorAll('#privacySettingsForm input[type="checkbox"]');
  checkboxes.forEach(checkbox => {
      checkbox.checked = true;
      checkbox.dispatchEvent(new Event('change'));
  });
  
  const retentionSelect = document.getElementById('ai_data_retention_days');
  if (retentionSelect) {
      retentionSelect.value = '365';
      retentionSelect.dispatchEvent(new Event('change'));
  }
  
  setTimeout(() => {
      const form = document.getElementById('privacySettingsForm');
      if (form) form.submit();
  }, 500);
}

// Updated rejectAll function
function rejectAll() {
  const { isEnglish, messages } = getLanguageAndMessages();
  const msg = isEnglish ? messages.en : messages.tr;
  
  if (!confirm(msg.rejectAllConfirm)) return;
  
  const rejectBtn = document.querySelector('.reject-all-btn');
  if (rejectBtn) {
      rejectBtn.disabled = true;
      const originalText = rejectBtn.textContent;
      rejectBtn.textContent = '⏳ ' + msg.rejectingAll;
  }
  
  const marketingConsent = document.getElementById('marketing_consent');
  const aiDataConsent = document.getElementById('ai_data_consent');
  
  if (marketingConsent) {
      marketingConsent.checked = false;
      marketingConsent.dispatchEvent(new Event('change'));
  }
  
  if (aiDataConsent) {
      aiDataConsent.checked = false;
      aiDataConsent.dispatchEvent(new Event('change'));
  }
  
  const retentionSelect = document.getElementById('ai_data_retention_days');
  if (retentionSelect) {
      retentionSelect.value = '30';
      retentionSelect.dispatchEvent(new Event('change'));
  }
  
  setTimeout(() => {
      const form = document.getElementById('privacySettingsForm');
      if (form) form.submit();
  }, 500);
}

// Make all functions globally available
window.resendVerification = resendVerification;
window.requestDataDownload = requestDataDownload;
window.deleteAccount = deleteAccount;
window.clearHistory = clearHistory;
window.deleteChat = deleteChat;
window.acceptAll = acceptAll;
window.rejectAll = rejectAll;



document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const submitButton = document.getElementById('submitButton');
    const requiredCheckboxes = document.querySelectorAll('input[type="checkbox"][required]');
    
    // Sadece password input'u varsa çalıştır
    if (passwordInput) {
        // Password strength validation
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            const checks = {
                length: password.length >= 8,
                uppercase: /[A-Z]/.test(password),
                lowercase: /[a-z]/.test(password),
                number: /\d/.test(password),
                special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
            };
            
            Object.keys(checks).forEach(check => {
                const element = document.getElementById(check);
                if (element && checks[check]) {
                    element.classList.add('valid');
                    element.textContent = element.textContent.replace('✗', '✓');
                } else if (element) {
                    element.classList.remove('valid');
                    element.textContent = element.textContent.replace('✓', '✗');
                }
            });
            
            if (typeof checkFormValidity === 'function') {
                checkFormValidity();
            }
        });
    }
    
    // Diğer kodlar için de benzer kontroller ekleyin
});
    
document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    const submitButton = document.getElementById('submitButton');
    const requiredCheckboxes = document.querySelectorAll('input[type="checkbox"][required]');
    
    // Sadece password elementleri varsa çalıştır
    if (passwordInput && confirmPasswordInput && submitButton) {
        
        // Password strength validation
        passwordInput.addEventListener('input', function() {
            // mevcut kod
            checkFormValidity();
        });

        // Password confirmation
        confirmPasswordInput.addEventListener('input', function() {
            const password = passwordInput.value;
            const confirmPassword = this.value;
            const matchDiv = document.getElementById('passwordMatch');
            
            if (matchDiv) { // null kontrolü ekle
                if (confirmPassword) {
                    if (password === confirmPassword) {
                        matchDiv.textContent = '✓ Passwords match';
                        matchDiv.style.color = '#51cf66';
                    } else {
                        matchDiv.textContent = '✗ Passwords do not match';
                        matchDiv.style.color = '#ff6b6b';
                    }
                } else {
                    matchDiv.textContent = '';
                }
            }
            
            checkFormValidity();
        });
        
        // Required checkboxes
        requiredCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', checkFormValidity);
        });
        
        function checkFormValidity() {
            const password = passwordInput.value;
            const confirmPassword = confirmPasswordInput.value;
            const passwordsMatch = password === confirmPassword && password.length > 0;
            const passwordStrong = password.length >= 8 && /[A-Z]/.test(password) && 
                                  /[a-z]/.test(password) && /\d/.test(password) && 
                                  /[!@#$%^&*(),.?":{}|<>]/.test(password);
            const requiredChecked = Array.from(requiredCheckboxes).every(cb => cb.checked);
            
            submitButton.disabled = !(passwordsMatch && passwordStrong && requiredChecked);
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin user detail page loaded');
    
    // CSRF token'ı al
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    console.log('CSRF Token:', csrfToken ? 'Found' : 'Missing');
    
    // Tüm admin form'larına CSRF token ekle
    document.querySelectorAll('form').forEach(form => {
        if (!form.querySelector('input[name="csrf_token"]') && csrfToken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
            console.log('CSRF token added to form:', form.action);
        }
    });
    
    // Form submission'ları logla
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            console.log('Form submitting:', this.action);
            console.log('Form data:', new FormData(this));
            
            // Confirmation kontrol et
            const confirmMsg = this.dataset.confirm;
            if (confirmMsg && !confirm(confirmMsg)) {
                e.preventDefault();
                console.log('User cancelled form submission');
                return false;
            }
            
            // Loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.textContent;
                submitBtn.textContent = 'İşleniyor...';
                
                // Reset after 30 seconds
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }, 30000);
            }
        });
    });
    
    // Tab functionality
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            console.log('Tab clicked:', tabName);
            
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(content => {
                content.style.display = 'none';
            });
            
            // Show selected tab
            const targetTab = document.getElementById(tabName + '-tab');
            if (targetTab) {
                targetTab.style.display = 'block';
            }
            
            // Update button styles
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.style.color = '#9ca3af';
                b.style.borderBottomColor = 'transparent';
                b.classList.remove('active');
            });
            
            this.style.color = 'white';
            this.style.borderBottomColor = '#667eea';
            this.classList.add('active');
        });
    });
    
    // Test admin routes
    console.log('Testing admin route accessibility...');
    fetch('/admin-test', { 
        method: 'GET',
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('Admin test response:', response.status);
        if (response.ok) {
            console.log('✅ Admin routes accessible');
        } else {
            console.log('❌ Admin routes not accessible:', response.status);
        }
    })
    .catch(error => {
        console.log('❌ Admin route test failed:', error);
    });
});

// Global notification function
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 10000;
        background: ${type === 'success' ? '#22c55e' : '#ef4444'};
        color: white; padding: 15px 20px; border-radius: 8px;
        font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideInRight 0.3s ease-out;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-in forwards';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// base.js'nin DOMContentLoaded event listener'ına EKLEYİN

// =============================================================================
// ADMIN FORM HANDLING (tüm admin sayfaları için)
// =============================================================================

// Admin sayfasında mıyız kontrol et
const isAdminPage = window.location.pathname.includes('/admin/');

if (isAdminPage) {
    console.log('Admin page detected - enabling admin functionality');
    
    // CSRF token'ı al
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    console.log('CSRF Token:', csrfToken ? 'Found' : 'Missing');
    
    // Tüm admin form'larına CSRF token ekle
    document.querySelectorAll('form').forEach(form => {
        if (!form.querySelector('input[name="csrf_token"]') && csrfToken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
            console.log('CSRF token added to form:', form.action);
        }
    });
    
    // Admin form submission handling
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            console.log('Admin form submitting:', this.action);
            
            // Confirmation kontrol et
            const confirmMsg = this.dataset.confirm;
            if (confirmMsg && !confirm(confirmMsg)) {
                e.preventDefault();
                console.log('User cancelled form submission');
                return false;
            }
            
            // Loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.textContent;
                
                // Türkçe loading mesajları
                let loadingText = 'İşleniyor...';
                if (originalText.includes('Approve') || originalText.includes('Onayla')) {
                    loadingText = 'Onaylanıyor...';
                } else if (originalText.includes('Activate') || originalText.includes('Aktif')) {
                    loadingText = 'Aktifleştiriliyor...';
                } else if (originalText.includes('Deactivate') || originalText.includes('Pasif')) {
                    loadingText = 'Pasifleştiriliyor...';
                } else if (originalText.includes('Delete') || originalText.includes('Sil')) {
                    loadingText = 'Siliniyor...';
                }
                
                submitBtn.textContent = loadingText;
                
                // Reset after 30 seconds
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }, 30000);
            }
        });
    });
    
    // Admin routes connectivity test
    console.log('Testing admin route accessibility...');
    fetch('/admin/test-routes', { 
        method: 'GET',
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('Admin test response:', response.status);
        if (response.ok) {
            console.log('✅ Admin routes accessible');
        } else {
            console.log('❌ Admin routes not accessible:', response.status);
        }
    })
    .catch(error => {
        console.log('❌ Admin route test failed:', error);
    });
}

// Delete user function (admin functionality)
function deleteUser(userId) {
    const langMeta = document.querySelector('meta[name="language"]') || document.querySelector('html[lang]');
    const currentLang = langMeta ? (langMeta.content || langMeta.lang || 'tr') : 'tr';
    const isEnglish = currentLang === 'en';
    
    const confirmMessage = isEnglish 
        ? 'Are you sure you want to delete this user? This action cannot be undone!'
        : 'Bu kullanıcıyı silmek istediğinizden emin misiniz? Bu işlem geri alınamaz!';
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    const deleteBtn = document.querySelector(`form[action*="delete"] button[type="submit"]`);
    if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.textContent = isEnglish ? 'Deleting...' : 'Siliniyor...';
    }
    
    // CSRF token al
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    
    fetch(`/tr/admin/user/${userId}/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `csrf_token=${encodeURIComponent(csrfToken)}`
    })
    .then(response => {
        if (response.ok) {
            const successMsg = isEnglish ? 'User deleted successfully!' : 'Kullanıcı başarıyla silindi!';
            alert(successMsg);
            window.location.href = '/admin/users';
        } else {
            throw new Error('Delete failed');
        }
    })
    .catch(error => {
        console.error('Delete error:', error);
        const errorMsg = isEnglish ? 'Error deleting user' : 'Kullanıcı silme hatası';
        alert(errorMsg);
        
        if (deleteBtn) {
            deleteBtn.disabled = false;
            deleteBtn.textContent = isEnglish ? '🗑️ Delete User' : '🗑️ Kullanıcıyı Sil';
        }
    });
}

// Global olarak erişilebilir yap
window.deleteUser = deleteUser;


function confirmDelete(userId, userEmail) {
    if (confirm(`${userEmail} kullanıcısını kalıcı olarak silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!`)) {
        // Form oluştur ve gönder
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/delete-user-permanent/${userId}`;
        
        // CSRF token ekle
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
        
        document.body.appendChild(form);
        form.submit();
    }
}

// Toplu silme için
function bulkDelete() {
    const checkboxes = document.querySelectorAll('input[name="user_ids[]"]:checked');
    
    if (checkboxes.length === 0) {
        alert('Lütfen silinecek kullanıcıları seçin.');
        return;
    }
    
    if (confirm(`${checkboxes.length} kullanıcıyı kalıcı olarak silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!`)) {
        document.getElementById('bulk-delete-form').submit();
    }
}


fetch('/api/ask-ai-with-code', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        question: "Python'da yapay zeka kütüphaneleri araştır",
        model: "auto",
        enable_research: true
    })
})
.then(response => response.json())
.then(data => {
    console.log('AI Response:', data.choices[0].message.content);
    if (data.research_performed) {
        console.log('Research Info:', data.research_info);
    }
});


fetch('/api/research/search', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        query: "Python machine learning libraries",
        max_results: 5
    })
})
.then(response => response.json())
.then(data => {
    console.log('Search Response:', data);
    if (data.success) {
        console.log(`Found ${data.total_results} results using ${data.engine}`);
        console.log('Fallback used:', data.fallback_used);
        data.results.forEach((result, index) => {
            console.log(`${index + 1}. ${result.title}`);
            console.log(`   URL: ${result.url}`);
            console.log(`   Snippet: ${result.snippet.substring(0, 100)}...`);
        });
    } else {
        console.log('Search failed:', data.error);
    }
});


fetch('/api/research/analyze', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        url: "https://python.org"
    })
})
.then(response => response.json())
.then(data => {
    console.log('Page Analysis:', data.content_summary);
});


const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

// Include in requests
function makeRequest(data) {
    fetch('/api/some-endpoint', {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify(data)
    });
}

// base.js içinde - Şifre eşleşme kontrolü (her iki dil için)

// Sayfa yüklendiğinde çalıştır
document.addEventListener('DOMContentLoaded', function() {
    // Reset password formunu bul
    const resetPasswordForm = document.querySelector('form[action*="reset-password"]');
    
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password');
            const confirmPassword = document.getElementById('confirm_password');
            
            if (!password || !confirmPassword) return; // Elementler yoksa çık
            
            if (password.value !== confirmPassword.value) {
                e.preventDefault();
                
                // Dil kontrolü - sayfa dilini algıla
                const lang = document.documentElement.lang || 'tr';
                const message = lang === 'en' 
                    ? 'Passwords do not match!' 
                    : 'Şifreler eşleşmiyor!';
                
                alert(message);
                
                // Confirm password alanını vurgula
                confirmPassword.focus();
                confirmPassword.classList.add('error');
            }
        });
        
        // Gerçek zamanlı şifre eşleşme göstergesi (opsiyonel)
        const confirmPassword = document.getElementById('confirm_password');
        if (confirmPassword) {
            confirmPassword.addEventListener('input', function() {
                const password = document.getElementById('password');
                if (password && this.value) {
                    if (this.value === password.value) {
                        this.style.borderColor = '#4ade80'; // Yeşil
                    } else {
                        this.style.borderColor = '#f87171'; // Kırmızı
                    }
                } else {
                    this.style.borderColor = ''; // Varsayılan
                }
            });
        }
    }
});

// Bot koruması - sadece register sayfasında çalışır
(function() {
    const form = document.getElementById('registerForm');
    
    // Form yoksa bu kodu çalıştırma
    if (!form) {
        return;
    }
    
    const submitButton = document.getElementById('submitButton');
    
    if (!submitButton) {
        console.warn('Register submit button not found');
        return;
    }
    
    let formStartTime = Date.now();
    let mouseMovements = 0;
    let keyPresses = 0;
    
    // Mouse hareketi kontrolü
    document.addEventListener('mousemove', function() {
        mouseMovements++;
    });
    
    // Klavye kontrolü
    form.addEventListener('keyup', function() {
        keyPresses++;
    });
    
    // Form validation - checkbox kontrolü
    const requiredCheckboxes = ['privacy_accepted', 'terms_accepted'];
    const allInputs = form.querySelectorAll('input[required]');
    
    function validateForm() {
        let allValid = true;
        
        // Text input kontrolü
        allInputs.forEach(input => {
            if (input.type !== 'checkbox' && !input.value.trim()) {
                allValid = false;
            }
        });
        
        // Checkbox kontrolü
        requiredCheckboxes.forEach(id => {
            const checkbox = document.getElementById(id);
            if (checkbox && !checkbox.checked) {
                allValid = false;
            }
        });
        
        // Şifre eşleşme kontrolü
        const password = document.getElementById('password');
        const confirmPassword = document.getElementById('confirm_password');
        if (password && confirmPassword && password.value !== confirmPassword.value) {
            allValid = false;
        }
        
        submitButton.disabled = !allValid;
    }
    
    // Form değişikliklerini dinle
    form.addEventListener('input', validateForm);
    form.addEventListener('change', validateForm);
    
    // Şifre güçlülüğü kontrolü
    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            
            // Length check
            const lengthCheck = document.getElementById('length');
            if (lengthCheck) {
                if (password.length >= 8) {
                    lengthCheck.classList.add('valid');
                    lengthCheck.textContent = '✓ En az 8 karakter';
                } else {
                    lengthCheck.classList.remove('valid');
                    lengthCheck.textContent = '✗ En az 8 karakter';
                }
            }
            
            // Uppercase check
            const uppercaseCheck = document.getElementById('uppercase');
            if (uppercaseCheck) {
                if (/[A-Z]/.test(password)) {
                    uppercaseCheck.classList.add('valid');
                    uppercaseCheck.textContent = '✓ En az 1 büyük harf';
                } else {
                    uppercaseCheck.classList.remove('valid');
                    uppercaseCheck.textContent = '✗ En az 1 büyük harf';
                }
            }
            
            // Lowercase check
            const lowercaseCheck = document.getElementById('lowercase');
            if (lowercaseCheck) {
                if (/[a-z]/.test(password)) {
                    lowercaseCheck.classList.add('valid');
                    lowercaseCheck.textContent = '✓ En az 1 küçük harf';
                } else {
                    lowercaseCheck.classList.remove('valid');
                    lowercaseCheck.textContent = '✗ En az 1 küçük harf';
                }
            }
            
            // Number check
            const numberCheck = document.getElementById('number');
            if (numberCheck) {
                if (/\d/.test(password)) {
                    numberCheck.classList.add('valid');
                    numberCheck.textContent = '✓ En az 1 rakam';
                } else {
                    numberCheck.classList.remove('valid');
                    numberCheck.textContent = '✗ En az 1 rakam';
                }
            }
            
            // Special character check
            const specialCheck = document.getElementById('special');
            if (specialCheck) {
                if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
                    specialCheck.classList.add('valid');
                    specialCheck.textContent = '✓ En az 1 özel karakter';
                } else {
                    specialCheck.classList.remove('valid');
                    specialCheck.textContent = '✗ En az 1 özel karakter';
                }
            }
            
            validateForm();
        });
    }
    
    // Şifre eşleşme kontrolü
    const confirmPassword = document.getElementById('confirm_password');
    if (confirmPassword) {
        confirmPassword.addEventListener('input', function() {
            const password = document.getElementById('password').value;
            const matchDiv = document.getElementById('passwordMatch');
            
            if (matchDiv) {
                if (this.value === '') {
                    matchDiv.textContent = '';
                } else if (this.value === password) {
                    matchDiv.textContent = '✓ Şifreler eşleşiyor';
                    matchDiv.style.color = '#51cf66';
                } else {
                    matchDiv.textContent = '✗ Şifreler eşleşmiyor';
                    matchDiv.style.color = '#ff6b6b';
                }
            }
            
            validateForm();
        });
    }
    
    // Form submit kontrolü - BOT KORUMALARI
    form.addEventListener('submit', function(e) {
        const elapsed = (Date.now() - formStartTime) / 1000;
        
        // 1. Çok hızlı gönderim kontrolü
        if (elapsed < 3) {
            e.preventDefault();
            alert('Lütfen formu daha dikkatli doldurun.');
            return false;
        }
        
        // 2. Mouse/klavye aktivitesi kontrolü
        if (mouseMovements === 0 && keyPresses === 0) {
            e.preventDefault();
            alert('Lütfen formu manuel olarak doldurun.');
            return false;
        }
        
        // 3. Honeypot kontrolü
        const honeypot = document.querySelector('input[name="website_url"]');
        if (honeypot && honeypot.value.trim() !== '') {
            e.preventDefault();
            console.warn('Bot detected - honeypot filled');
            return false;
        }
        
        return true;
    });
    
    // İlk validation
    validateForm();
})();

async function testExternalAPIs() {
    try {
        const response = await fetch('/api/external/status');
        const data = await response.json();
        
        console.log('External API Status:', data);
        
        // Only display if the div exists
        const statusDiv = document.getElementById('api-status');
        if (statusDiv) {
            displayAPIStatus(data);
        }
    } catch (error) {
        console.error('API status check failed:', error);
    }
}

// API durumunu göster
function displayAPIStatus(data) {
    const statusDiv = document.getElementById('api-status');
    if (!statusDiv) return;
    
    let html = '<h4>External API Services:</h4><ul>';
    
    for (const [service, status] of Object.entries(data)) {
        if (service === 'cache_size' || service === 'timestamp') continue;
        
        if (typeof status === 'object' && status.configured !== undefined) {
            const icon = status.configured ? '✅' : '❌';
            html += `<li>${icon} ${service.replace('_api', '')}: ${status.status}</li>`;
        }
    }
    
    html += '</ul>';
    statusDiv.innerHTML = html;
}

// Sayfa yüklendiğinde test et (sadece console'da)
document.addEventListener('DOMContentLoaded', () => {
    // Quietly check API status in background
    testExternalAPIs();
});



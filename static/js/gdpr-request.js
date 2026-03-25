// static/js/gdpr-request.js
document.addEventListener('DOMContentLoaded', function() {
    // Request type selection
    document.querySelectorAll('.request-type').forEach(type => {
        type.addEventListener('click', function() {
            document.querySelectorAll('.request-type').forEach(t => t.classList.remove('selected'));
            this.classList.add('selected');
            document.getElementById('request_type').value = this.dataset.type;
        });
    });

    // Form submission
    const gdprForm = document.getElementById('gdprForm');
    if (gdprForm) {
        gdprForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const requestType = document.getElementById('request_type').value;
            if (!requestType) {
                alert('Please select a request type');
                return;
            }
            
            const submitBtn = document.querySelector('.submit-btn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';
            
            const formData = new FormData(this);
            
            fetch('/api/submit-gdpr-request', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`GDPR request submitted successfully! Reference: ${data.request_id}`);
                    window.location.href = '/privacy';
                } else {
                    alert('Error: ' + data.error);
                    submitBtn.disabled = false;
                    submitBtn.textContent = '📤 Submit Request';
                }
            })
            .catch(error => {
                alert('An error occurred during submission');
                submitBtn.disabled = false;
                submitBtn.textContent = '📤 Submit Request';
            });
        });
    }
});
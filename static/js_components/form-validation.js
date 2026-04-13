document.addEventListener('DOMContentLoaded', function () {
    var form = document.querySelector('form[action="/submit_contact_form"]');
    if (!form) return;

    var textarea = form.querySelector('textarea[name="message"]');
    var submitBtn = form.querySelector('button[type="submit"]');
    var maxLen = 2000;

    // Character counter
    if (textarea) {
        textarea.setAttribute('maxlength', maxLen);
        var counter = document.createElement('div');
        counter.className = 'char-count';
        counter.textContent = '0 / ' + maxLen;
        textarea.parentNode.insertBefore(counter, textarea.nextSibling);

        textarea.addEventListener('input', function () {
            var len = textarea.value.length;
            counter.textContent = len + ' / ' + maxLen;
            counter.classList.toggle('warning', len > maxLen * 0.8);
        });
    }

    // Inline validation on blur
    var emailField = form.querySelector('input[name="email"]');
    if (emailField) {
        emailField.addEventListener('blur', function () {
            if (emailField.value && !emailField.value.match(/^[^@]+@[^@]+\.[^@]+$/)) {
                emailField.style.borderColor = 'var(--error-color)';
                showInlineError(emailField, 'Please enter a valid email address');
            } else {
                emailField.style.borderColor = '';
                clearInlineError(emailField);
            }
        });
    }

    var nameFields = form.querySelectorAll('input[name="firstname"], input[name="lastname"]');
    nameFields.forEach(function (field) {
        field.addEventListener('blur', function () {
            if (field.value && field.value.trim().length < 2) {
                field.style.borderColor = 'var(--error-color)';
                showInlineError(field, 'Please enter at least 2 characters');
            } else {
                field.style.borderColor = '';
                clearInlineError(field);
            }
        });
    });

    function showInlineError(field, msg) {
        clearInlineError(field);
        var err = document.createElement('div');
        err.className = 'inline-error';
        err.textContent = msg;
        err.style.color = 'var(--error-color)';
        err.style.fontSize = 'var(--size-xs)';
        err.style.fontFamily = 'var(--font-family-body)';
        err.style.marginTop = '-12px';
        err.style.marginBottom = '8px';
        field.parentNode.insertBefore(err, field.nextSibling);
    }

    function clearInlineError(field) {
        var next = field.nextElementSibling;
        if (next && next.classList.contains('inline-error')) {
            next.remove();
        }
    }

    // Loading state on submit
    if (submitBtn) {
        form.addEventListener('submit', function () {
            submitBtn.classList.add('button-loading');
            submitBtn.querySelector('span').textContent = 'Sending...';
        });
    }
});

document.addEventListener('DOMContentLoaded', function () {
    var steps = document.querySelectorAll('.calc-step');
    var progressContainer = document.getElementById('calc-progress');
    var currentStep = 0;
    var totalSteps = 5;
    var answers = {};

    // Build progress dots
    for (var i = 0; i < totalSteps; i++) {
        var dot = document.createElement('div');
        dot.className = 'calc-progress-dot' + (i === 0 ? ' current' : '');
        progressContainer.appendChild(dot);
    }

    function updateProgress() {
        var dots = progressContainer.querySelectorAll('.calc-progress-dot');
        for (var i = 0; i < dots.length; i++) {
            dots[i].className = 'calc-progress-dot';
            if (i < currentStep) dots[i].className += ' filled';
            if (i === currentStep) dots[i].className += ' current';
        }
    }

    function showStep(index) {
        for (var i = 0; i < steps.length; i++) {
            steps[i].classList.remove('active');
            steps[i].style.display = 'none';
        }
        if (index === 'result') {
            var resultStep = document.querySelector('[data-step="result"]');
            resultStep.style.display = 'block';
            resultStep.classList.add('active');
            progressContainer.style.display = 'none';
        } else {
            steps[index].style.display = 'block';
            steps[index].classList.add('active');
            progressContainer.style.display = 'flex';
        }
    }

    function calculateResult() {
        var base = answers.base || 4000;
        var multiplier = 1.0;

        if (answers.sources) multiplier *= answers.sources;
        if (answers.users) multiplier *= answers.users;
        if (answers.timeline) multiplier *= answers.timeline;
        if (answers.support) multiplier *= answers.support;

        var low = Math.round(base * multiplier / 500) * 500;
        var high = Math.round(low * 1.5 / 500) * 500;

        var fmt = function (n) {
            return 'CHF ' + n.toLocaleString('de-CH');
        };

        document.getElementById('calc-result-range').textContent = fmt(low) + ' \u2013 ' + fmt(high);
    }

    // Option click handlers
    var options = document.querySelectorAll('.calc-option');
    options.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var key = btn.getAttribute('data-key');

            // Store answer
            if (btn.hasAttribute('data-base')) {
                answers.base = parseFloat(btn.getAttribute('data-base'));
            }
            if (btn.hasAttribute('data-mult')) {
                answers[key] = parseFloat(btn.getAttribute('data-mult'));
            }

            // Highlight selected
            var siblings = btn.parentElement.querySelectorAll('.calc-option');
            siblings.forEach(function (s) { s.classList.remove('selected'); });
            btn.classList.add('selected');

            // Advance after short delay
            setTimeout(function () {
                currentStep++;
                if (currentStep >= totalSteps) {
                    calculateResult();
                    showStep('result');
                } else {
                    updateProgress();
                    showStep(currentStep);
                }
            }, 200);
        });
    });

    // Expose back/reset globally
    window.calcBack = function () {
        if (currentStep > 0) {
            currentStep--;
            updateProgress();
            showStep(currentStep);
        }
    };

    window.calcReset = function () {
        currentStep = 0;
        answers = {};
        options.forEach(function (btn) { btn.classList.remove('selected'); });
        updateProgress();
        showStep(0);
        progressContainer.style.display = 'flex';
    };
});

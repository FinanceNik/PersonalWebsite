document.addEventListener("DOMContentLoaded", function () {
    var questions = document.querySelectorAll('.faq .question');

    questions.forEach(function (question) {
        question.setAttribute('tabindex', '0');
        question.setAttribute('role', 'button');
        question.setAttribute('aria-expanded', 'false');

        function toggle() {
            var answer = question.querySelector('.answer');
            if (!answer) return;

            var isOpen = answer.classList.contains('open');

            // Close all others
            questions.forEach(function (q) {
                var a = q.querySelector('.answer');
                if (a && a !== answer) {
                    a.classList.remove('open');
                    q.classList.remove('active');
                    q.setAttribute('aria-expanded', 'false');
                }
            });

            // Toggle current
            answer.classList.toggle('open');
            question.classList.toggle('active');
            question.setAttribute('aria-expanded', !isOpen);
        }

        question.addEventListener('click', toggle);
        question.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggle();
            }
        });
    });
});

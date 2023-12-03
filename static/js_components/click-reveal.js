// Wait for the DOM to be fully loaded
document.addEventListener("DOMContentLoaded", function() {
    // Get all the question elements
    var questions = document.querySelectorAll('.faq .question');

    // Add a click event listener to each question
    questions.forEach(function(question) {
        question.addEventListener('click', function() {
            // This toggles the display of the answer
            var answer = this.querySelector('.answer');
            if (answer.style.display === "block") {
                answer.style.display = "none";
            } else {
                answer.style.display = "block";
            }
        });
    });
});
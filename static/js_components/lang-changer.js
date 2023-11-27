function setElementInnerHTML(elementId, content) {
    var element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = content;
    } else {
        console.error(`Element with ID ${elementId} not found.`);
    }
}

function loadJSON(languageCode) {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                try {
                    var jsonData = JSON.parse(xhr.responseText);

                    document.getElementById('hero-title').innerHTML = jsonData.herotitle.content;
                    document.getElementById('hero-subtitle').innerHTML = jsonData.herosubtitle.content;
                    document.getElementById('hero-text').innerHTML = jsonData.herotext.content;

                    document.getElementById('pre-footer').innerHTML = jsonData.prefooter.content;
                    document.getElementById('contact-button').innerHTML = jsonData.contactbutton.content;

                    document.getElementById('expertise-header').innerHTML = jsonData.expertiseheader.content;

                    for (let i = 1; i <= 6; i++) {
                        setElementInnerHTML(`card-expertise-${i}-header`, jsonData[`cardexpertise${i}header`].content);
                        setElementInnerHTML(`card-expertise-${i}-text`, jsonData[`cardexpertise${i}text`].content);
                    }

                    document.getElementById('technology-header').innerHTML = jsonData.technologyheader.content;

                    for (let i = 1; i <= 9; i++) {
                        setElementInnerHTML(`card-technology-${i}-text`, jsonData[`cardtechnology${i}text`].content);
                    }

                    for (let i = 1; i <= 10; i++) {
                        setElementInnerHTML(`faq-question-${i}`, jsonData[`faqquestion${i}`].content);
                        setElementInnerHTML(`faq-answer-${i}`, jsonData[`faqanswer${i}`].content);
                    }

                    document.getElementById('copyright-footer').innerHTML = jsonData.copyrightfooter.content;

                    console.log(jsonData);
                } catch (error) {
                    console.error('Error parsing JSON:', error);
                }
            } else {
                console.error(`Error fetching JSON. Status: ${xhr.status}`);
            }
        }
    };

    var filename = languageCode + '.json';
    xhr.open('GET', '/static/' + filename, true);
    xhr.send();
}

// Call the function when the page is loaded
loadJSON();
document.addEventListener('DOMContentLoaded', () => {  
    const recordButton = document.getElementById('recordButton');  
    const audioPlayback = document.getElementById('audioPlayback');  
    const audioFileInput = document.getElementById('audioFile');  
    const fileAudioPlayback = document.getElementById('fileAudioPlayback');  
    const transcribeButton = document.getElementById('transcribe');  
    const generateSoapButton = document.getElementById('generateSoap');  
    const transcribeProcessingTime = document.getElementById('transcribeProcessingTime');  
    const soapProcessingTime = document.getElementById('soapProcessingTime');  
    const markdownSoap = document.getElementById('markdownSoap');  
    const transcriptionResult = document.getElementById('transcriptionResult');  
    const soapResult = document.getElementById('soapResult');  
    const soapMarkdownPreview = document.getElementById('soapMarkdownPreview');  
    const transcribeSpinner = document.getElementById('transcribeSpinner');  
    const soapSpinner = document.getElementById('soapSpinner');  
    const advancedModeCheckbox = document.getElementById('advancedMode');  
    const advancedOptions = document.querySelectorAll('.advanced-option');  
    const languageOption = document.querySelector('.language-option');  
    const selectLanguage = document.getElementById('select_language');  
    let audioBlob = null;  
    let mediaRecorder = null;  
    let isRecording = false;  
    let recognition = null;  
    let final_transcript = '';  
  
    // Populate language dropdown  
    for (let i = 0; i < langs.length; i++) {  
        selectLanguage.options[i] = new Option(langs[i][0], langs[i][1][0]);  
    }  
    selectLanguage.value = 'id-ID'; // Set default to 'Bahasa Indonesia'  
  
    const renderMarkdown = (textarea, preview) => {  
        preview.innerHTML = marked.parse(textarea.value);  
        textarea.style.display = 'none';  
        preview.style.display = 'block';  
    };  
  
    const hideMarkdown = (textarea, preview) => {  
        preview.style.display = 'none';  
        textarea.style.display = 'block';  
    };  
  
    markdownSoap.addEventListener('change', () => {  
        if (markdownSoap.checked) {  
            renderMarkdown(soapResult, soapMarkdownPreview);  
        } else {  
            hideMarkdown(soapResult, soapMarkdownPreview);  
        }  
    });  
  
    soapResult.addEventListener('input', () => {  
        if (markdownSoap.checked) {  
            renderMarkdown(soapResult, soapMarkdownPreview);  
        }  
    });  
  
    advancedModeCheckbox.addEventListener('change', () => {  
        advancedOptions.forEach(option => {  
            option.style.display = advancedModeCheckbox.checked ? 'block' : 'none';  
        });  
        languageOption.style.display = advancedModeCheckbox.checked ? 'none' : 'block';  
    });  
  
    // Ensure advanced options are visible by default  
    advancedOptions.forEach(option => {  
        option.style.display = 'block';  
    });  
  
    // Enable markdown by default for SOAP note  
    renderMarkdown(soapResult, soapMarkdownPreview);  
  
    recordButton.addEventListener('click', () => {  
        if (!isRecording) {  
            // Start recording  
            navigator.mediaDevices.getUserMedia({ audio: true })  
                .then(stream => {  
                    mediaRecorder = new MediaRecorder(stream);  
                    mediaRecorder.start();  
                    isRecording = true;  
                    recordButton.textContent = 'Stop Recording';  
                    recordButton.classList.add('stop-button');  
                    console.log('Recording started');  
                    const audioChunks = [];  
                    mediaRecorder.addEventListener('dataavailable', event => {  
                        audioChunks.push(event.data);  
                    });  
                    mediaRecorder.addEventListener('stop', () => {  
                        audioBlob = new Blob(audioChunks, { type: 'audio/wav' });  
                        const audioUrl = URL.createObjectURL(audioBlob);  
                        audioPlayback.src = audioUrl;  
                        isRecording = false;  
                        recordButton.textContent = 'Start Recording';  
                        recordButton.classList.remove('stop-button');  
                        console.log('Recording stopped');  
                    });  
  
                    // Start Web Speech API recognition  
                    if (!('webkitSpeechRecognition' in window)) {  
                        console.error('Web Speech API is not supported by this browser.');  
                        return;  
                    }  
  
                    recognition = new webkitSpeechRecognition();  
                    recognition.continuous = true;  
                    recognition.interimResults = true;  
                    recognition.lang = selectLanguage.value;  
  
                    recognition.onstart = function() {  
                        console.log('Speech recognition started');  
                    };  
  
                    recognition.onerror = function(event) {  
                        console.error('Speech recognition error', event);  
                    };  
  
                    recognition.onend = function() {  
                        console.log('Speech recognition ended');  
                    };  
  
                    recognition.onresult = function(event) {  
                        let interim_transcript = '';  
                        for (let i = event.resultIndex; i < event.results.length; ++i) {  
                            if (event.results[i].isFinal) {  
                                final_transcript += event.results[i][0].transcript;  
                            } else {  
                                interim_transcript += event.results[i][0].transcript;  
                            }  
                        }  
                        transcriptionResult.value = final_transcript + interim_transcript;  
                    };  
  
                    recognition.start();  
                })  
                .catch(error => {  
                    console.error('Error accessing microphone', error);  
                });  
        } else {  
            // Stop recording  
            mediaRecorder.stop();  
            if (recognition) {  
                recognition.stop();  
            }  
        }  
    });  
  
    audioFileInput.addEventListener('change', (event) => {  
        console.log('Audio file selected');  
        const file = event.target.files[0];  
        audioBlob = file;  
        const audioUrl = URL.createObjectURL(file);  
        fileAudioPlayback.src = audioUrl;  
    });  
  
    transcribeButton.addEventListener('click', () => {  
        console.log('Transcribe button clicked');  
        const patientName = document.getElementById('patientName').value;  
        const sttModel = document.getElementById('sttModel').value;  
        // Create FormData to send audio file to the backend  
        const formData = new FormData();  
        formData.append('audio', audioBlob);  
        formData.append('stt_model', sttModel);  
        const startTime = performance.now();  
        // Show spinner  
        transcribeSpinner.style.display = 'block';  
        transcribeButton.disabled = true;  
        fetch('http://127.0.0.1:8008/transcribe', {  
            method: 'POST',  
            body: formData,  
        })  
            .then(response => {  
                console.log('Received response from /transcribe');  
                return response.json();  
            })  
            .then(data => {  
                console.log('Transcription data:', data);  
                const transcription = `Nama pasien: ${patientName}\n${data.transcription}`;  
                transcriptionResult.value = transcription;  
                const endTime = performance.now();  
                const processingTime = ((endTime - startTime) / 1000).toFixed(2);  
                transcribeProcessingTime.textContent = `Transcription processing time: ${processingTime} seconds`;  
            })  
            .catch(error => {  
                console.error('Error transcribing audio', error);  
            })  
            .finally(() => {  
                // Hide spinner  
                transcribeSpinner.style.display = 'none';  
                transcribeButton.disabled = false;  
            });  
    });  
  
    generateSoapButton.addEventListener('click', () => {  
        console.log('Generate SOAP button clicked');  
        const transcription = transcriptionResult.value;  
        const llmModel = document.getElementById('llmModel').value;  
        const formData = new FormData();  
        formData.append('transcription', transcription);  
        formData.append('llm_model', llmModel);  
        const startTime = performance.now();  
        // Show spinner  
        soapSpinner.style.display = 'block';  
        generateSoapButton.disabled = true;  
        fetch('http://127.0.0.1:8008/generate_soap', {  
            method: 'POST',  
            body: formData,  
        })  
            .then(response => response.json())  
            .then(data => {  
                console.log('SOAP note data:', data);  
                soapResult.value = data.soap_note;  
                const endTime = performance.now();  
                const processingTime = ((endTime - startTime) / 1000).toFixed(2);  
                soapProcessingTime.textContent = `SOAP generation processing time: ${processingTime} seconds`;  
                if (markdownSoap.checked) {  
                    renderMarkdown(soapResult, soapMarkdownPreview);  
                }  
            })  
            .catch(error => {  
                console.error('Error generating SOAP note', error);  
            })  
            .finally(() => {  
                // Hide spinner  
                soapSpinner.style.display = 'none';  
                generateSoapButton.disabled = false;  
            });  
    });  
});  

document.addEventListener('DOMContentLoaded', () => {  
    const recordButton = document.getElementById('recordButton');  
    const recordedAudioPlayback = document.getElementById('recordedAudioPlayback');  
    const uploadedAudioPlayback = document.getElementById('uploadedAudioPlayback');  
    const audioFileInput = document.getElementById('audioFile');  
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
    const selectLanguage = document.getElementById('select_language');  
    const diarizationCheckbox = document.getElementById('diarizationMode'); 
    let audioBlob = null;  
    let mediaRecorder = null;  
    let isRecording = false;  
    let recognition = null;  
    let final_transcript = '';  
    let audioStream = null;  
  
    // Function to generate a random alpha-numeric string  
    const generateRandomId = (length = 10) => {  
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';  
        let result = '';  
        for (let i = 0; i < length; i++) {  
            result += characters.charAt(Math.floor(Math.random() * characters.length));  
        }  
        return result;  
    };
  
    // Populate language dropdown  
    for (let i = 0; i < langs.length; i++) {  
        selectLanguage.options[i] = new Option(langs[i][0], langs[i][1][0]);  
    }  
    selectLanguage.value = 'id-ID'; // Set default to 'Bahasa Indonesia'  

    const requestId = generateRandomId(); // Generate random ID 
  
    const renderMarkdown = (textarea, preview) => {  
        preview.innerHTML = marked.parse(textarea.value);  
        textarea.style.display = 'none';  
        preview.style.display = 'block';  
    };  
  
    const hideMarkdown = (textarea, preview) => {  
        preview.style.display = 'none';  
        textarea.style.display = 'block';  
    };  

    function renderTranscript(transcript, metadata) {
        const transcriptionResult = document.getElementById('transcriptionResult');
        const audioElement = uploadedAudioPlayback.src ? uploadedAudioPlayback : recordedAudioPlayback;
        
        if (!transcriptionResult) {
            console.error('Transcription result textarea not found');
            return;
        }
        
        if (!audioElement || !audioElement.src) {
            console.error('No audio source found');
            return;
        }
        
        // Set the full transcription in the textarea
        transcriptionResult.value = transcript;

        let highlightInterval;

        const playAudioFromTime = (startTime) => {
            if (audioElement.readyState >= 2) {
                audioElement.currentTime = startTime;
                audioElement.play().catch(e => console.error('Error playing audio:', e));
                startHighlighting();
            } else {
                console.log('Audio not ready, waiting...');
                audioElement.addEventListener('canplay', () => {
                    audioElement.currentTime = startTime;
                    audioElement.play().catch(e => console.error('Error playing audio:', e));
                    startHighlighting();
                }, { once: true });
            }
        };

        const startHighlighting = () => {
            if (highlightInterval) {
                clearInterval(highlightInterval);
            }
            highlightInterval = setInterval(updateHighlight, 100); // Update every 100ms
        };

        const updateHighlight = () => {
            const currentTime = audioElement.currentTime;
            let currentChunk = metadata.find(chunk => currentTime >= chunk.start && currentTime < chunk.end);
            
            if (currentChunk) {
                const start = transcript.indexOf(currentChunk.text);
                const end = start + currentChunk.text.length;
                transcriptionResult.setSelectionRange(start, end);
                transcriptionResult.focus();
            }
        };

        const stopHighlighting = () => {
            if (highlightInterval) {
                clearInterval(highlightInterval);
            }
        };

        audioElement.addEventListener('pause', stopHighlighting);
        audioElement.addEventListener('ended', () => {
            stopHighlighting();
            transcriptionResult.setSelectionRange(0, 0);
        });

        // Add click event listener to the textarea
        transcriptionResult.addEventListener('click', (event) => {
            const clickPosition = transcriptionResult.selectionStart;
            let currentPosition = 0;
            let selectedChunk = null;

            for (const chunk of metadata) {
                const chunkStart = transcript.indexOf(chunk.text, currentPosition);
                if (chunkStart === -1) continue; // Skip if chunk text not found

                const chunkEnd = chunkStart + chunk.text.length;
                if (clickPosition >= chunkStart && clickPosition < chunkEnd) {
                    selectedChunk = chunk;
                    break;
                }
                currentPosition = chunkEnd;
            }

            if (selectedChunk) {
                // Stop the current playback and highlighting
                audioElement.pause();
                stopHighlighting();

                // Start playing from the new position
                playAudioFromTime(selectedChunk.start);
            }
        });
    }
  
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
    });  
  
    // Ensure advanced options are visible by default  
    advancedOptions.forEach(option => {  
        option.style.display = 'block';  
    });  
  
    // Enable markdown by default for SOAP note  
    renderMarkdown(soapResult, soapMarkdownPreview);  
  
    const getMicrophoneAccess = () => {  
        return navigator.mediaDevices.getUserMedia({ audio: true })  
            .then(stream => {  
                audioStream = stream;  
                return stream;  
            })  
            .catch(error => {  
                console.error('Error accessing microphone', error);  
                throw error;  
            });  
    };  
  
    const startRecording = () => {  
        if (!audioStream) {  
            getMicrophoneAccess().then(() => {  
                startMediaRecorder();  
                startSpeechRecognition();  
            });  
        } else {  
            startMediaRecorder();  
            startSpeechRecognition();  
        }  
    };  
  
    const startMediaRecorder = () => {  
        mediaRecorder = new MediaRecorder(audioStream);  
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
            recordedAudioPlayback.src = audioUrl;  
            uploadedAudioPlayback.src = ''; // Clear the uploaded audio source
            recordedAudioPlayback.load(); // Ensure the audio is loaded
            recordedAudioPlayback.addEventListener('canplay', () => {
                console.log('Recorded audio is ready to play');
            }, { once: true });
            isRecording = false;  
            recordButton.textContent = 'Start Recording';  
            recordButton.classList.remove('stop-button');  
            console.log('Recording stopped');  
        });  
    };  
  
    const startSpeechRecognition = () => {  
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
    };  
  
    recordButton.addEventListener('click', () => {  
        if (!isRecording) {  
            startRecording();  
        } else {  
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
        uploadedAudioPlayback.src = audioUrl;  
        recordedAudioPlayback.src = ''; // Clear the recorded audio source
        uploadedAudioPlayback.load(); // Ensure the audio is loaded
        uploadedAudioPlayback.addEventListener('canplay', () => {
            console.log('Uploaded audio is ready to play');
        }, { once: true });
    });  
  
    transcribeButton.addEventListener('click', () => {  
        console.log('Transcribe button clicked');  
        const patientName = document.getElementById('patientName').value;  
        const sttModel = document.getElementById('sttModel').value;   
        const diarization = diarizationCheckbox.checked;
        
        // Determine which audio source to use
        const audioToTranscribe = uploadedAudioPlayback.src ? uploadedAudioPlayback : recordedAudioPlayback;
        
        if (!audioToTranscribe.src) {
            console.error('No audio source found');
            return;
        }
        
        // Create FormData to send audio file to the backend  
        const formData = new FormData();  
        formData.append('audio', audioBlob);  
        formData.append('stt_model', sttModel);  
        formData.append('id', requestId);
        formData.append('diarization', diarization);
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
                const transcription = `Patient Name: ${patientName}\n${data.transcription}`;
                
                if (data.metadata) {
                    renderTranscript(transcription, data.metadata);
                } else {
                    transcriptionResult.value = transcription;
                    console.error('No metadata found in the response');
                }
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
        formData.append('id', requestId);
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

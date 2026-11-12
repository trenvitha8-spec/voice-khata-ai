
import { useState, useRef } from "react";
import "./App.css";

const menuItems = [
  { icon: "🏠", label: "Home" },
  { icon: "🛒", label: "Sales" },
  { icon: "📦", label: "Stock" },
  { icon: "👥", label: "Customers" },
  { icon: "💰", label: "Expenses" },
  { icon: "📊", label: "Reports" },
  { icon: "⚙️", label: "Settings" },
];

const quickActions = [
  { icon: "🛒", label: "Record Sale", color: "green" },
  { icon: "📦", label: "Check Stock", color: "cream" },
  { icon: "👥", label: "Customer Khata", color: "green" },
  { icon: "🧾", label: "Add Expense", color: "cream" },
];

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [activePage, setActivePage] = useState("Home");
  const [language, setLanguage] = useState("Kannada");
  const [listening, setListening] = useState(false);
  const [processing, setProcessing] = useState(false);

  const [transcript, setTranscript] = useState("");
  const [translatedMessage, setTranslatedMessage] = useState("");
  const [audioUrl, setAudioUrl] = useState("");

  const [customerLanguage, setCustomerLanguage] = useState("");
  const [replyTranscript, setReplyTranscript] = useState("");
  const [customerTranslation, setCustomerTranslation] = useState("");
  const [replyAudioUrl, setReplyAudioUrl] = useState("");

  const [error, setError] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // CUSTOMER SPEAKS → SHOPKEEPER HEARS TRANSLATION
  const startRecording = async () => {
    try {
      setError("");
      setTranscript("");
      setTranslatedMessage("");
      setAudioUrl("");
      setReplyTranscript("");
      setCustomerTranslation("");
      setReplyAudioUrl("");

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        setListening(false);
        setProcessing(true);
        stream.getTracks().forEach((track) => track.stop());

        try {
          const audioBlob = new Blob(audioChunksRef.current, {
            type: recorder.mimeType,
          });

          const formData = new FormData();
          formData.append("audio", audioBlob, "customer-voice.webm");
          formData.append("target_language", language);

          const response = await fetch(
            "http://127.0.0.1:8001/translate-audio",
            {
              method: "POST",
              body: formData,
            }
          );

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.detail || "Audio processing failed");
          }

          setTranscript(data.original_transcript);
          setTranslatedMessage(data.translated_message);
          setCustomerLanguage(data.detected_language);

          if (data.audio_base64) {
            setAudioUrl(
              `data:audio/wav;base64,${data.audio_base64}`
            );
          }
        } catch (err) {
          setError(err.message);
        } finally {
          setProcessing(false);
        }
      };

      recorder.start();
      setListening(true);
    } catch (err) {
      setError("Please allow microphone access and try again.");
      setListening(false);
    }
  };

  // SHOPKEEPER REPLIES → CUSTOMER HEARS TRANSLATION
  const startReplyRecording = async () => {
    if (!customerLanguage) {
      setError("Please record the customer's voice first.");
      return;
    }

    try {
      setError("");
      setReplyTranscript("");
      setCustomerTranslation("");
      setReplyAudioUrl("");

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        setListening(false);
        setProcessing(true);
        stream.getTracks().forEach((track) => track.stop());

        try {
          const audioBlob = new Blob(audioChunksRef.current, {
            type: recorder.mimeType,
          });

          const formData = new FormData();
          formData.append("audio", audioBlob, "shopkeeper-reply.webm");
          formData.append("customer_language", customerLanguage);

          const response = await fetch(
            "http://127.0.0.1:8001/reply-audio",
            {
              method: "POST",
              body: formData,
            }
          );

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.detail || "Reply translation failed");
          }

          setReplyTranscript(data.original_transcript);
          setCustomerTranslation(data.translated_message);

          if (data.audio_base64) {
            setReplyAudioUrl(
              `data:audio/wav;base64,${data.audio_base64}`
            );
          }
        } catch (err) {
          setError(err.message);
        } finally {
          setProcessing(false);
        }
      };

      recorder.start();
      setListening(true);
    } catch (err) {
      setError("Please allow microphone access and try again.");
      setListening(false);
    }
  };

  // STOP CURRENT RECORDING
  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
  };

  return (
    <div className="app-shell">
      {menuOpen && (
        <div
          className="menu-overlay"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon">🎙️</div>
          <h2>
            Voice Khata <span>AI</span>
          </h2>
        </div>

        <nav>
          {menuItems.map((item) => (
            <button
              key={item.label}
              className={`nav-item ${
                activePage === item.label ? "active" : ""
              }`}
              onClick={() => {
                setActivePage(item.label);
                setMenuOpen(false);
              }}
            >
              <span>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p>Smart Shop.</p>
          <p>Smart Voice.</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="menu-button"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            ☰
          </button>

          <div>
            <h1>Namaste! 👋</h1>
            <p>Your AI shop assistant is here.</p>
          </div>

          <div className="shop-label">🏪 My Shop</div>
        </header>

        <section className="voice-card">
          <div className="language-control">
            <label htmlFor="language">Shopkeeper language</label>

            <select
              id="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {[
                "Kannada",
                "Telugu",
                "Tamil",
                "Malayalam",
                "Hindi",
                "English",
                "Marathi",
                "Bengali",
                "Gujarati",
                "Punjabi",
              ].map((lang) => (
                <option key={lang}>{lang}</option>
              ))}
            </select>
          </div>

          <div className="voice-content">
            <h2>
              Speak <span>Naturally...</span>
            </h2>

            <p className="subtitle">in any language</p>

            <div className={`waveform ${listening ? "wave-active" : ""}`}>
              {Array.from({ length: 35 }).map((_, i) => (
                <span key={i} style={{ "--i": i }} />
              ))}
            </div>

            {/* CUSTOMER VOICE BUTTON */}
            <button
              className={`mic-button ${
                listening ? "mic-listening" : ""
              }`}
              onClick={listening ? stopRecording : startRecording}
              disabled={processing}
              aria-label={listening ? "Stop recording" : "Start recording"}
            >
              🎙️
            </button>

            <p className="mic-status">
              <span
                className={
                  listening ? "status-dot live" : "status-dot"
                }
              />

              {processing
                ? "Translating your voice..."
                : listening
                ? "Recording... Tap the main microphone to stop"
                : "Tap to speak"}
            </p>

            <p className="voice-hint">
              {listening
                ? "Speak naturally. Tap the main microphone when finished."
                : "Your shop assistant understands your voice."}
            </p>

            {error && (
              <p style={{ color: "#ff7777" }}>{error}</p>
            )}
          </div>

          <div className="shop-illustration">
            <span>🏪</span>
            <p>Voice Khata AI</p>
            <small>Always with you!</small>
          </div>
        </section>

        {/* CUSTOMER → SHOPKEEPER TRANSLATION */}
        {(transcript || translatedMessage || processing) && (
          <section className="page-notice">
            <h3>Customer Language Translation</h3>

            {processing && (
              <p>Processing your voice. Please wait...</p>
            )}

            {transcript && (
              <p>
                <strong>Customer said:</strong> {transcript}
              </p>
            )}

            {translatedMessage && (
              <p>
                <strong>Shopkeeper language ({language}):</strong>{" "}
                {translatedMessage}
              </p>
            )}

            {audioUrl && <audio controls src={audioUrl} />}
          </section>
        )}

        {/* SHOPKEEPER → CUSTOMER TRANSLATION */}
        {(replyTranscript || customerTranslation) && (
          <section className="page-notice">
            <h3>Shopkeeper Reply Translation</h3>

            {replyTranscript && (
              <p>
                <strong>Shopkeeper said:</strong> {replyTranscript}
              </p>
            )}

            {customerTranslation && (
              <p>
                <strong>Translated for customer:</strong>{" "}
                {customerTranslation}
              </p>
            )}

            {replyAudioUrl && (
              <audio controls src={replyAudioUrl} />
            )}
          </section>
        )}

        <section className="quick-actions">
          {quickActions.map((action) => (
            <button
              key={action.label}
              className={`action-card ${action.color}`}
              onClick={() => setActivePage(action.label)}
            >
              <span>{action.icon}</span>
              <strong>{action.label}</strong>
            </button>
          ))}
        </section>

        <div className="tip">
          💡 Speak in your preferred language — we'll understand!
        </div>

        {activePage !== "Home" && (
          <div className="page-notice">
            <h3>{activePage}</h3>

            <p>
              This section will be connected to your shop management features.
            </p>

            <button onClick={() => setActivePage("Home")}>
              Back to Home
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

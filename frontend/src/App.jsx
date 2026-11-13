import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";

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
  { icon: "🛒", label: "Record Sale", page: "Sales", color: "green" },
  { icon: "📦", label: "Check Stock", page: "Stock", color: "cream" },
  { icon: "👥", label: "Customer Khata", page: "Customers", color: "green" },
  { icon: "🧾", label: "Add Expense", page: "Expenses", color: "cream" },
];

const languages = [
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
];

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || data.message || "Request failed.");
  }

  return data;
}

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
  const [pageError, setPageError] = useState("");
  const [success, setSuccess] = useState("");

  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [report, setReport] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingModeRef = useRef("customer");

  // --------------------------------------------------
  // COMMON PAGE HELPERS
  // --------------------------------------------------

  const openPage = (page) => {
    setActivePage(page);
    setMenuOpen(false);
    setPageError("");
    setSuccess("");
  };

  const loadPageData = async (page = activePage) => {
    setPageError("");

    try {
      if (page === "Customers") {
        const data = await apiRequest("/api/customers");
        setCustomers(data);
      }

      if (page === "Sales" || page === "Stock") {
        const data = await apiRequest("/api/products");
        setProducts(data);
      }

      if (page === "Expenses") {
        const data = await apiRequest("/api/expenses");
        setExpenses(data);
      }

      if (page === "Reports") {
        const data = await apiRequest("/api/reports/daily");
        setReport(data);
      }
    } catch (err) {
      setPageError(err.message);
    }
  };

  useEffect(() => {
    if (activePage !== "Home" && activePage !== "Settings") {
      loadPageData(activePage);
    }
  }, [activePage]);

  const submitForm = async (event, path, onSuccess, transform) => {
  event.preventDefault();

  const formElement = event.currentTarget;
  const formData = Object.fromEntries(new FormData(formElement));

  setPageError("");
  setSuccess("");

  try {
    const payload = transform ? transform(formData) : formData;

    const result = await apiRequest(path, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    setSuccess(
      result.message ||
        result.sale?.message ||
        "Saved successfully."
    );

    formElement.reset();

    if (onSuccess) {
      await onSuccess(result);
    }

    await loadPageData(activePage);
  } catch (err) {
    setPageError(err.message);
  }
};

  // --------------------------------------------------
  // VOICE RECORDING
  // --------------------------------------------------

  const startRecording = async (mode = "customer") => {
    try {
      setError("");
      setTranscript("");
      setTranslatedMessage("");
      setAudioUrl("");
      setReplyTranscript("");
      setCustomerTranslation("");
      setReplyAudioUrl("");

      if (mode === "reply" && !customerLanguage) {
        setError("Please record the customer's voice first.");
        return;
      }

      recordingModeRef.current = mode;

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

          if (mode === "customer") {
            formData.append("audio", audioBlob, "customer-voice.webm");
            formData.append("target_language", language);
          } else {
            formData.append("audio", audioBlob, "shopkeeper-reply.webm");
            formData.append("customer_language", customerLanguage);
          }

          const endpoint =
            mode === "customer" ? "/translate-audio" : "/reply-audio";

          const response = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            body: formData,
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.detail || "Audio processing failed.");
          }

          if (mode === "customer") {
            setTranscript(data.original_transcript);
            setTranslatedMessage(data.translated_message);
            setCustomerLanguage(data.detected_language);

            if (data.audio_base64) {
              setAudioUrl(`data:audio/wav;base64,${data.audio_base64}`);
            }
          } else {
            setReplyTranscript(data.original_transcript);
            setCustomerTranslation(data.translated_message);

            if (data.audio_base64) {
              setReplyAudioUrl(
                `data:audio/wav;base64,${data.audio_base64}`
              );
            }
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

  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
  };

  // --------------------------------------------------
  // CUSTOMER KHATA
  // --------------------------------------------------

  const loadTransactions = async (customerName) => {
    if (!customerName) return;

    try {
      setSelectedCustomer(customerName);
      const data = await apiRequest(
        `/api/customers/${encodeURIComponent(customerName)}/transactions`
      );
      setTransactions(data);
    } catch (err) {
      setPageError(err.message);
    }
  };

  // --------------------------------------------------
  // PAGE CONTENT
  // --------------------------------------------------

  const renderHome = () => (
    <>
      <section className="voice-card">
        <div className="language-control">
          <label htmlFor="language">Shopkeeper language</label>
          <select
            id="language"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            {languages.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
        </div>

        <div className="voice-content">
          <h2>
            Speak <span>Naturally...</span>
          </h2>

          <p className="subtitle">in any language</p>

          <div className={`waveform ${listening ? "wave-active" : ""}`}>
            {Array.from({ length: 35 }).map((_, index) => (
              <span key={index} style={{ "--i": index }} />
            ))}
          </div>

          <button
            className={`mic-button ${listening ? "mic-listening" : ""}`}
            onClick={listening ? stopRecording : () => startRecording("customer")}
            disabled={processing}
            aria-label={listening ? "Stop recording" : "Start recording"}
          >
            🎙️
          </button>

          <p className="mic-status">
            <span className={`status-dot ${listening ? "live" : ""}`} />
            {processing
              ? "Translating your voice..."
              : listening
              ? "Recording... Tap the microphone to stop"
              : "Tap to speak"}
          </p>

          <p className="voice-hint">
            {listening
              ? "Speak naturally. Tap the microphone when finished."
              : "Your shop assistant understands your voice."}
          </p>

          {error && <p className="error-message">{error}</p>}
        </div>

        <div className="shop-illustration">
          <span>🏪</span>
          <p>Voice Khata AI</p>
          <small>Always with you!</small>
        </div>
      </section>

      {(transcript || translatedMessage || processing) && (
        <section className="management-card">
          <h3>Customer Language Translation</h3>

          {processing && <p>Processing your voice. Please wait...</p>}

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

          {translatedMessage && (
            <button
              className="primary-button"
              onClick={() => startRecording("reply")}
              disabled={listening || processing}
            >
              🎙️ Reply to Customer
            </button>
          )}
        </section>
      )}

      {(replyTranscript || customerTranslation) && (
        <section className="management-card">
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

          {replyAudioUrl && <audio controls src={replyAudioUrl} />}
        </section>
      )}

      <section className="quick-actions">
        {quickActions.map((action) => (
          <button
            key={action.label}
            className={`action-card ${action.color}`}
            onClick={() => openPage(action.page)}
          >
            <span>{action.icon}</span>
            <strong>{action.label}</strong>
          </button>
        ))}
      </section>

      <div className="tip">
        💡 Speak in your preferred language — we'll understand!
      </div>
    </>
  );

  const renderSales = () => (
    <section className="management-card">
      <h2>🛒 Sales</h2>
      <p>Record a sale and automatically update your stock.</p>

      <form
        className="management-form"
        onSubmit={(event) =>
          submitForm(event, "/api/sales", null, (data) => ({
            product_name: data.product_name,
            quantity: Number(data.quantity),
            payment_method: data.payment_method,
          }))
        }
      >
        <label>Product</label>
        <select name="product_name" required defaultValue="">
          <option value="" disabled>
            Select product
          </option>
          {products.map((product) => (
            <option key={product.name} value={product.name}>
              {product.name} — Stock: {product.quantity}
            </option>
          ))}
        </select>

        <label>Quantity</label>
        <input name="quantity" type="number" min="1" required />

        <label>Payment method</label>
        <select name="payment_method" defaultValue="CASH">
          <option value="CASH">Cash</option>
          <option value="UPI">UPI</option>
          <option value="CARD">Card</option>
        </select>

        <button className="primary-button" type="submit">
          Record Sale
        </button>
      </form>

      <button className="secondary-button" onClick={() => loadPageData("Sales")}>
        Refresh Products
      </button>
    </section>
  );

  const renderStock = () => (
    <>
      <section className="management-card">
        <h2>📦 Stock Management</h2>
        <p>Add products and maintain your shop inventory.</p>

        <form
          className="management-form"
          onSubmit={(event) =>
            submitForm(event, "/api/products", null, (data) => ({
              name: data.name,
              price: Number(data.price),
              quantity: Number(data.quantity),
            }))
          }
        >
          <h3>Add New Product</h3>

          <label>Product name</label>
          <input name="name" required placeholder="Example: Rice" />

          <label>Price per unit (₹)</label>
          <input name="price" type="number" min="0" step="0.01" required />

          <label>Opening quantity</label>
          <input name="quantity" type="number" min="0" required />

          <button className="primary-button" type="submit">
            Add Product
          </button>
        </form>
      </section>

      <section className="management-card">
        <h3>Available Products</h3>

        {products.length === 0 ? (
          <p>No products added yet.</p>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Quantity</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.name}>
                    <td>{product.name}</td>
                    <td>₹{Number(product.price).toFixed(2)}</td>
                    <td>{product.quantity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="management-card">
        <h3>Update Stock Quantity</h3>

        <form
          className="management-form"
          onSubmit={(event) =>
            submitForm(event, "/api/stock", null, (data) => ({
              product_name: data.product_name,
              quantity_change: Number(data.quantity_change),
            }))
          }
        >
          <label>Choose product</label>
          <select name="product_name" required defaultValue="">
            <option value="" disabled>
              Select product
            </option>
            {products.map((product) => (
              <option key={product.name} value={product.name}>
                {product.name}
              </option>
            ))}
          </select>

          <label>Quantity change (use negative number to reduce)</label>
          <input name="quantity_change" type="number" required />

          <button className="primary-button" type="submit">
            Update Stock
          </button>
        </form>
      </section>
    </>
  );

  const renderCustomers = () => (
    <>
      <section className="management-card">
        <h2>👥 Customers & Khata</h2>
        <p>Manage customers and their outstanding balances.</p>

        <form
          className="management-form"
          onSubmit={(event) =>
            submitForm(event, "/api/customers", null, (data) => ({
              name: data.name,
            }))
          }
        >
          <h3>Add Customer</h3>
          <label>Customer name</label>
          <input name="name" required placeholder="Enter customer name" />

          <button className="primary-button" type="submit">
            Add Customer
          </button>
        </form>
      </section>

      <section className="management-card">
        <h3>Customer List</h3>

        {customers.length === 0 ? (
          <p>No customers added yet.</p>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Outstanding balance</th>
                  <th>History</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((customer) => (
                  <tr key={customer.id}>
                    <td>{customer.name}</td>
                    <td>₹{Number(customer.balance || 0).toFixed(2)}</td>
                    <td>
                      <button
                        className="small-button"
                        onClick={() => loadTransactions(customer.name)}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="management-card">
        <h3>Record Khata Transaction</h3>

        <form
          className="management-form"
          onSubmit={(event) =>
            submitForm(event, "/api/khata/transaction", null, (data) => ({
              customer_name: data.customer_name,
              transaction_type: data.transaction_type,
              amount: Number(data.amount),
              description: data.description,
            }))
          }
        >
          <label>Customer</label>
          <select name="customer_name" required defaultValue="">
            <option value="" disabled>
              Select customer
            </option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.name}>
                {customer.name}
              </option>
            ))}
          </select>

          <label>Transaction type</label>
          <select name="transaction_type" defaultValue="CREDIT">
            <option value="CREDIT">Credit — customer took goods</option>
            <option value="PAYMENT">Payment — customer paid</option>
          </select>

          <label>Amount (₹)</label>
          <input name="amount" type="number" min="0.01" step="0.01" required />

          <label>Description</label>
          <input name="description" placeholder="Optional details" />

          <button className="primary-button" type="submit">
            Save Khata Transaction
          </button>
        </form>
      </section>

      {selectedCustomer && (
        <section className="management-card">
          <h3>Transaction History: {selectedCustomer}</h3>

          {transactions.length === 0 ? (
            <p>No transactions found for this customer.</p>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Description</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((transaction) => (
                    <tr key={transaction.id}>
                      <td>{transaction.transaction_type}</td>
                      <td>₹{Number(transaction.amount).toFixed(2)}</td>
                      <td>{transaction.description}</td>
                      <td>{transaction.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );

  const renderExpenses = () => (
    <>
      <section className="management-card">
        <h2>💰 Expenses</h2>
        <p>Record and track your shop expenses.</p>

        <form
          className="management-form"
          onSubmit={(event) =>
            submitForm(event, "/api/expenses", null, (data) => ({
              category: data.category,
              amount: Number(data.amount),
              description: data.description,
            }))
          }
        >
          <label>Expense category</label>
          <select name="category" required defaultValue="">
            <option value="" disabled>
              Select category
            </option>
            <option value="Rent">Rent</option>
            <option value="Electricity">Electricity</option>
            <option value="Transport">Transport</option>
            <option value="Salary">Salary</option>
            <option value="Purchase">Purchase</option>
            <option value="Other">Other</option>
          </select>

          <label>Amount (₹)</label>
          <input name="amount" type="number" min="0.01" step="0.01" required />

          <label>Description</label>
          <input name="description" placeholder="Optional details" />

          <button className="primary-button" type="submit">
            Add Expense
          </button>
        </form>
      </section>

      <section className="management-card">
        <h3>Expense History</h3>

        {expenses.length === 0 ? (
          <p>No expenses recorded yet.</p>
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Description</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((expense) => (
                  <tr key={expense.id}>
                    <td>{expense.category}</td>
                    <td>₹{Number(expense.amount).toFixed(2)}</td>
                    <td>{expense.description}</td>
                    <td>{expense.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );

  const renderReports = () => (
    <section className="management-card">
      <h2>📊 Daily Business Report</h2>
      <p>Your shop's daily performance summary.</p>

      {report ? (
        <div className="report-grid">
          <div className="report-box">
            <span>Today's Sales</span>
            <strong>₹{Number(report.total_sales || 0).toFixed(2)}</strong>
          </div>

          <div className="report-box">
            <span>Number of Sales</span>
            <strong>{report.number_of_sales || 0}</strong>
          </div>

          <div className="report-box">
            <span>Today's Expenses</span>
            <strong>₹{Number(report.total_expenses || 0).toFixed(2)}</strong>
          </div>

          <div className="report-box">
            <span>Expense Entries</span>
            <strong>{report.number_of_expenses || 0}</strong>
          </div>

          <div className="report-box">
            <span>Sales - Expenses</span>
            <strong>
              ₹{Number(report.sales_minus_expenses || 0).toFixed(2)}
            </strong>
          </div>

          <div className="report-box">
            <span>Customer Outstanding</span>
            <strong>
              ₹{Number(report.customer_outstanding || 0).toFixed(2)}
            </strong>
          </div>
        </div>
      ) : (
        <p>Loading report...</p>
      )}

      <button
        className="primary-button"
        onClick={() => loadPageData("Reports")}
      >
        Refresh Report
      </button>
    </section>
  );

  const renderSettings = () => (
    <section className="management-card">
      <h2>⚙️ Settings</h2>
      <p>Choose the language used by your shop assistant.</p>

      <div className="management-form">
        <label>Shopkeeper language</label>
        <select
          value={language}
          onChange={(event) => setLanguage(event.target.value)}
        >
          {languages.map((lang) => (
            <option key={lang} value={lang}>
              {lang}
            </option>
          ))}
        </select>

        <p className="settings-note">
          This language is used for the translated audio that the shopkeeper
          hears when a customer speaks.
        </p>
      </div>
    </section>
  );

  const renderActivePage = () => {
    switch (activePage) {
      case "Sales":
        return renderSales();
      case "Stock":
        return renderStock();
      case "Customers":
        return renderCustomers();
      case "Expenses":
        return renderExpenses();
      case "Reports":
        return renderReports();
      case "Settings":
        return renderSettings();
      default:
        return renderHome();
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
              onClick={() => openPage(item.label)}
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
            <h1>{activePage === "Home" ? "Namaste! 👋" : activePage}</h1>
            <p>
              {activePage === "Home"
                ? "Your AI shop assistant is here."
                : "Manage your shop with Voice Khata AI."}
            </p>
          </div>

          <div className="shop-label">🏪 My Shop</div>
        </header>

        {pageError && <p className="error-message page-message">{pageError}</p>}
        {success && <p className="success-message page-message">{success}</p>}

        {renderActivePage()}
      </main>
    </div>
  );
}

export default App;
import { useState, useEffect } from "react"

const API = "http://localhost:8000"

// ── Chat Panel ──────────────────────────────────
function ChatPanel({ books }) {
  const [selectedBook, setSelectedBook] = useState("")
  const [query, setQuery] = useState("")
  const [history, setHistory] = useState([])
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [memory, setMemory] = useState(null)

  const loadMemory = async (bookId) => {
    const res = await fetch(`${API}/chat/memory/${bookId}`)
    const data = await res.json()
    setMemory(data)
  }
  const loadHistory = async (bookId) => {
  try {
    const res = await fetch(`${API}/chat/history/${bookId}`)
    const data = await res.json()
    setHistory(data.history || [])
  } catch (e) {
    console.error("History error:", e)
  }
}
  const sendMessage = async () => {
    if (!query.trim() || !selectedBook) return
    
    const userMsg = { role: "user", text: query }
    setMessages(prev => [...prev, userMsg])
    setQuery("")
    setLoading(true)

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: parseInt(selectedBook), query })
      })
      const data = await res.json()
      
      setMessages(prev => [...prev, {
        role: "assistant",
        text: data.answer,
        sources: data.sources,
        time: data.time_taken
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: "Error: " + e.message
      }])
    }
    setLoading(false)
  }

  return (
    <div style={styles.chatContainer}>
      <h2 style={styles.heading}>💬 Book Chat</h2>

      {/* Book Selector */}
      <select
        style={styles.select}
        value={selectedBook}
        onChange={e => {
  setSelectedBook(e.target.value)
  setMessages([])
  setMemory(null)
  setHistory([])
  if (e.target.value) {
    loadMemory(e.target.value)
    loadHistory(e.target.value)  
  }
}}
      >
        <option value="">-- Book select karo --</option>
        {books.map(b => (
          <option key={b.id} value={b.id}>
            📚 {b.title} ({b.status})
          </option>
        ))}
      </select>

      {/* Memory Panel */}
      {memory && (
        <div style={styles.memoryPanel}>
          <h3 style={styles.memoryTitle}>📖 Book Memory</h3>
          <div style={styles.memoryGrid}>
            <div style={styles.memoryCard}>
              <b>🟢 Start</b>
              <p>{memory.start?.[0]?.row_text?.slice(0, 150)}...</p>
              <small>Pages {memory.start?.[0]?.start_page}-{memory.start?.[0]?.end_page}</small>
            </div>
            <div style={styles.memoryCard}>
              <b>🟡 Middle</b>
              <p>{memory.middle?.[0]?.row_text?.slice(0, 150)}...</p>
              <small>Pages {memory.middle?.[0]?.start_page}-{memory.middle?.[0]?.end_page}</small>
            </div>
            <div style={styles.memoryCard}>
              <b>🔴 End</b>
              <p>{memory.end?.[0]?.row_text?.slice(0, 150)}...</p>
              <small>Pages {memory.end?.[0]?.start_page}-{memory.end?.[0]?.end_page}</small>
            </div>
          </div>
        </div>
      )}

    {/* History Panel */}
    {history.length > 0 && (
  <div style={styles.historyPanel}>
    <h4 style={{color: "#a78bfa", marginBottom: 8}}>
      📜 Purani Conversations ({history.length})
    </h4>
    {history.slice(0, 5).map((h, i) => (
      <div key={i} style={styles.historyItem}>
        <div style={{color: "#7c3aed", fontSize: 13}}>
          ❓ {h.question}
        </div>
        <div style={{color: "#94a3b8", fontSize: 12, marginTop: 4}}>
          💬 {h.answer}
        </div>
        <div style={{color: "#475569", fontSize: 11, marginTop: 2}}>
          🕐 {new Date(h.created_at).toLocaleString()}
        </div>
      </div>
    ))}
  </div>
)}

      {/* Messages */}
      <div style={styles.messages}>
        {messages.length === 0 && (
          <p style={styles.placeholder}>Koi bhi sawaal pucho is book ke baare mein... 🤔</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={msg.role === "user" ? styles.userMsg : styles.botMsg}>
            <div style={styles.msgText}>
              {msg.role === "user" ? "👤 " : "🤖 "}
              {msg.text}
            </div>
            {msg.sources && (
              <div style={styles.sources}>
                <small>📄 Sources: {msg.sources.map(s =>
                  `${s.pages} (${s.similarity})`
                ).join(" | ")}</small>
                <small> ⏱️ {msg.time}s</small>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={styles.botMsg}>
            <div style={styles.msgText}>🤖 Soch raha hoon... ⏳</div>
          </div>
        )}
      </div>

      {/* Input */}
      <div style={styles.inputRow}>
        <input
          style={styles.input}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && sendMessage()}
          placeholder="Sawaal pucho... (Enter dabao)"
          disabled={!selectedBook || loading}
        />
        <button
          style={styles.sendBtn}
          onClick={sendMessage}
          disabled={!selectedBook || loading || !query.trim()}
        >
          Send 🚀
        </button>
      </div>
    </div>
  )
}

// ── Processing Dashboard ─────────────────────────
function Dashboard({ books, onRefresh }) {
  return (
    <div style={styles.dashboard}>
      <div style={styles.dashHeader}>
        <h2 style={styles.heading}>📊 Processing Dashboard</h2>
        <button style={styles.refreshBtn} onClick={onRefresh}>🔄 Refresh</button>
      </div>

      {books.length === 0 && (
        <p style={styles.placeholder}>Koi book nahi mili — Swagger se upload karo!</p>
      )}

      {books.map(book => (
        <div key={book.id} style={styles.bookCard}>
          <div style={styles.bookHeader}>
            <b>📚 {book.title}</b>
            <span style={{
              ...styles.badge,
              background: book.status === "done" ? "#22c55e" :
                          book.status === "processing" ? "#f59e0b" : "#6b7280"
            }}>
              {book.status === "done" ? "✅ Done" :
               book.status === "processing" ? "⚙️ Processing" : "⏳ Pending"}
            </span>
          </div>

          {book.meta_data && (
            <div style={styles.progressInfo}>
              {/* Progress Bar */}
              {book.meta_data.total_chunks > 0 && (
                <>
                  <div style={styles.progressBar}>
                    <div style={{
                      ...styles.progressFill,
                      width: `${Math.round((book.meta_data.chunks_done / book.meta_data.total_chunks) * 100)}%`
                    }} />
                  </div>
                  <small>
                    {book.meta_data.chunks_done}/{book.meta_data.total_chunks} chunks
                    ({Math.round((book.meta_data.chunks_done / book.meta_data.total_chunks) * 100)}%)
                  </small>
                </>
              )}

              {/* Time Info */}
              <div style={styles.timeInfo}>
                {book.status === "processing" && book.meta_data.estimated_remaining_minutes && (
                  <span>⏱️ Bacha: ~{book.meta_data.estimated_remaining_minutes} min</span>
                )}
                {book.status === "done" && book.meta_data.total_time_minutes && (
                  <span>✅ Total time: {book.meta_data.total_time_minutes} min</span>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Main App ─────────────────────────────────────
export default function App() {
  const [books, setBooks] = useState([])
  const [activeTab, setActiveTab] = useState("dashboard")

  const fetchBooks = async () => {
    try {
      const res = await fetch(`${API}/chat/books`)
      const data = await res.json()
      setBooks(data.books || [])
    } catch (e) {
      console.error("Books fetch error:", e)
    }
  }

  useEffect(() => {
    fetchBooks()
    // Har 30 sec mein auto refresh
    const interval = setInterval(fetchBooks, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>📚 Book Processing Pipeline</h1>
        <div style={styles.tabs}>
          <button
            style={activeTab === "dashboard" ? styles.activeTab : styles.tab}
            onClick={() => setActiveTab("dashboard")}
          >
            📊 Dashboard
          </button>
          <button
            style={activeTab === "chat" ? styles.activeTab : styles.tab}
            onClick={() => setActiveTab("chat")}
          >
            💬 Chat
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === "dashboard"
        ? <Dashboard books={books} onRefresh={fetchBooks} />
        : <ChatPanel books={books.filter(b => b.status === "done")} />
      }
    </div>
  )
}

// ── Styles ───────────────────────────────────────
const styles = {
  app: { fontFamily: "sans-serif", maxWidth: 900, margin: "0 auto", padding: 20, background: "#0f172a", minHeight: "100vh", color: "#e2e8f0" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24, borderBottom: "1px solid #334155", paddingBottom: 16 },
  title: { fontSize: 24, fontWeight: "bold", color: "#7c3aed", margin: 0 },
  tabs: { display: "flex", gap: 8 },
  tab: { padding: "8px 16px", borderRadius: 8, border: "1px solid #334155", background: "#1e293b", color: "#94a3b8", cursor: "pointer" },
  activeTab: { padding: "8px 16px", borderRadius: 8, border: "none", background: "#7c3aed", color: "white", cursor: "pointer" },
  heading: { fontSize: 20, fontWeight: "bold", marginBottom: 16, color: "#a78bfa" },
  dashboard: { background: "#1e293b", borderRadius: 12, padding: 20 },
  dashHeader: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  refreshBtn: { padding: "6px 12px", background: "#334155", border: "none", borderRadius: 6, color: "#e2e8f0", cursor: "pointer" },
  bookCard: { background: "#0f172a", borderRadius: 8, padding: 16, marginBottom: 12, border: "1px solid #334155" },
  bookHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  badge: { padding: "4px 10px", borderRadius: 12, fontSize: 12, color: "white" },
  progressBar: { height: 8, background: "#334155", borderRadius: 4, overflow: "hidden", margin: "8px 0" },
  progressFill: { height: "100%", background: "#7c3aed", borderRadius: 4, transition: "width 0.5s" },
  progressInfo: { marginTop: 8 },
  timeInfo: { marginTop: 4, color: "#94a3b8", fontSize: 13 },
  chatContainer: { background: "#1e293b", borderRadius: 12, padding: 20 },
  select: { width: "100%", padding: 10, borderRadius: 8, background: "#0f172a", border: "1px solid #334155", color: "#e2e8f0", marginBottom: 16, fontSize: 14 },
  memoryPanel: { background: "#0f172a", borderRadius: 8, padding: 16, marginBottom: 16, border: "1px solid #334155" },
  memoryTitle: { fontSize: 16, fontWeight: "bold", marginBottom: 12, color: "#a78bfa" },
  memoryGrid: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 },
  memoryCard: { background: "#1e293b", borderRadius: 8, padding: 12, fontSize: 13, color: "#94a3b8" },
  messages: { minHeight: 300, maxHeight: 400, overflowY: "auto", marginBottom: 16, padding: 8 },
  placeholder: { color: "#475569", textAlign: "center", marginTop: 80 },
  userMsg: { background: "#7c3aed22", borderRadius: 8, padding: 12, marginBottom: 8, borderLeft: "3px solid #7c3aed" },
  botMsg: { background: "#0f172a", borderRadius: 8, padding: 12, marginBottom: 8, borderLeft: "3px solid #22c55e" },
  msgText: { fontSize: 14, lineHeight: 1.6 },
  sources: { marginTop: 8, color: "#64748b", fontSize: 12 },
  inputRow: { display: "flex", gap: 8 },
  input: { flex: 1, padding: 10, borderRadius: 8, background: "#0f172a", border: "1px solid #334155", color: "#e2e8f0", fontSize: 14 },
  sendBtn: { padding: "10px 20px", background: "#7c3aed", border: "none", borderRadius: 8, color: "white", cursor: "pointer", fontSize: 14 },
  historyPanel: {
  background: "#0f172a", borderRadius: 8,
  padding: 12, marginBottom: 12,
  border: "1px solid #1e293b",
  maxHeight: 200, overflowY: "auto"
},
historyItem: {
  padding: "8px 0",
  borderBottom: "1px solid #1e293b"
},
}

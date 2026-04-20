import { useState, useRef, useEffect } from 'react'

export default function Chatbot({ engine }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `I'm monitoring **${engine.name}** in real time. Current RUL is **${engine.rul} cycles** with ${engine.healthPercent}% health. Ask me anything about this engine's condition or maintenance needs.`,
    },
  ])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const buildSystemPrompt = () =>
    `You are an expert turbofan engine maintenance engineer analyzing real-time sensor data from NASA CMAPSS FD001.

Engine: ${engine.name}
Status: ${engine.status.toUpperCase()}
Remaining Useful Life (RUL): ${engine.rul} cycles
Health: ${engine.healthPercent}%
Cycle count: ${engine.cycleCount}
Recent RUL trend (oldest → newest): ${engine.rulHistory.join(', ')}

Answer the maintenance technician's questions concisely and technically. Give specific, actionable advice. If the engine is critical, emphasize urgency. Keep responses under 4 sentences unless a detailed breakdown is explicitly requested.`

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', content: text }
    const updated = [...messages, userMsg]
    setMessages(updated)
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_prompt: buildSystemPrompt(),
          messages: updated.map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-3 border-b border-border shrink-0">
        <p className="text-white text-xs font-semibold">AI Analysis</p>
        <p className="text-muted text-[10px]">Gemini · gemini-2.5-flash</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg, i) => (
          <Message key={i} message={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border shrink-0">
        <div className="flex gap-2">
          <textarea
            className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-muted resize-none focus:outline-none focus:border-accent/50 transition-colors"
            placeholder="Ask about this engine…"
            rows={2}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="px-4 rounded-lg text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 active:scale-95 shrink-0"
            style={{ background: '#3b82f6', color: '#fff' }}
          >
            Send
          </button>
        </div>
        <p className="text-muted/50 text-[10px] mt-1.5">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}

function Message({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div
          className="w-5 h-5 rounded-full shrink-0 mr-2 mt-0.5 flex items-center justify-center text-[8px] font-bold text-white"
          style={{ background: '#3b82f6', boxShadow: '0 0 8px rgba(59,130,246,0.4)' }}
        >
          AI
        </div>
      )}
      <div
        className={`max-w-[85%] px-3.5 py-2.5 rounded-xl text-xs leading-relaxed ${
          isUser
            ? 'text-white'
            : 'text-slate-200'
        }`}
        style={{
          backgroundColor: isUser ? '#3b82f6' : '#1a1a24',
          border: isUser ? 'none' : '1px solid #1e1e2e',
        }}
      >
        <FormattedText text={message.content} />
      </div>
    </div>
  )
}

function FormattedText({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith('**') && part.endsWith('**') ? (
          <strong key={i} className="font-semibold text-white">
            {part.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2">
      <div
        className="w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[8px] font-bold text-white"
        style={{ background: '#3b82f6' }}
      >
        AI
      </div>
      <div className="flex gap-1 px-3 py-2.5 rounded-xl" style={{ backgroundColor: '#1a1a24', border: '1px solid #1e1e2e' }}>
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="w-1 h-1 rounded-full bg-muted animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import HomeScreen from './components/HomeScreen'
import DetailView from './components/DetailView'

export default function App() {
  const [selectedEngine, setSelectedEngine] = useState(null)
  const [engines, setEngines]               = useState([])
  const [loading, setLoading]               = useState(true)
  const [error, setError]                   = useState(null)

  useEffect(() => {
    fetch('/fleet')
      .then(r => {
        if (!r.ok) throw new Error(`Fleet fetch failed: ${r.status}`)
        return r.json()
      })
      .then(data => { setEngines(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  return (
    <div className="flex h-screen bg-bg overflow-hidden">
      <Sidebar
        engines={engines}
        selectedEngine={selectedEngine}
        onSelect={setSelectedEngine}
        onHome={() => setSelectedEngine(null)}
      />

      <main className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full text-muted text-sm">
            Loading fleet data…
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-400 text-sm px-8 text-center">
            {error}
            <br />
            <span className="text-muted text-xs mt-2 block">Make sure the FastAPI server is running on port 8000</span>
          </div>
        ) : selectedEngine ? (
          <DetailView
            engine={selectedEngine}
            onBack={() => setSelectedEngine(null)}
          />
        ) : (
          <HomeScreen engines={engines} onSelect={setSelectedEngine} />
        )}
      </main>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { RunPage } from './pages/RunPage'
import { RunsPage } from './pages/RunsPage'
import { UploadPage } from './pages/UploadPage'
import {
  currentRoute,
  navigate,
  workspaceTitle,
  type Route,
} from './routing'
import './App.css'

function App() {
  const [route, setRoute] = useState<Route>(currentRoute)

  useEffect(() => {
    const update = () => setRoute(currentRoute())
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])

  return (
    <div className="app-shell">
      <aside className="side-rail" aria-label="Навигация">
        <div className="rail-brand">
          <span>AI</span>
        </div>
        <nav className="rail-nav">
          <button
            className={route.page === 'runs' ? 'active' : ''}
            onClick={() => navigate('/runs')}
          >
            <span>▦</span>
            Архив
          </button>
          <button
            className={route.page === 'new' ? 'active' : ''}
            onClick={() => navigate('/runs/new')}
          >
            <span>↑</span>
            Новое видео
          </button>
        </nav>
      </aside>
      <div className="workspace">
        <header className="workspace-header">
          <div className="workspace-header-inner">
            <div className="topbar-left">
              {route.page !== 'runs' && (
                <button className="back-button" onClick={() => navigate('/runs')}>
                  ‹ Назад
                </button>
              )}
              <div className="topbar-title">
                <span>Аналитика рекламы</span>
                <strong>{workspaceTitle(route)}</strong>
              </div>
            </div>
            <div className="topbar-status">
              <span />
              Сервис активен
            </div>
          </div>
        </header>
        <main className="workspace-main">
          {route.page === 'runs' && <RunsPage />}
          {route.page === 'new' && <UploadPage />}
          {route.page === 'run' && <RunPage runId={route.runId} />}
        </main>
      </div>
    </div>
  )
}

export default App

import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import CharterPage from './pages/CharterPage.jsx'
import ManagerPage from './pages/ManagerPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <span className="brand">Spaceport</span>
        <nav>
          <NavLink to="/" end>Charter a Ship</NavLink>
          <NavLink to="/manager">Fleet Manager</NavLink>
        </nav>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<CharterPage />} />
          <Route path="/manager" element={<ManagerPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

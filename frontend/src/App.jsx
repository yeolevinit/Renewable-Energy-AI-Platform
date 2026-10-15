import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Generation from './pages/Generation'
import Weather from './pages/Weather'
import DataQuality from './pages/DataQuality'
import Models from './pages/Models'
import Anomalies from './pages/Anomalies'
import EnergyBalance from './pages/EnergyBalance'
import ScenarioLab from './pages/ScenarioLab'
import Pipeline from './pages/Pipeline'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="generation" element={<Generation />} />
        <Route path="weather" element={<Weather />} />
        <Route path="quality" element={<DataQuality />} />
        <Route path="models" element={<Models />} />
        <Route path="anomalies" element={<Anomalies />} />
        <Route path="energy" element={<EnergyBalance />} />
        <Route path="scenarios" element={<ScenarioLab />} />
        <Route path="pipeline" element={<Pipeline />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

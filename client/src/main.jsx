import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './fonts.css'
import Odds from './Odds.jsx'

// steve - not using this since it gets pinged twice in development and I don't want to eat API credits
// createRoot(document.getElementById('root')).render(
//   <StrictMode>
//     <Odds />
//   </StrictMode>,
// )

createRoot(document.getElementById('root')).render(
    <Odds />,
)
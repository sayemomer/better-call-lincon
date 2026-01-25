import { BrowserRouter, Routes, Route } from "react-router-dom";
import AuthPage from "./pages/AuthPage";
import HomePage from "./pages/HomePage";
import EligibilityPage from "./pages/EligibilityPage";
import DeadlinesPage from "./pages/DeadlinesPage";
import UpdatesPage from "./pages/UpdatesPage";
import DocumentsPage from "./pages/DocumentsPage";
import ChatPage from "./pages/chatPage";
import AboutUsPage from "./pages/AboutUsPage"; 

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AuthPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/eligibility" element={<EligibilityPage />} />
        <Route path="/deadlines" element={<DeadlinesPage />} />
        <Route path="/updates" element={<UpdatesPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/about" element={<AboutUsPage />} /> 
      </Routes>
    </BrowserRouter>
  );
}
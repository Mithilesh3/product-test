import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import App from "./App";
import "./index.css";

// Providers
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { UsageProvider } from "./context/UsageContext";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <UsageProvider>
          <BrowserRouter>
            <App />
            <Toaster position="top-right" />
          </BrowserRouter>
        </UsageProvider>
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>
);
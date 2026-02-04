import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // Keep or modify if needed for global styles
import App from './App';
import 'bootstrap/dist/css/bootstrap.min.css'; // Import Bootstrap CSS

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.jsx';
import {WatchlistProvider} from './WatchlistContext.jsx';
import './style.css';
import './investor.css';

createRoot(document.getElementById('root')).render(<WatchlistProvider><App/></WatchlistProvider>);

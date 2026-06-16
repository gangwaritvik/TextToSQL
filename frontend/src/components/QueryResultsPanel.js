import React, { useState, useEffect } from "react";
import ChatMessage from "./ChatMessage";
import "./QueryResultsPanel.css";

function QueryResultsPanel({ results, isLoading, onCloseTab, onClearAll, onOpenNewQuery, selectedDatabase, onDatabaseChange }) {
  const [selectedTabId, setSelectedTabId] = useState(results[0]?.id || null);
  const [databases, setDatabases] = useState([]);
  const [loadingDatabases, setLoadingDatabases] = useState(true);

  // Fetch available databases on mount
  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        const response = await fetch("http://localhost:8000/databases");
        const data = await response.json();
        setDatabases(data);
        setLoadingDatabases(false);
      } catch (error) {
        console.error("Error fetching databases:", error);
        setLoadingDatabases(false);
      }
    };
    fetchDatabases();
  }, []);

  // Auto-switch to newly added query
  useEffect(() => {
    if (results.length > 0) {
      setSelectedTabId(results[results.length - 1].id);
    }
  }, [results]);

  if (results.length === 0 && !isLoading) {
    return (
      <div className="query-results-panel">
        <div className="panel-header">
          <h3>Query Results</h3>
          <div className="header-actions">
          <div className="database-select-wrapper">
            <label className="database-label">Choose DB</label>
            <select 
              className="database-selector"
              value={selectedDatabase}
              onChange={(e) => onDatabaseChange(e.target.value)}
              disabled={loadingDatabases}
            >
              <option value="" disabled>Select a database...</option>
              {databases.map((db) => (
                <option key={db} value={db}>{db}</option>
              ))}
            </select>
          </div>
            <button 
              className="query-btn" 
              onClick={onOpenNewQuery}
              title="Create a new query"
            >
              Query
            </button>
          </div>
        </div>
        <div className="empty-state">
          <div className="empty-message">
            <p>No queries yet</p>
            <p className="empty-hint">Click the ✚ button to create a new query</p>
          </div>
        </div>
      </div>
    );
  }

  // Show loading animation on fresh page load
  if (isLoading && results.length === 0) {
    return (
      <div className="query-results-panel">
        <div className="panel-header">
          <h3>Query Results</h3>
          <div className="header-actions">
          <div className="database-select-wrapper">
            <label className="database-label">Choose DB</label>
            <select 
              className="database-selector"
              value={selectedDatabase}
              onChange={(e) => onDatabaseChange(e.target.value)}
              disabled={loadingDatabases}
            >
              <option value="" disabled>Select a database...</option>
              {databases.map((db) => (
                <option key={db} value={db}>{db}</option>
              ))}
            </select>
          </div>
            <button 
              className="query-btn" 
              onClick={onOpenNewQuery}
              title="Create a new query"
            >
              Query
            </button>
          </div>
        </div>
        <div className="empty-state">
          <div className="loading-animation">
            <div className="spinner"></div>
            <div className="loading-text">Processing your query...</div>
            <div className="loading-subtext">Calling LLM to generate SQL</div>
          </div>
        </div>
      </div>
    );
  }

  const selectedResult = results.find(r => r.id === selectedTabId);

  return (
    <div className="query-results-panel">
      <div className="panel-header">
        <h3>Query Results</h3>
        <div className="header-actions">
          <div className="database-select-wrapper">
            <label className="database-label">Choose DB</label>
            <select 
              className="database-selector"
              value={selectedDatabase}
              onChange={(e) => onDatabaseChange(e.target.value)}
              disabled={loadingDatabases}
            >
              <option value="" disabled>Select a database...</option>
              {databases.map((db) => (
                <option key={db} value={db}>{db}</option>
              ))}
            </select>
          </div>
          <button 
            className="query-btn" 
            onClick={onOpenNewQuery}
            title="Create a new query"
          >
            Query
          </button>
          {results.length > 1 && (
            <button className="clear-all-btn" onClick={onClearAll}>
              Clear All
            </button>
          )}
        </div>
      </div>

      <div className="tabs-container">
        {results.map((result, index) => (
          <div 
            key={result.id} 
            className={`tab ${selectedTabId === result.id ? 'active' : ''}`}
            onClick={() => setSelectedTabId(result.id)}
          >
            <span className="tab-label">
              Query {index + 1}
            </span>
            <button
              className="tab-close"
              onClick={(e) => {
                e.stopPropagation();
                onCloseTab(result.id);
                if (selectedTabId === result.id && results.length > 1) {
                  const nextResult = results.find(r => r.id !== result.id);
                  setSelectedTabId(nextResult.id);
                }
              }}
              title="Close this query result"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="results-content">
        {isLoading && (
          <div className="loading-container">
            <div className="loading-animation">
              <div className="spinner"></div>
              <div className="loading-text">Processing your query...</div>
              <div className="loading-subtext">Calling LLM to generate SQL</div>
            </div>
          </div>
        )}
        {selectedResult && !isLoading && (
          <div className="result-card">
            <div className="result-query-input">
              <span className="user-icon">👤</span>
              <span className="query-text">{selectedResult.query}</span>
              {selectedResult.database && (
                <span className="database-badge">{selectedResult.database}</span>
              )}
            </div>
            <ChatMessage chat={selectedResult} isInPanel={true} />
          </div>
        )}
      </div>
    </div>
  );
}

export default QueryResultsPanel;

import React, { useState, useEffect } from "react";
import "./ChatMessage.css";
import FullScreenTableModal from "./FullScreenTableModal";

function ChatMessage({ chat, isInPanel }) {
  const [expanded, setExpanded] = useState(true);
  const [copied, setCopied] = useState(false);
  const [isFullscreenOpen, setIsFullscreenOpen] = useState(false);

  // Handle ESC key to close fullscreen modal
  useEffect(() => {
    const handleEscKey = (e) => {
      if (e.key === "Escape" && isFullscreenOpen) {
        setIsFullscreenOpen(false);
      }
    };
    window.addEventListener("keydown", handleEscKey);
    return () => window.removeEventListener("keydown", handleEscKey);
  }, [isFullscreenOpen]);

  // Copy SQL to clipboard
  const handleCopySQL = () => {
    if (chat.sql) {
      navigator.clipboard.writeText(chat.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Download results as CSV
  const handleDownloadCSV = () => {
    if (!chat.results || chat.results.length === 0) return;

    const headers = Object.keys(chat.results[0]);
    const rows = chat.results.map(row => 
      headers.map(header => {
        const value = row[header];
        return typeof value === 'string' && value.includes(',') 
          ? `"${value}"` 
          : value;
      }).join(',')
    );

    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query-results-${Date.now()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="chat-message glass">
      {!isInPanel && (
        <div className="chat-header" onClick={() => setExpanded(!expanded)}>
          <div className="query-text">
            <span className="user-icon">👤</span>
            <span className="query">{chat.query}</span>
          </div>
          <span className="expand-icon">{expanded ? "▼" : "▶"}</span>
        </div>
      )}

      {expanded && (
        <div className="chat-content">
          {/* Retrieved Tables */}
          <div className="content-section">
            <h4 className="section-title">🗂️ Retrieved Tables</h4>
            <div className="chips-container">
              {chat.tables.map((table, idx) => (
                <span key={idx} className="chip">
                  {table}
                </span>
              ))}
            </div>
            <div className="join-path-container">
              <span className="label">Join Path:</span>
              <div className="join-path-animated">
                {chat.joinPath ? (
                  chat.joinPath.split(' → ').map((part, idx, arr) => (
                    <React.Fragment key={idx}>
                      <span className={`join-part join-part-${idx % 3}`}>{part}</span>
                      {idx < arr.length - 1 && <span className="join-arrow">→</span>}
                    </React.Fragment>
                  ))
                ) : (
                  <span className="no-joins">No joins needed</span>
                )}
              </div>
            </div>
          </div>

          {/* Generated SQL */}
          <div className="content-section">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
              <h4 className="section-title" style={{ margin: 0 }}>⚙️ Generated SQL</h4>
              {chat.executionError && (
                <button 
                  className="danger-button"
                  disabled
                  title="This operation has been blocked for safety"
                >
                  🚨 DANGEROUS - BLOCKED
                </button>
              )}
            </div>
            {chat.sql ? (
              <div className="sql-box">
                <pre className="sql-code">{chat.sql}</pre>
                <div className="sql-actions">
                  <button 
                    className="sql-btn"
                    onClick={handleCopySQL}
                    title="Copy SQL to clipboard"
                  >
                    {copied ? '✅ Copied!' : '📋 Copy'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="sql-box" style={{ padding: '15px', color: '#999', textAlign: 'center' }}>
                <p>No SQL generated</p>
              </div>
            )}
          </div>

          {/* Query Results */}
          <div className="content-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', gap: '8px', flexWrap: 'wrap' }}>
              <h4 className="section-title" style={{ margin: 0 }}>📈 Query Results</h4>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className="sql-btn" 
                  style={{ fontSize: '0.7em' }}
                  onClick={handleDownloadCSV}
                  disabled={!chat.results || chat.results.length === 0}
                  title="Download results as CSV"
                >
                  📥 Download CSV
                </button>
                <button 
                  className="sql-btn" 
                  style={{ fontSize: '0.7em' }}
                  onClick={() => setIsFullscreenOpen(true)}
                  disabled={!chat.results || chat.results.length === 0}
                  title="Expand to fullscreen"
                >
                  ⛶ Expand
                </button>
              </div>
            </div>
            {chat.results && chat.results.length > 0 ? (
              <div className="results-wrapper">
                <table className="results-table">
                  <thead>
                    <tr>
                      {Object.keys(chat.results[0] || {}).map((key) => (
                        <th key={key}>{key.charAt(0).toUpperCase() + key.slice(1)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {chat.results.map((row, idx) => (
                      <tr key={idx}>
                        {Object.values(row).map((val, i) => (
                          <td key={i}>{String(val)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: '#999', textAlign: 'center', padding: '20px' }}>
                No results to display
              </p>
            )}
          </div>

          {/* AI Summary */}
          <div className="content-section">
            <h4 className="section-title">🤖 AI Summary</h4>
            <p className="summary-text">{chat.summary}</p>
          </div>

          {/* Analytics */}
          <div className="content-section">
            <h4 className="section-title">📊 Analytics</h4>
            <div className="analytics-grid">
              <div className="stat-item">
                <div className="stat-label">Execution Time</div>
                <div className="stat-value">{chat.executionTime}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Tokens Used</div>
                <div className="stat-value">{chat.tokensUsed}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Complexity</div>
                <div className="stat-value">{chat.complexity}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Table Modal */}
      <FullScreenTableModal
        isOpen={isFullscreenOpen}
        onClose={() => setIsFullscreenOpen(false)}
        tableTitle="Query Results"
        columns={chat.results && chat.results.length > 0 ? Object.keys(chat.results[0]) : []}
        rows={chat.results || []}
      />
    </div>
  );
}

export default ChatMessage;

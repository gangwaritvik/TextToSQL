import React, { useState } from 'react';
import './FullScreenTableModal.css';

function FullScreenTableModal({ isOpen, onClose, tableTitle, columns, rows }) {
  const [searchTerm, setSearchTerm] = useState('');

  if (!isOpen) return null;

  // Filter rows based on search
  const filteredRows = rows.filter((row) => {
    return Object.values(row).some((val) =>
      String(val).toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  return (
    <div className="fullscreen-modal-overlay">
      <div className="fullscreen-modal-container">
        {/* Header */}
        <div className="fullscreen-modal-header">
          <div className="header-content">
            <h1 className="modal-title">📊 {tableTitle}</h1>
            <p className="modal-subtitle">
              Showing {filteredRows.length} of {rows.length} rows
            </p>
          </div>

          {/* Search Bar */}
          <div className="modal-search">
            <input
              type="text"
              placeholder="🔍 Search rows..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>

          {/* Close Button */}
          <button className="modal-close-btn" onClick={onClose} title="Close (ESC)">
            ✕
          </button>
        </div>

        {/* Table */}
        <div className="fullscreen-modal-content">
          {filteredRows.length > 0 ? (
            <table className="fullscreen-table">
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row, idx) => (
                  <tr key={idx}>
                    {columns.map((col) => (
                      <td key={`${idx}-${col}`}>
                        {row[col] !== null && row[col] !== undefined
                          ? String(row[col])
                          : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state-fullscreen">
              <p>No rows match your search</p>
            </div>
          )}
        </div>

        {/* Footer Stats */}
        <div className="fullscreen-modal-footer">
          <div className="footer-stats">
            <span>📋 {columns.length} columns</span>
            <span>📊 {filteredRows.length} rows</span>
            {searchTerm && (
              <span className="search-info">
                Search: <strong>{searchTerm}</strong>
              </span>
            )}
          </div>
          <button className="close-action-btn" onClick={onClose}>
            Close (ESC)
          </button>
        </div>
      </div>
    </div>
  );
}

export default FullScreenTableModal;

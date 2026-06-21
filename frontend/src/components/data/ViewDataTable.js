import React, { useState, useEffect } from "react";
import "./ViewDataTable.css";
import FullScreenTableModal from "../common/FullScreenTableModal";

function ViewDataTable({ refreshTrigger, selectedDatabase: initialDatabase }) {
  const [databases, setDatabases] = useState([]);
  const [tables, setTables] = useState([]);
  const [uploadedTables, setUploadedTables] = useState([]);
  const [selectedDatabase, setSelectedDatabase] = useState(initialDatabase || null);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableData, setTableData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isFullscreenOpen, setIsFullscreenOpen] = useState(false);

  // Fetch databases on component mount
  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch("http://localhost:8000/databases");
        if (!response.ok) throw new Error("Failed to fetch databases");
        const dbNames = await response.json();
        setDatabases(dbNames);
        if (initialDatabase && dbNames.includes(initialDatabase)) {
          setSelectedDatabase(initialDatabase);
        }
      } catch (err) {
        setError(err.message);
        console.error("Error fetching databases:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDatabases();
  }, [initialDatabase]);

  // Fetch tables and uploaded files when database changes or refresh triggered
  useEffect(() => {
    if (!selectedDatabase) return;

    // Clear table selection immediately when database changes
    setSelectedTable(null);
    setTableData(null);

    const fetchTables = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(
          `http://localhost:8000/databases/${selectedDatabase}/tables`
        );
        if (!response.ok) throw new Error(`Failed to fetch tables for ${selectedDatabase}`);
        let tablesData = await response.json();

        // Fetch uploaded tables
        let uploadedData = [];
        try {
          const uploadedResponse = await fetch(
            `http://localhost:8000/upload/tables?database=${selectedDatabase}`
          );
          if (uploadedResponse.ok) {
            uploadedData = await uploadedResponse.json();
            setUploadedTables(uploadedData);
          }
        } catch (err) {
          console.warn("Could not fetch uploaded tables:", err);
          setUploadedTables([]);
        }

        // Filter out uploaded tables from regular tables list
        const uploadedTableNames = uploadedData.map(t => t.name);
        const filteredTables = Array.isArray(tablesData) 
          ? tablesData.filter(t => !uploadedTableNames.includes(t.name))
          : [];
        
        setTables(filteredTables);

        if (filteredTables.length > 0) {
          setSelectedTable(filteredTables[0].name);
        }
      } catch (err) {
        setError(err.message);
        console.error("Error fetching tables:", err);
        setTables([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTables();
  }, [selectedDatabase, refreshTrigger]);

  // Fetch table data when table changes
  useEffect(() => {
    if (!selectedDatabase || !selectedTable) return;

    const fetchTableData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(
          `http://localhost:8000/databases/${selectedDatabase}/tables/${selectedTable}/data`
        );
        if (!response.ok) throw new Error(`Failed to fetch data for ${selectedTable}`);
        const data = await response.json();
        setTableData(data);
      } catch (err) {
        setError(err.message);
        console.error("Error fetching table data:", err);
        setTableData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchTableData();
  }, [selectedDatabase, selectedTable]);

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

  return (
    <div className="view-data-container">
      <div className="view-data-header">
        <h2>📊 View Data</h2>
        <p className="view-data-subtitle">Browse database tables and their contents</p>
      </div>

      {loading && (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading databases...</p>
        </div>
      )}

      {error && (
        <div className="error-state">
          <p>Error: {error}</p>
          <p style={{ fontSize: "0.9em", marginTop: "10px" }}>
            Make sure the backend is running on http://localhost:8000
          </p>
        </div>
      )}

      {!loading && !error && (
        <div className="data-view-wrapper">
          <div className="selectors-section">
            <div className="selector-group">
              <label className="selector-label">Select Database:</label>
              <div className="selector-buttons">
                {databases.length === 0 ? (
                  <span className="no-items">No databases found</span>
                ) : (
                  databases.map((dbName) => (
                    <button
                      key={dbName}
                      className={`selector-btn db-btn ${selectedDatabase === dbName ? "active" : ""}`}
                      onClick={() => setSelectedDatabase(dbName)}
                    >
                      🗄️ {dbName}
                    </button>
                  ))
                )}
              </div>
            </div>

            <div className="selector-group">
              <label className="selector-label">Select Table:</label>
              <div className="selector-buttons">
                {tables.length === 0 && uploadedTables.length === 0 ? (
                  <span className="no-items">No tables in this database</span>
                ) : (
                  <>
                    {tables.length > 0 && (
                      <div className="table-section-header">📋 Existing Tables</div>
                    )}
                    {tables.map((table) => (
                      <button
                        key={table.name}
                        className={`selector-btn table-btn ${selectedTable === table.name ? "active" : ""}`}
                        onClick={() => setSelectedTable(table.name)}
                      >
                        📋 {table.name} ({table.rows} rows)
                      </button>
                    ))}
                    {uploadedTables.length > 0 && (
                      <div className="table-section-header uploaded">📤 Uploaded Files</div>
                    )}
                    {uploadedTables.map((table) => (
                      <button
                        key={table.name}
                        className={`selector-btn table-btn uploaded ${selectedTable === table.name ? "active" : ""}`}
                        onClick={() => setSelectedTable(table.name)}
                      >
                        📤 {table.name} ({table.rows} rows)
                      </button>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="data-table-container">
            {!tableData ? (
              <div className="empty-state">
                <p>Select a table to view its data</p>
              </div>
            ) : tableData.rows && tableData.rows.length > 0 ? (
              <div className="data-table-wrapper">
                <div className="table-info">
                  <span className="row-count">📊 {tableData.rows.length} row{tableData.rows.length !== 1 ? 's' : ''}</span>
                  <span className="col-count">📋 {tableData.columns.length} column{tableData.columns.length !== 1 ? 's' : ''}</span>
                  <button 
                    className="expand-btn"
                    onClick={() => setIsFullscreenOpen(true)}
                    title="Expand to fullscreen"
                  >
                    ⛶ Expand
                  </button>
                </div>
                <div className="table-scroll-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {tableData.columns.map((col) => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.rows.map((row, idx) => (
                        <tr key={idx}>
                          {tableData.columns.map((col) => (
                            <td key={`${idx}-${col}`}>
                              {row[col] !== null && row[col] !== undefined ? String(row[col]) : "-"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <p>No data found in this table</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fullscreen Table Modal */}
      <FullScreenTableModal
        isOpen={isFullscreenOpen}
        onClose={() => setIsFullscreenOpen(false)}
        tableTitle={selectedTable}
        columns={tableData?.columns || []}
        rows={tableData?.rows || []}
      />
    </div>
  );
}

export default ViewDataTable;

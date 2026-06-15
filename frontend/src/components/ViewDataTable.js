import React, { useState, useEffect } from "react";
import "./ViewDataTable.css";

function ViewDataTable() {
  const [databases, setDatabases] = useState([]);
  const [tables, setTables] = useState([]);
  const [selectedDatabase, setSelectedDatabase] = useState(null);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableData, setTableData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
        // Don't auto-select - wait for user to select
      } catch (err) {
        setError(err.message);
        console.error("Error fetching databases:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDatabases();
  }, []);

  // Fetch tables when database changes
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
        const tablesData = await response.json();
        setTables(Array.isArray(tablesData) ? tablesData : []);
        if (Array.isArray(tablesData) && tablesData.length > 0) {
          setSelectedTable(tablesData[0].name);
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
  }, [selectedDatabase]);

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
                {tables.length === 0 ? (
                  <span className="no-items">No tables in this database</span>
                ) : (
                  tables.map((table) => (
                    <button
                      key={table.name}
                      className={`selector-btn table-btn ${selectedTable === table.name ? "active" : ""}`}
                      onClick={() => setSelectedTable(table.name)}
                    >
                      📋 {table.name} ({table.rows} rows)
                    </button>
                  ))
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
                </div>
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
            ) : (
              <div className="empty-state">
                <p>No data found in this table</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ViewDataTable;

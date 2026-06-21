import React, { useState, useEffect } from "react";
import "./DatabaseSchemaView.css";
import FullScreenTableModal from "../common/FullScreenTableModal";

function DatabaseSchemaView({ refreshTrigger, selectedDatabase }) {
  const [expandedDatabase, setExpandedDatabase] = useState(null);
  const [expandedSchema, setExpandedSchema] = useState(null);
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fullscreenSchema, setFullscreenSchema] = useState(null);

  // Fetch databases and their schemas on component mount or refresh
  useEffect(() => {
    const fetchDatabasesAndSchemas = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch all databases
        const dbResponse = await fetch("http://localhost:8000/databases");
        if (!dbResponse.ok) throw new Error("Failed to fetch databases");
        const dbNames = await dbResponse.json();

        // Fetch schema for each database
        const dbsWithTables = await Promise.all(
          dbNames.map(async (dbName, dbIndex) => {
            try {
              // Fetch regular tables
              const tablesResponse = await fetch(
                `http://localhost:8000/databases/${dbName}/tables`
              );
              if (!tablesResponse.ok) {
                console.warn(`Failed to fetch tables for ${dbName}`);
                return { id: dbIndex, name: dbName, tables: [] };
              }

              let tablesData = await tablesResponse.json();
              tablesData = Array.isArray(tablesData) ? tablesData : [];

              // Fetch uploaded tables for this database
              let uploadedData = [];
              try {
                const uploadedResponse = await fetch(
                  `http://localhost:8000/upload/tables?database=${dbName}`
                );
                if (uploadedResponse.ok) {
                  uploadedData = await uploadedResponse.json();
                }
              } catch (err) {
                console.warn(`Could not fetch uploaded tables for ${dbName}:`, err);
              }

              // Get list of uploaded table names
              const uploadedTableNames = uploadedData.map(t => t.name);

              // Filter out uploaded tables from regular tables list (to avoid duplicates)
              const regularTablesOnly = tablesData.filter(
                t => !uploadedTableNames.includes(t.name)
              );

              // Combine and prepare all tables
              const allTables = [
                ...regularTablesOnly.map(t => ({ ...t, isUploaded: false })),
                ...uploadedData.map(t => ({ ...t, isUploaded: true }))
              ];

              // Fetch schema for each table
              const tablesWithSchema = await Promise.all(
                allTables.map(async (table, tableIndex) => {
                  try {
                    const schemaResponse = await fetch(
                      `http://localhost:8000/databases/${dbName}/tables/${table.name}/schema`
                    );
                    if (!schemaResponse.ok) {
                      console.warn(`Failed to fetch schema for ${table.name}`);
                      return {
                        id: tableIndex,
                        name: table.name,
                        rows: table.rows || 0,
                        columns: [],
                        schema: [],
                        isUploaded: table.isUploaded
                      };
                    }

                    const schemaData = await schemaResponse.json();
                    return {
                      id: tableIndex,
                      name: table.name,
                      rows: table.rows || 0,
                      columns: schemaData.columns.map((col) => col.name),
                      schema: schemaData.columns,
                      isUploaded: table.isUploaded
                    };
                  } catch (err) {
                    console.error(`Error fetching schema for ${table.name}:`, err);
                    return {
                      id: tableIndex,
                      name: table.name,
                      rows: table.rows || 0,
                      columns: [],
                      schema: [],
                      isUploaded: table.isUploaded
                    };
                  }
                })
              );

              return {
                id: dbIndex,
                name: dbName,
                tables: tablesWithSchema
              };
            } catch (err) {
              console.error(`Error processing database ${dbName}:`, err);
              return { id: dbIndex, name: dbName, tables: [] };
            }
          })
        );

        setDatabases(dbsWithTables);
        if (dbsWithTables.length > 0) {
          setExpandedDatabase(0);
        }
      } catch (err) {
        setError(err.message);
        console.error("Error fetching databases:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDatabasesAndSchemas();
  }, [refreshTrigger, selectedDatabase]);

  // Handle ESC key to close fullscreen modal
  useEffect(() => {
    const handleEscKey = (e) => {
      if (e.key === "Escape" && fullscreenSchema !== null) {
        setFullscreenSchema(null);
      }
    };
    window.addEventListener("keydown", handleEscKey);
    return () => window.removeEventListener("keydown", handleEscKey);
  }, [fullscreenSchema]);

  const toggleDatabase = (id) => {
    setExpandedDatabase(expandedDatabase === id ? null : id);
  };

  const toggleSchema = (dbId, tableId, dbName, tableName) => {
    const key = `${dbId}-${tableId}`;
    if (expandedSchema === key) {
      // Close if already open
      setExpandedSchema(null);
    } else {
      // Open this one, close others
      setExpandedSchema(key);
    }
  };

  return (
    <div className="schema-view-container">
      <div className="schema-view-header">
        <h2>🗄️ Database Schema</h2>
        <p className="schema-view-subtitle">View table structures and data types</p>
      </div>

      <div className="schema-explorer">
        {loading && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading databases and schemas...</p>
          </div>
        )}

        {error && (
          <div className="error-state">
            <p>❌ Error loading databases: {error}</p>
            <p style={{ fontSize: "0.9em", marginTop: "10px" }}>
              Make sure the backend is running on http://localhost:8000
            </p>
          </div>
        )}

        {!loading && !error && databases.length === 0 && (
          <div className="empty-state">
            <p>📭 No databases found</p>
          </div>
        )}

        {!loading && !error && databases.length > 0 && (
          databases.map((db) => (
            <div key={db.id} className="db-section">
              <button
                className="db-section-header"
                onClick={() => toggleDatabase(db.id)}
              >
                <span className="toggle-icon">{expandedDatabase === db.id ? "▼" : "▶"}</span>
                <span className="db-section-icon">🗄️</span>
                <span className="db-section-name">{db.name}</span>
                <span className="table-badge">{db.tables.length}</span>
              </button>

              {expandedDatabase === db.id && (
                <div className="tables-section">
                  {db.tables.length === 0 ? (
                    <div className="empty-tables">
                      <p>No tables in this database</p>
                    </div>
                  ) : (
                    db.tables.map((table) => {
                      const tableKey = `${db.id}-${table.id}`;
                      const isSchemaExpanded = expandedSchema === tableKey;
                      return (
                        <div key={table.id} className="table-section" data-uploaded={table.isUploaded || false}>
                          <button
                            className="table-section-header"
                            onClick={() => toggleSchema(db.id, table.id, db.name, table.name)}
                          >
                            <span className="toggle-icon">{isSchemaExpanded ? "▼" : "▶"}</span>
                            <span className="table-section-icon">{table.isUploaded ? "📤" : "📋"}</span>
                            <span className="table-section-name">{table.name}</span>
                            <span className="column-badge">{table.columns.length} cols</span>
                            <span className="row-count-badge">{table.rows || 0} rows</span>
                          </button>

                          {isSchemaExpanded && (
                            <div className="schema-table-container">
                              {table.schema.length === 0 ? (
                                <p className="no-schema">No schema information available</p>
                              ) : (
                                <>
                                  <div className="schema-header-actions">
                                    <button 
                                      className="expand-schema-btn"
                                      onClick={() => setFullscreenSchema({
                                        tableName: table.name,
                                        columns: ['Field', 'Type', 'Nullable', 'Key', 'Default'],
                                        rows: table.schema.map(col => ({
                                          Field: col.name,
                                          Type: col.type,
                                          Nullable: col.nullable ? 'YES' : 'NO',
                                          Key: col.primary_key ? 'PRI' : '-',
                                          Default: col.default || '-'
                                        }))
                                      })}
                                      title="Expand to fullscreen"
                                    >
                                      ⛶ Expand
                                    </button>
                                  </div>
                                  <div className="schema-table-scroll">
                                    <table className="schema-table">
                                      <thead>
                                        <tr>
                                          <th>Field</th>
                                          <th>Type</th>
                                          <th>Nullable</th>
                                          <th>Key</th>
                                          <th>Default</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {table.schema.map((col, idx) => (
                                          <tr key={idx}>
                                            <td className="field-name">{col.name}</td>
                                            <td className="field-type">{col.type}</td>
                                            <td className="field-nullable">{col.nullable ? "YES" : "NO"}</td>
                                            <td className="field-key">
                                              {col.primary_key ? "PRI" : "-"}
                                          </td>
                                          <td className="field-default">{col.default || "-"}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Fullscreen Schema Modal */}
      <FullScreenTableModal
        isOpen={fullscreenSchema !== null}
        onClose={() => setFullscreenSchema(null)}
        tableTitle={fullscreenSchema?.tableName || ""}
        columns={fullscreenSchema?.columns || []}
        rows={fullscreenSchema?.rows || []}
      />
    </div>
  );
}

export default DatabaseSchemaView;

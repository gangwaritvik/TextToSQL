import React, { useState, useEffect } from "react";
import "./DatabaseSchemaView.css";

function DatabaseSchemaView() {
  const [expandedDatabase, setExpandedDatabase] = useState(null);
  const [expandedSchema, setExpandedSchema] = useState(null); // Only one schema at a time
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch databases and their schemas on component mount
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
              const tablesResponse = await fetch(
                `http://localhost:8000/databases/${dbName}/tables`
              );
              if (!tablesResponse.ok) {
                console.warn(`Failed to fetch tables for ${dbName}`);
                return { id: dbIndex, name: dbName, tables: [] };
              }

              const tablesData = await tablesResponse.json();

              // Fetch schema for each table
              const tablesWithSchema = await Promise.all(
                (Array.isArray(tablesData) ? tablesData : []).map(async (table, tableIndex) => {
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
                        schema: []
                      };
                    }

                    const schemaData = await schemaResponse.json();
                    return {
                      id: tableIndex,
                      name: table.name,
                      rows: table.rows || 0,
                      columns: schemaData.columns.map((col) => col.name),
                      schema: schemaData.columns
                    };
                  } catch (err) {
                    console.error(`Error fetching schema for ${table.name}:`, err);
                    return {
                      id: tableIndex,
                      name: table.name,
                      rows: table.rows || 0,
                      columns: [],
                      schema: []
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
  }, []);

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
                        <div key={table.id} className="table-section">
                          <button
                            className="table-section-header"
                            onClick={() => toggleSchema(db.id, table.id, db.name, table.name)}
                          >
                            <span className="toggle-icon">{isSchemaExpanded ? "▼" : "▶"}</span>
                            <span className="table-section-icon">📋</span>
                            <span className="table-section-name">{table.name}</span>
                            <span className="column-badge">{table.columns.length} cols</span>
                            <span className="row-count-badge">{table.rows || 0} rows</span>
                          </button>

                          {isSchemaExpanded && (
                            <div className="schema-table-container">
                              {table.schema.length === 0 ? (
                                <p className="no-schema">No schema information available</p>
                              ) : (
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
    </div>
  );
}

export default DatabaseSchemaView;

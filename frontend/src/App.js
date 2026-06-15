import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import DatabaseSchemaView from "./components/DatabaseSchemaView";
import ViewDataTable from "./components/ViewDataTable";
import QueryResultsPanel from "./components/QueryResultsPanel";
import QueryModal from "./components/QueryModal";
import "./App.css";

function App() {
  const [activeView, setActiveView] = useState("query");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [queryResults, setQueryResults] = useState([]);
  const [selectedDatabase, setSelectedDatabase] = useState(() => {
    // Load from localStorage on mount, default to "fastapi_db"
    return localStorage.getItem("selectedDatabase") || "fastapi_db";
  });

  // Save selected database to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem("selectedDatabase", selectedDatabase);
  }, [selectedDatabase]);

  const handleNewChat = async (query) => {
    try {
      // Call backend API to process query
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: query,
          database: selectedDatabase
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const result = await response.json();
      setQueryResults([...queryResults, { ...result, database: selectedDatabase }]);
    } catch (error) {
      console.error("Error processing query:", error);
      // Show error to user
      const errorResult = {
        id: Date.now(),
        query: query,
        database: selectedDatabase,
        tables: [],
        joinPath: "",
        confidence: 0,
        sql: "ERROR",
        results: [],
        summary: `Error: ${error.message}`,
        executionTime: "0ms",
        tokensUsed: "0",
        complexity: "N/A"
      };
      setQueryResults([...queryResults, errorResult]);
    }
  };

  const handleCloseTab = (resultId) => {
    setQueryResults(queryResults.filter(r => r.id !== resultId));
  };

  const handleClearAll = () => {
    setQueryResults([]);
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleModalSubmit = (query) => {
    handleNewChat(query);
    handleCloseModal();
  };

  return (
    <div className="app-layout">
      <QueryModal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
        onSubmit={handleModalSubmit}
      />
      <div className="sidebar">
        <Sidebar activeView={activeView} onViewChange={setActiveView} />
      </div>
      <div className="main-content">
        {activeView === "query" && (
          <div className="query-layout">
            <div className="results-panel-area">
              <QueryResultsPanel 
                results={queryResults} 
                onCloseTab={handleCloseTab}
                onClearAll={handleClearAll}
                onOpenNewQuery={handleOpenModal}
                selectedDatabase={selectedDatabase}
                onDatabaseChange={setSelectedDatabase}
              />
            </div>
          </div>
        )}
        {activeView === "schema" && (
          <DatabaseSchemaView />
        )}
        {activeView === "data" && (
          <ViewDataTable />
        )}
      </div>
    </div>
  );
}

export default App;  

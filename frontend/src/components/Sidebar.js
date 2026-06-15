import React from "react";
import "./Sidebar.css";

function Sidebar({ activeView, onViewChange }) {
  const menuItems = [
    { id: "query", label: "Query", icon: "💬" },
    { id: "schema", label: "Database Schema", icon: "🗄️" },
    { id: "data", label: "View Data", icon: "📊" }
  ];

  return (
    <div className="sidebar-nav">
      <div className="sidebar-header">
        <h1>📝 SQL Master</h1>
        <p className="sidebar-subtitle">Text-to-SQL</p>
      </div>

      <nav className="sidebar-menu">
        {menuItems.map((item) => (
          <button
            key={item.id}
            className={`menu-item ${activeView === item.id ? "active" : ""}`}
            onClick={() => onViewChange(item.id)}
          >
            <span className="menu-icon">{item.icon}</span>
            <span className="menu-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <p className="footer-text">v1.0.0</p>
        <p className="footer-subtext">Powered by AI</p>
      </div>
    </div>
  );
}

export default Sidebar;  

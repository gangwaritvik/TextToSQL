# Text-to-SQL 🗣️➡️📊

A full-stack application that converts natural language queries to SQL using AI, with React frontend and FastAPI backend for PostgreSQL integration.

---

## **Project Structure**

```
TextToSQL/
├── frontend/              # React 18 UI
│   ├── src/
│   │   ├── components/    # React components (ChatInput, ChatMessage, etc.)
│   │   ├── App.js
│   │   └── index.css
│   └── package.json
├── main.py               # FastAPI backend
├── pyproject.toml        # Python dependencies
├── .env                  # PostgreSQL credentials (git-ignored)
└── README.md
```

---

## **Backend Setup 🚀**

### **Requirements**
- Python 3.10+
- PostgreSQL 12+
- pip

### **Installation**

1. **Install dependencies:**
   ```bash
   cd c:\Users\gangwarr\Documents\TextToSQL
   pip install fastapi==0.104.1 uvicorn==0.24.0 psycopg2-binary==2.9.9 sqlalchemy==2.0.23
   ```

   Or use pyproject.toml:
   ```bash
   pip install -e .
   ```

2. **Configure PostgreSQL connection:**
   - Update `.env` with your PostgreSQL credentials:
     ```env
     DB_HOST=localhost
     DB_PORT=5432
     DB_USER=gangwarr
     DB_PASSWORD=USA@#5959
     DB_NAME=Sample
     ```

3. **Run the backend:**
   ```bash
   python main.py
   ```
   
   Backend will start at `http://localhost:8000`

---

## **API Endpoints 📡**

### **1. Health Check**
```
GET /health
```
Returns server status.

---

### **2. List All Databases**
```
GET /databases
```
Returns all PostgreSQL databases accessible by the user.

**Response:**
```json
["Sample", "postgres", "template1", "MyDatabase"]
```

---

### **3. Get Tables in Database**
```
GET /databases/{database_name}/tables
```
Returns all tables in a specific database with row counts.

**Example:** `GET /databases/Sample/tables`

**Response:**
```json
[
  {
    "name": "customers",
    "schema": "public",
    "rows": 150
  },
  {
    "name": "orders",
    "schema": "public",
    "rows": 3200
  }
]
```

---

### **4. Get Table Schema**
```
GET /databases/{database_name}/tables/{table_name}/schema
```
Returns detailed schema including columns, types, and constraints.

**Example:** `GET /databases/Sample/tables/customers/schema`

**Response:**
```json
{
  "table_name": "customers",
  "database": "Sample",
  "columns": [
    {
      "name": "id",
      "type": "INTEGER",
      "nullable": false,
      "primary_key": true,
      "default": null
    },
    {
      "name": "name",
      "type": "VARCHAR(255)",
      "nullable": false,
      "primary_key": false,
      "default": null
    }
  ],
  "primary_keys": ["id"],
  "foreign_keys": [],
  "column_count": 2
}
```

---

### **5. Get Full Database Schema**
```
GET /databases/{database_name}/schema
```
Returns complete schema for all tables in a database.

**Example:** `GET /databases/Sample/schema`

**Response:**
```json
{
  "database": "Sample",
  "tables": [
    {
      "name": "customers",
      "columns": [...],
      "primary_keys": ["id"]
    },
    {
      "name": "orders",
      "columns": [...],
      "primary_keys": ["order_id"]
    }
  ],
  "table_count": 2
}
```

---

## **Frontend Setup 🎨**

### **Installation**

1. Navigate to frontend:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm start
   ```

Frontend runs at `http://localhost:3000`

---

## **Features ✨**

### **Backend**
- ✅ Fetch all PostgreSQL databases
- ✅ List all tables in each database
- ✅ Get detailed table schemas (columns, types, constraints)
- ✅ Display row counts
- ✅ CORS enabled for frontend communication
- ✅ Error handling with detailed messages
- ✅ FastAPI auto-documentation at `/docs`

### **Frontend**
- ✅ 3-view navigation (Query, Schema, Data)
- ✅ Query input with send button
- ✅ Expandable query history
- ✅ Database schema browser
- ✅ Data table selector
- ✅ Dark minimal design with colorful accents
- ✅ Teal glow input box with modern typography

---

## **How to Use 🔄**

1. **Start Backend:**
   ```bash
   python main.py
   ```

2. **Start Frontend:**
   ```bash
   cd frontend && npm start
   ```

3. **Open Browser:** Visit `http://localhost:3000`

4. **View API Docs:** Visit `http://localhost:8000/docs`

---

## **Testing API with cURL 🧪**

```bash
# Get all databases
curl http://localhost:8000/databases

# Get tables in Sample database
curl http://localhost:8000/databases/Sample/tables

# Get customers table schema
curl http://localhost:8000/databases/Sample/tables/customers/schema

# Get full database schema
curl http://localhost:8000/databases/Sample/schema
```

---

## **Environment Variables 🔐**

- `DB_HOST` - PostgreSQL server address
- `DB_PORT` - PostgreSQL port
- `DB_USER` - PostgreSQL username
- `DB_PASSWORD` - PostgreSQL password
- `DB_NAME` - Default database to connect to

**Note:** Keep `.env` secure and never commit to version control!

---

## **Troubleshooting 🔧**

| Issue | Solution |
|-------|----------|
| `connection refused` | Ensure PostgreSQL is running on `localhost:5432` |
| `FATAL: password authentication failed` | Check DB_USER and DB_PASSWORD in `.env` |
| `database does not exist` | Ensure DB_NAME database exists in PostgreSQL |
| `Module not found` | Run `pip install -e .` to install dependencies |
| `Port 8000 already in use` | Change port in `main.py` uvicorn.run() |

---

## **Next Steps 🎯**

- [ ] Integrate backend with frontend for live database browsing
- [ ] Add SQL query execution endpoint
- [ ] Implement natural language to SQL conversion using LLM
- [ ] Add query history persistence
- [ ] Create user authentication
- [ ] Add data export (CSV, JSON)
- [ ] Implement query optimization suggestions

---

**Created with ❤️ for SQL enthusiasts**

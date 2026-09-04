CREATE TABLE contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  email TEXT,
  phone TEXT,
  company TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  contact_id INTEGER,
  intent TEXT NOT NULL,
  product TEXT,
  quantity TEXT,
  order_reference TEXT,
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'Nuevo',
  created_at TEXT NOT NULL,
  FOREIGN KEY(contact_id) REFERENCES contacts(id)
);
CREATE TABLE interactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  message TEXT NOT NULL,
  intent TEXT,
  confidence REAL,
  created_at TEXT NOT NULL
);

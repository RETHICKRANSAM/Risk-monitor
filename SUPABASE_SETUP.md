# Supabase Setup Guide

## ✅ What's Been Done

1. **Installed Supabase Python client** (`supabase==2.10.0`)
2. **Created configuration files**:
   - Updated `config.py` with Supabase settings
   - Updated `.env` with Supabase credentials
   - Created `supabase_client.py` for easy client access
3. **Created example files**:
   - `example_supabase_usage.py` - Examples of how to use Supabase
   - `test_supabase_connection.py` - Test script for connection
4. **Integrated with Flask app** (`app.py`)

## 🔑 Getting Your Supabase API Key

### Step 1: Go to Supabase Dashboard
1. Visit: https://app.supabase.com
2. Select your project: `iemqgpjvslrixivfkaet`

### Step 2: Get API Keys
1. Click on **Project Settings** (gear icon in bottom left)
2. Click on **API** in the sidebar
3. Find the **Project API keys** section
4. Copy the **anon** / **public** key (NOT the service_role key)
   - It should start with `eyJhbGci...` and be very long (~200+ characters)

### Step 3: Update .env File
Replace the current `SUPABASE_KEY` in your `.env` file with the correct key:

```env
SUPABASE_URL=https://iemqgpjvslrixivfkaet.supabase.co
SUPABASE_KEY=eyJhbGci... (your full anon key here)
```

## 🧪 Testing the Connection

After updating the API key, run:

```bash
python test_supabase_connection.py
```

You should see:
```
✓ SUPABASE_URL: https://iemqgpjvslrixivfkaet.supabase.co
✓ SUPABASE_KEY: eyJhbGci...
✓ Supabase client initialized successfully!
✓ Database connection successful!
```

## 📝 Using Supabase in Your Code

### Method 1: Using the helper functions

```python
from supabase_client import query_table, insert_data, update_data, delete_data

# Query data
alerts = query_table("alerts", {"severity": "critical"})

# Insert data
new_alert = insert_data(
    "alerts",
    {
        "title": "Security Alert",
        "severity": "high",
        "description": "Suspicious activity detected",
    },
)

# Update data
updated = update_data("alerts", {"id": 1}, {"status": "resolved"})

# Delete data
deleted = delete_data("alerts", {"id": 1})
```

### Method 2: Using the client directly

```python
from supabase_client import get_supabase_client

supabase = get_supabase_client()

# Query with filters
response = (
    supabase.table("alerts")
    .select("*")
    .eq("severity", "critical")
    .order("created_at", desc=True)
    .limit(10)
    .execute()
)

alerts = response.data
```

### Method 3: Using in Flask routes

```python
from flask import current_app, jsonify


@app.route("/api/alerts")
def get_alerts():
    supabase = current_app.supabase
    response = supabase.table("alerts").select("*").execute()
    return jsonify(response.data)
```

## 🗄️ Database Setup

### Creating Tables

You can create tables in two ways:

#### 1. Using Supabase Dashboard (Recommended for beginners)
1. Go to **Table Editor** in Supabase dashboard
2. Click **New table**
3. Define your schema

#### 2. Using SQL Editor
```sql
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_status ON alerts(status);
```

### Example Schema for Your SOC Project

```sql
-- Endpoints table
CREATE TABLE endpoints (
    id BIGSERIAL PRIMARY KEY,
    hostname TEXT NOT NULL,
    ip_address TEXT,
    os_type TEXT,
    status TEXT DEFAULT 'active',
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Alerts table
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_name TEXT NOT NULL,
    vendor TEXT,
    severity TEXT NOT NULL,
    reported_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    endpoint_id BIGINT REFERENCES endpoints(id),
    status TEXT DEFAULT 'open',
    assigned_to TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Findings table
CREATE TABLE findings (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL,
    status TEXT DEFAULT 'new',
    alert_id BIGINT REFERENCES alerts(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 🔐 Security Best Practices

1. **Never commit your API keys** to version control
   - The `.env` file is already in `.gitignore`
2. **Use anon/public key for client-side** operations
3. **Use service_role key only on server-side** and keep it secret
4. **Enable Row Level Security (RLS)** in Supabase for production
5. **Set up proper authentication** before deploying

## 📚 Additional Resources

- [Supabase Python Client Docs](https://supabase.com/docs/reference/python/introduction)
- [Supabase Database Guide](https://supabase.com/docs/guides/database)
- [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

## 🆘 Troubleshooting

### Error: "Invalid API key"
- Make sure you copied the complete anon/public key
- The key should be 200+ characters long
- It should start with `eyJhbGci`

### Error: "relation 'table_name' does not exist"
- The table hasn't been created yet
- Create it using Supabase dashboard or SQL editor

### Connection timeout
- Check your internet connection
- Verify the SUPABASE_URL is correct
- Check if Supabase is experiencing downtime

## ✨ Next Steps

1. ✅ Get the correct API key from Supabase dashboard
2. ✅ Update `.env` file with the correct key
3. ✅ Run `python test_supabase_connection.py` to verify
4. ✅ Create your database tables
5. ✅ Start using Supabase in your routes (see `example_supabase_usage.py`)
6. ✅ Run your Flask app: `python app.py`

import streamlit as st
from core.database import DatabaseManager

st.title("Debug Schema Initialization")

# Create database manager
db_manager = DatabaseManager()

# Test connection
st.header("1. Connection Test")
result = db_manager.execute("SELECT 1 as test")
if result:
    st.success(f"✅ Connection works: {result}")
else:
    st.error("❌ Connection failed")

# Get existing tables
st.header("2. Existing Tables")
tables = db_manager.get_existing_tables()
st.write(f"Tables found: {tables}")

required_tables = ['users', 'cvs', 'analyses', 'payments']
for table in required_tables:
    if table in tables:
        st.success(f"✅ {table} exists")
    else:
        st.error(f"❌ {table} missing")

# Test initialize_schema
st.header("3. Initialize Schema Test")
result = db_manager.initialize_schema()
st.write(f"Initialize schema returned: {result}")

# Manual table check
st.header("4. Manual Table Check")
query = """
    SELECT tablename, 
           pg_size_pretty(pg_total_relation_size(quote_ident(tablename)::regclass)) as size,
           (SELECT COUNT(*) FROM pg_indexes WHERE tablename = t.tablename) as index_count
    FROM pg_tables t
    WHERE schemaname = 'public' 
    AND tablename IN ('users', 'cvs', 'analyses', 'payments')
    ORDER BY tablename
"""
result = db_manager.execute(query)
if result:
    for row in result:
        st.write(f"Table: {row['tablename']} | Size: {row['size']} | Indexes: {row['index_count']}")

# Test creating a simple table
st.header("5. Permission Test")
if st.button("Test CREATE permission"):
    test_result = db_manager.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50)
        )
    """, fetch=False)
    
    if test_result is not None:
        st.success("✅ CREATE permission OK")
        # Clean up
        db_manager.execute("DROP TABLE IF EXISTS test_table", fetch=False)
    else:
        st.error("❌ No CREATE permission")

# Show the actual error
st.header("6. Check Console Output")
st.info("Check your terminal/console where you ran 'streamlit run' for detailed error messages")

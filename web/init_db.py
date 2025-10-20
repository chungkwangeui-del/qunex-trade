"""
Initialize the database and create tables
Run this once to set up the database
"""

from app import app, db

with app.app_context():
    # Create all tables
    db.create_all()
    print("✅ Database tables created successfully!")

    # Show all tables
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    print(f"\n📊 Tables in database:")
    for table in tables:
        print(f"  - {table}")
        columns = inspector.get_columns(table)
        for column in columns:
            print(f"    • {column['name']}: {column['type']}")

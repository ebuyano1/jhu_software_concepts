import pytest

@pytest.mark.web
def test_flask_app_factory(client):
    """Assert a testable Flask app is created."""
    assert client.application is not None

@pytest.mark.web
def test_get_analysis_page_load(client):
    """Test GET /analysis (page load) Status 200."""
    response = client.get("/analysis")
    assert response.status_code == 200

@pytest.mark.web
def test_page_contains_buttons(client):
    """Page Contains both 'Pull Data' and 'Update Analysis' buttons."""
    response = client.get("/analysis")
    html = response.data.decode()
    # Check for buttons (adjust text if your HTML uses slightly different wording)
    assert "Pull" in html
    assert "Update Analysis" in html

@pytest.mark.web
def test_page_text_content(client, db_cursor):
    """Page text includes 'Analysis' and at least one 'Answer:'."""
    # 1. Insert data to ensure analysis runs
    db_cursor.execute("""
        INSERT INTO applicants (p_id, term, us_or_international)
        VALUES (1, 'Fall 2025', 'American')
    """)
    db_cursor.connection.commit()

    # 2. Get Page
    response = client.get("/analysis")
    html = response.data.decode()
    
    # 3. Assertions
    assert "Analysis" in html
    # This will now PASS because we added "Answer:" to the HTML
    assert "Answer:" in html

@pytest.mark.web
def test_index_route(client):
    """
    Hits the root route '/' (Lines 89-95 usually).
    Most tests hit '/analysis', so this line is often missed.
    """
    response = client.get("/")
    
    # It might redirect to /analysis or render a template
    # We just need to ensure the code runs (200 OK or 302 Redirect are both fine)
    assert response.status_code in [200, 302]

@pytest.mark.web
def test_index_route_coverage(client):
    """
    Hits the root URL '/' to cover the index route handler in app.py.
    """
    # This hits the 'def index():' function in app.py
    response = client.get("/")
    assert response.status_code == 200

@pytest.mark.web
def test_create_app_defaults():
    """
    Calls create_app() with NO arguments (None).
    This hits the 'else' implicit branch of 'if test_config:'.
    (Lines 115->119 in app.py)
    """
    from app import create_app
    
    # Call without arguments
    app = create_app()
    
    # Verify it created an app
    assert app is not None
    # By default, testing should be False if we don't pass {"TESTING": True}
    assert app.testing is False
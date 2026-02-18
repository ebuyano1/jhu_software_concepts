import pytest
import query_data

@pytest.mark.analysis
def test_query_data_q11_loop(db_cursor):
    """Verifies Q11 formatting loop runs correctly."""
    db_cursor.execute("""
        INSERT INTO applicants (p_id, degree, gre, term) 
        VALUES (99901, 'PhD', 320, 'Fall 2025'), (99902, 'Masters', 310, 'Fall 2025')
    """)
    db_cursor.connection.commit()
    results = query_data.get_analysis()
    q11 = next(r for r in results if r['id'] == 'q11')
    assert "PhD" in q11['answer']
    assert "Masters" in q11['answer']

@pytest.mark.analysis
def test_q3_averages_coverage(db_cursor):
    """
    Inserts a row with valid scores to hit lines 59-60 in query_data.py.
    This forces the 'Average GPA/GRE' logic to run.
    """
    from query_data import get_analysis

    # 1. Insert data with NON-NULL scores
    # We use a high ID (99999) to avoid conflicts
    db_cursor.execute("""
        INSERT INTO applicants (p_id, gpa, gre, gre_v, gre_aw, term, degree, university) 
        VALUES (99999, 4.00, 170, 160, 5.0, 'Fall 2025', 'PhD', 'Test U')
    """)
    db_cursor.connection.commit()

    # 2. Run the analysis
    results = get_analysis()

    # 3. Verify that we got a result containing "GPA:" (Question 3)
    # This confirms lines 59-60 executed successfully.
    # We loop through results to find the specific answer string.
    found_averages = False
    for res in results:
        if "GPA: 4.0" in str(res['answer']):
            found_averages = True
            break
            
    assert found_averages is True
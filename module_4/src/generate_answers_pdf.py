from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from query_data import get_analysis
from datetime import datetime

def draw_wrapped_block(c, text, x, y, max_width, font_name, font_size, line_height):
    """
    Helper function to draw text that automatically wraps to the next line 
    if it exceeds max_width.
    Returns the new Y position after drawing the block.
    """
    c.setFont(font_name, font_size)
    lines = simpleSplit(text, font_name, font_size, max_width)
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
    return y

def generate_pdf():
    filename = "module3_analysis.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Margins and layout settings
    left_margin = 40
    right_margin = 40
    max_width = width - left_margin - right_margin
    start_y = height - 50
    y = start_y
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Module 3: Database Query Analysis")
    y -= 20
    
    c.setFont("Helvetica", 10)
    c.drawString(left_margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 40 # Add some spacing after title

    analysis = get_analysis()

    for item in analysis:
        # Check if we need a new page before starting this block
        # (Estimate ~150 units for a standard question block)
        if y < 150:
            c.showPage()
            y = start_y
        
        # 1. Question (Bold)
        y = draw_wrapped_block(c, f"Q: {item['question']}", left_margin, y, max_width, "Helvetica-Bold", 12, 14)
        y -= 5

        # 2. Answer
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_margin, y, "Answer:")
        # Indent the answer text slightly
        y = draw_wrapped_block(c, str(item['answer']), left_margin + 15, y - 12, max_width - 15, "Helvetica", 10, 12)
        y -= 5

        # 3. Explanation/Logic
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(left_margin, y, "Logic:")
        y = draw_wrapped_block(c, item['explanation'], left_margin + 35, y, max_width - 35, "Helvetica-Oblique", 10, 12)
        y -= 5

        # 4. SQL (Courier Font, Wrapped)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_margin, y, "SQL:")
        # We use a slightly smaller font for code (size 9) and Courier so it looks like code
        y = draw_wrapped_block(c, item['sql'], left_margin, y - 12, max_width, "Courier", 9, 10)
        
        y -= 25  # Space between items

    c.save()
    print(f"PDF generated: {filename}")

if __name__ == "__main__":
    generate_pdf()
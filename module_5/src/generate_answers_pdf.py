"""
Module to generate a PDF report of the Database Query Analysis.
"""
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

from query_data import get_analysis


def draw_wrapped_block(c, text, x, y, **kwargs):
    """
    Helper function to draw text that automatically wraps to the next line.
    Expects kwargs: max_width, font_name, font_size, line_height.
    Returns the new Y position after drawing the block.
    """
    max_width = kwargs.get('max_width', 500)
    font_name = kwargs.get('font_name', 'Helvetica')
    font_size = kwargs.get('font_size', 10)
    line_height = kwargs.get('line_height', 12)

    c.setFont(font_name, font_size)
    lines = simpleSplit(text, font_name, font_size, max_width)
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
    return y


def generate_pdf():
    """
    Fetches analysis data and generates a formatted PDF file.
    """
    filename = "module3_analysis.pdf"
    pdf_canvas = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Margins and layout settings
    left_margin = 40
    right_margin = 40
    max_w = width - left_margin - right_margin
    start_y = height - 50
    curr_y = start_y

    # Title
    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawString(left_margin, curr_y, "Module 3: Database Query Analysis")
    curr_y -= 20

    pdf_canvas.setFont("Helvetica", 10)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf_canvas.drawString(left_margin, curr_y, f"Generated on: {timestamp}")
    curr_y -= 40

    analysis = get_analysis()

    for item in analysis:
        if curr_y < 150:
            pdf_canvas.showPage()
            curr_y = start_y

        # 1. Question (Bold)
        curr_y = draw_wrapped_block(
            pdf_canvas, f"Q: {item['question']}", left_margin, curr_y,
            max_width=max_w, font_name="Helvetica-Bold", font_size=12, line_height=14
        )
        curr_y -= 5

        # 2. Answer
        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawString(left_margin, curr_y, "Answer:")
        curr_y = draw_wrapped_block(
            pdf_canvas, str(item['answer']), left_margin + 15, curr_y - 12,
            max_width=max_w - 15, font_name="Helvetica", font_size=10, line_height=12
        )
        curr_y -= 5

        # 3. Explanation/Logic
        pdf_canvas.setFont("Helvetica-Oblique", 10)
        pdf_canvas.drawString(left_margin, curr_y, "Logic:")
        curr_y = draw_wrapped_block(
            pdf_canvas, item['explanation'], left_margin + 35, curr_y,
            max_width=max_w - 35, font_name="Helvetica-Oblique",
            font_size=10, line_height=12
        )
        curr_y -= 5

        # 4. SQL (Courier Font, Wrapped)
        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawString(left_margin, curr_y, "SQL:")
        curr_y = draw_wrapped_block(
            pdf_canvas, item['sql'], left_margin, curr_y - 12,
            max_width=max_w, font_name="Courier", font_size=9, line_height=10
        )

        curr_y -= 25

    pdf_canvas.save()
    print(f"PDF generated: {filename}")


if __name__ == "__main__":
    generate_pdf()

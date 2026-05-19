import pandas as pd
import matplotlib
matplotlib.use('Agg')       # put this before: import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
import re  # Import regex module for text cleaning
from reportlab.lib.utils import ImageReader
import os
from reportlab.platypus import PageBreak
from reportlab.lib import colors




# PDF File Output
pdf_file = "JARI_PROTAC_Report.pdf"

# Load CSV Data
csv_file = "DeepPK_Cleaned_Output.csv"
df = pd.read_csv(csv_file)

# Clean column names
df.columns = df.columns.str.replace("_", " ")









def add_favicon(canvas, doc):
    """Adds the favicon at the top-right and page numbers (JARI I, JARI II, etc.) at the bottom."""
    
    # Ensure correct absolute path
    favicon_path = os.path.abspath("static/images/favicon.png")

    # Debugging: Print confirmation message
    print(f"🔍 Attempting to add favicon and page number on page {doc.page}.")

    # Check if file exists
    if not os.path.exists(favicon_path):
        print(f"⚠️ Favicon not found at {favicon_path}. Skipping...")
    else:
        try:
            # Set favicon size
            favicon_size = 0.5 * inch  

            # Save the current state of the canvas
            canvas.saveState()

            # Get page dimensions
            page_width, page_height = landscape(letter)

            # Position the favicon in the top-right corner
            x_position = page_width - favicon_size - 15  # Right margin
            y_position = page_height - favicon_size - 15  # Top margin

            # Read and draw the image
            favicon = ImageReader(favicon_path)
            canvas.drawImage(favicon, x_position, y_position, width=favicon_size, height=favicon_size)

            print(f"✅ Successfully added favicon on the page at ({x_position}, {y_position}).")

        except Exception as e:
            print(f"❌ ERROR: Could not add favicon - {e}")

    # 📌 **Step 2: Add Page Numbers in Roman Numerals**
    try:
        # Convert page number to Roman numerals
        roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
                          "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
        page_num = doc.page  # Get current page number
        roman_page = f"JARI {roman_numerals[page_num - 1]}" if page_num <= len(roman_numerals) else f"JARI {page_num}"

        # Positioning at the bottom center
        font_size = 12
        text_x = page_width / 2
        text_y = 20  # Bottom margin

        # Set font and draw the text
        canvas.setFont("Helvetica-Bold", font_size)
        canvas.drawCentredString(text_x, text_y, roman_page)

        print(f"✅ Page number added: {roman_page}")

    except Exception as e:
        print(f"❌ ERROR: Could not add page number - {e}")

    # Restore canvas state
    canvas.restoreState()

def first_page_layout(canvas, doc):
    add_favicon(canvas, doc)  # Your existing function to add favicon and page numbers

    # Assuming svg_image is an Image object and not SVG (since you're loading a PNG)
    svg_image = Image("Protac.png", width=4*inch, height=4*inch)  # Set size when creating the image
    print("Adding Image to First page")

    # Positioning the image on the first page
    page_width, page_height = doc.pagesize  # Get the dimensions of the page
    x_position = doc.width - 5*inch  # Adjust X position as needed
    y_position = doc.height - 2.6*inch  # Adjust Y position as needed

    # Determine the available width and height for the image
    available_width = doc.width - x_position  # You can adjust this calculation as needed
    available_height = doc.height - y_position  # You can adjust this calculation as needed

    # Correct usage of wrapOn
    svg_image.wrapOn(canvas, available_width, available_height)
    svg_image.drawOn(canvas, x=x_position, y=y_position)  # Draw the image at the specified position



# **Fix the second column formatting**
def clean_parameter_name(param):
    """Removes brackets and deletes text before the first '/' in the parameter name."""
    param = re.sub(r"[\[\]]", "", str(param))  # Remove brackets
    return param.split("/", 1)[-1]  # Remove everything before the first '/'

df["Parameter"] = df["Parameter"].apply(clean_parameter_name)

# Group by Category
categories = df["Category"].unique()


def save_pie_chart(values, labels, colors, title, filename, startangle=90):
    plt.figure(figsize=(6, 6))
    numeric_values = [float(value) for value in values]

    if sum(numeric_values) > 0:
        plt.pie(numeric_values, labels=labels, colors=colors, autopct="%1.1f%%", startangle=startangle)
    else:
        plt.text(0.5, 0.5, "No qualifying data", ha="center", va="center", fontsize=12)
        plt.axis("off")

    plt.title(title)
    plt.savefig(filename)
    plt.close()

# Define Colors for Each Category (Header Colors)
category_colors = {
    "Absorption": colors.lightblue,
    "Distribution": colors.lightgreen,
    "Metabolism": colors.purple,
    "Excretion": colors.khaki,
    "Toxicology": colors.red,
    "General Properties": colors.gray
}

# Define Colors for Key Predictions (Only Applies to Last Column)
def get_prediction_color(prediction):
    if "Toxic" in str(prediction):
        return colors.red
    elif "Safe" in str(prediction):
        return colors.green
    elif "Non-Inhibitor" in str(prediction):  # Highlight inhibitors in light yellow
        return colors.whitesmoke
    elif "Non-Penetrable" in str(prediction):  # Highlight inhibitors in light yellow
        return colors.lightgreen
    elif "Non-Substrate" in str(prediction):  # Highlight inhibitors in light yellow
        return colors.whitesmoke
    elif "Substrate" in str(prediction):  # Highlight inhibitors in light yellow
        return colors.springgreen
    elif "Penetrable" in str(prediction):  # Highlight inhibitors in light yellow
        return colors.orangered
    elif "Inhibitor" in str(prediction):  # Highlight inhibitors in light yellow
        return colors.lightyellow
    elif "Half-Life" in str(prediction):  # Highlight inhibitors in light yellow
        return colors.skyblue
    elif "Non-Bioavailable" in str(prediction):
        return colors.orange
    elif "Absorbed" in str(prediction):
        return colors.lightgreen
    else:
        return colors.whitesmoke





########################################################





# Create PDF Document
doc = SimpleDocTemplate(pdf_file, pagesize=landscape(letter))
elements = []
styles = getSampleStyleSheet()

# Build the PDF with an explicit call to add_favicon
doc.build(elements, onFirstPage=first_page_layout, onLaterPages=add_favicon)


# Title
title = Paragraph("<b>Parameter Analysis Report</b>", styles["Title"])
elements.append(title)
elements.append(Spacer(1, 12))

# Summary Section (Now Includes ALL Categories)
summary_text = f"""
<b>Parameter Summary</b><br/>
- Total Data Entries: {len(df)}<br/>
- Absorption Entries: {len(df[df['Category'] == 'Absorption'])}<br/>
- Distribution Entries: {len(df[df['Category'] == 'Distribution'])}<br/>
- Metabolism Entries: {len(df[df['Category'] == 'Metabolism'])}<br/>
- Excretion Entries: {len(df[df['Category'] == 'Excretion'])}<br/>
- Toxicology Entries: {len(df[df['Category'] == 'Toxicology'])}<br/>
- General Properties Entries: {len(df[df['Category'] == 'General Properties'])}<br/>
"""
elements.append(Paragraph(summary_text, styles["Normal"]))
elements.append(Spacer(1, 20))

# Style for wrapping long text
wrap_style = ParagraphStyle(
    name="WrapStyle",
    fontSize=8,
    leading=10,
    alignment=TA_CENTER
)

# Function to wrap text inside a table cell
def wrap_text(text):
    return Paragraph(str(text), wrap_style)

# Function to create a well-structured table for each category
def create_category_table(data, category):
    # Adjust column widths (Category wider, Parameter moderate, Value flexible)
    col_widths = [1.5 * inch, 4 * inch, 3.5 * inch]

    # Convert long text values into wrapped paragraphs
    table_data = [data.columns.tolist()] + [[wrap_text(cell) for cell in row] for row in data.values]

    table = Table(table_data, colWidths=col_widths)

    # Define header color
    header_color = category_colors.get(category, colors.lightgrey)

    # Style table headers (ALL headers bolded now)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),  # Header color per category
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # Larger font for headers
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    # Apply cell formatting (first column centered & bold)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Multi-line text alignment
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Headers stand out
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Bold headers
        ('ALIGN', (0, 0), (-1, 0), 'CENTER')  # Center headers
    ]))

    # Apply value-specific highlighting only to the last column
    for i, row in enumerate(data.values, start=1):
        value_color = get_prediction_color(row[-1])  # Last column only
        table.setStyle([
            ('BACKGROUND', (-1, i), (-1, i), value_color),
            ('TEXTCOLOR', (-1, i), (-1, i), colors.black),
            ('ALIGN', (-1, i), (-1, i), 'CENTER')
        ])

  
    return table





# Add category-wise tables
for category in categories:
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>{category} Data</b>", styles["Heading2"]))

    # Filter data for the category
    subset = df[df["Category"] == category]
    
    # Add category table
    elements.append(create_category_table(subset, category))
    elements.append(Spacer(1, 20))

# Generate a Pie Chart for Category Distribution
category_counts = df["Category"].value_counts()
save_pie_chart(
    category_counts.tolist(),
    category_counts.index.tolist(),
    ['red', 'purple', 'lightblue', 'gray', 'lightgreen', "khaki"][: len(category_counts.index)],
    "Distribution of Categories in Parameter Data",
    "category_distribution.png",
)

# Add chart to PDF
elements.append(Image("category_distribution.png", width=400, height=400))
elements.append(Spacer(1, 20))


# Extract entries that contain 'Toxic' or 'Safe' in the 'Value' column
# safest: coerce to string and treat NaN as empty, regex word boundary
toxic_safe_filter = df['Value'].astype(str).str.contains(r'\b(Toxic|Safe)\b', na=False)

toxic_safe_data = df[toxic_safe_filter]['Value']

# Normalize the entries to just 'Toxic' or 'Safe'
toxic_safe_data = toxic_safe_data.apply(lambda x: 'Toxic' if 'Toxic' in x else 'Safe')

# Count occurrences of 'Toxic' and 'Safe'
toxic_safe_counts = toxic_safe_data.value_counts()

# Define colors for each category explicitly
color_map = {'Toxic': 'red', 'Safe': 'green'}

# Ensure the order of the data for consistent color application
labels = ['Toxic', 'Safe']  # This makes sure the labels are in a specific order
toxic_safe_values = [toxic_safe_counts.get(label, 0) for label in labels]
toxic_safe_colors = [color_map[label] for label in labels]
save_pie_chart(
    toxic_safe_values,
    labels,
    toxic_safe_colors,
    'Distribution of Toxic and Safe Classifications in Values',
    "toxic_safe_distribution.png",
)

# You can add this chart to your PDF similar to the previous chart
elements.append(Image("toxic_safe_distribution.png", width=400, height=400))
elements.append(Spacer(1, 20))
print(f"✅ Pie chart created and saved as 'toxic_safe_distribution.png'")







import pandas as pd
import matplotlib.pyplot as plt

# Load CSV Data
df = pd.read_csv("DeepPK_Cleaned_Output.csv")
df.columns = df.columns.str.replace("_", " ")

def create_metabolism_pie_chart(data_frame, positive_term, negative_term, file_name):
    # Filter data to include only relevant entries from the 'Metabolism' category
    relevant_data = data_frame[data_frame['Category'] == 'Metabolism']
    relevant_data = relevant_data[relevant_data['Value'].str.contains(f"{negative_term}|{positive_term}")]

    # Normalize the entries to prioritize negative terms first
    relevant_data['Normalized'] = relevant_data['Value'].apply(lambda x: negative_term if negative_term in x else positive_term)

    # Count occurrences
    counts = relevant_data['Normalized'].value_counts()

    # Define colors for each category, with custom colors for clarity
    color_map = {
        positive_term: 'lightyellow' if positive_term == 'Inhibitor' else 'springgreen',  # Custom color for inhibitors and substrates
        negative_term: 'whitesmoke'
    }
    colors = [color_map[label] for label in counts.index]

    save_pie_chart(
        counts.tolist(),
        counts.index.tolist(),
        colors,
        f'Distribution of {positive_term} and {negative_term} in Metabolism',
        file_name,
    )

    print(f"✅ Pie chart for {positive_term} and {negative_term} created and saved as '{file_name}'.")

# Generate pie charts for Inhibitors and Substrates using the defined colors
create_metabolism_pie_chart(df, 'Inhibitor', 'Non-Inhibitor', 'metabolism_inhibitor_chart.png')
create_metabolism_pie_chart(df, 'Substrate', 'Non-Substrate', 'metabolism_substrate_chart.png')



# Include these charts in your PDF report similar to other images
elements.append(Image("metabolism_inhibitor_chart.png", width=400, height=400))
elements.append(Spacer(1, 20))
elements.append(Image("metabolism_substrate_chart.png", width=400, height=400))
elements.append(Spacer(1, 20))



print(f"✅ Metabolism charts created and saved as 'metabolism_inhibitor_chart.png' and 'metabolism_substrate_chart.png'")




# Continue building the PDF with the updated content
doc.build(elements, onFirstPage=first_page_layout, onLaterPages=add_favicon)




print(f"✅ PDF report saved as {pdf_file}")

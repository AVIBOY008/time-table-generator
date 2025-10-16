# 📘 SMART CLASSROOM & TIMETABLE SCHEDULER
# ✅ FINAL HACKATHON VERSION (with AI LAB)
# Developed by Dhruva

from ortools.sat.python import cp_model
import pandas as pd
from tabulate import tabulate
import random
import os
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import uuid

# ===== DEFAULT SUBJECTS, FACULTY, LABS =====
days = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]

timeslots = [
    "8:00-8:55", "8:55-9:50", "9:50-10:45",
    "10:45-11:15", # Tea Break
    "11:15-12:10", "12:10-1:05",
    "1:05-2:00",   # Lunch Break
    "2:00-2:55", "2:55-3:50", "3:50-4:45", "4:45-5:40"
]

subjects = {
    "COA": "Ms. Suman M",
    "DBMS": "Ms. Sangeetha S",
    "SDM": "Dr. Chandra Shekar",
    "FDS": "Mr. Pramoda R",
    "AI": "Mr. Suresh Babu P",
    "AI LAB": "Mr. Suresh Babu P",
    "DBMS LAB": "Ms. Sangeetha S",
    "DS LAB": "Ms. Suman M",
    "DAE LAB": "Mr. Pramoda R"
}

def get_user_config():
    """Get configuration from user input"""
    global timeslots, subjects, tea_break, lunch_break
    
    change_slots = input("Do you want to modify timeslots? (y/n): ").lower()
    if change_slots == "y":
        timeslots = []
        n = int(input("Enter number of timeslots per day: "))
        for i in range(n):
            t = input(f"Enter timeslot {i+1}: ")
            timeslots.append(t)
        user_tea_break = input("Enter the timeslot for the tea break (e.g., 10:45-11:15): ")
        user_lunch_break = input("Enter the timeslot for the lunch break (e.g., 1:05-2:00): ")
        tea_break = user_tea_break
        lunch_break = user_lunch_break
    else:
        lunch_break = "1:05-2:00"
        tea_break = "10:45-11:15"

    change_subjects = input("Do you want to modify subjects/faculty? (y/n): ").lower()
    if change_subjects == "y":
        subjects = {}
        n = int(input("Enter number of subjects/labs: "))
        for i in range(n):
            sub = input(f"Enter subject/lab {i+1} name: ")
            fac = input(f"Enter faculty for {sub}: ")
            subjects[sub] = fac

    num_timetables = int(input("How many timetables to generate? (default 5): ") or 5)
    if num_timetables < 5:
        print("Increasing number of timetables to generate to at least 5.")
        num_timetables = 5
    
    return num_timetables

def generate_timetable_api(user_timeslots, user_subjects, user_tea_break, user_lunch_break):
    """Generate timetable with given configuration (for API use)"""
    model = cp_model.CpModel()
    timetable = {}

    lab_subjects = [s for s in user_subjects if "LAB" in s.upper()]

    # Create boolean variables for each possible subject-day-timeslot assignment
    for d in days:
        for t in user_timeslots:
            for s in user_subjects:
                timetable[(d, t, s)] = model.NewBoolVar(f"{d}_{t}_{s}")

    # Constraint: Only one subject per slot
    for d in days:
        for t in user_timeslots:
            model.Add(sum(timetable[(d, t, s)] for s in user_subjects) <= 1)

    # Constraint: Each subject appears a reasonable number of times
    for s in user_subjects:
        if s in lab_subjects:
            model.Add(sum(timetable[(d, t, s)] for d in days for t in user_timeslots) >= 2)
            model.Add(sum(timetable[(d, t, s)] for d in days for t in user_timeslots) <= 4)
        else:
            model.Add(sum(timetable[(d, t, s)] for d in days for t in user_timeslots) >= 3)
            model.Add(sum(timetable[(d, t, s)] for d in days for t in user_timeslots) <= 5)

    # Constraint: Labs occupy two continuous slots
    for d in days:
        for lab in lab_subjects:
            model.Add(sum(timetable[(d, t, lab)] for t in user_timeslots) <= 2)
            
            for i in range(len(user_timeslots) - 1):
                t1, t2 = user_timeslots[i], user_timeslots[i + 1]
                if t2 != user_lunch_break and t2 != user_tea_break:
                    model.AddImplication(timetable[(d, t1, lab)], timetable[(d, t2, lab)])
                    model.AddImplication(timetable[(d, t2, lab)].Not(), timetable[(d, t1, lab)].Not())

    # Constraint: No class during lunch or tea breaks
    for d in days:
        for s in user_subjects:
            if user_lunch_break in user_timeslots:
                model.Add(timetable[(d, user_lunch_break, s)] == 0)
            if user_tea_break in user_timeslots:
                model.Add(timetable[(d, user_tea_break, s)] == 0)

    # Solve model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15
    solver.parameters.random_seed = random.randint(1, 10000)
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result = {}
        for d in days:
            result[d] = []
            for t in user_timeslots:
                cell = ""
                if t == user_lunch_break:
                    cell = "LUNCH BREAK"
                elif t == user_tea_break:
                    cell = "TEA BREAK"
                else:
                    for s in user_subjects:
                        if solver.Value(timetable[(d, t, s)]) == 1:
                            cell = f"{s}"
                result[d].append(cell)
        return result
    else:
        return None

def generate_professional_pdf(timetable, timeslots, session_id, filename="timetable.pdf"):
    """Generate clean PDF timetable with only timetable and faculty info"""
    try:
        # Ensure the session directory exists
        session_folder = os.path.join("timetables_pdf", session_id)
        if not os.path.exists(session_folder):
            os.makedirs(session_folder)
        
        # Create the PDF document - using landscape for the wide table
        pdf_path = os.path.join(session_folder, filename)
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            topMargin=0.4*inch,
            bottomMargin=0.4*inch,
            leftMargin=0.3*inch,
            rightMargin=0.3*inch
        )
        
        # Create styles
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Normal'],
            fontSize=14,
            alignment=1,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        # Faculty style
        faculty_style = ParagraphStyle(
            'FacultyStyle',
            parent=styles['Normal'],
            fontSize=9,
            alignment=0,
            spaceAfter=3,
            fontName='Helvetica'
        )
        
        elements = []
        
        # Add simple title
        elements.append(Paragraph("CLASS TIMETABLE - 3RD SEM", title_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # Create single continuous table data
        table_data = []
        
        # Header row with all timeslots
        header_row = ["DAY"] + timeslots
        table_data.append(header_row)
        
        # Data rows for each day
        for day in days:
            row = [day]
            for i, slot in enumerate(timeslots):
                if day in timetable and i < len(timetable[day]):
                    cell_content = timetable[day][i]
                    # Handle empty cells
                    if not cell_content:
                        row.append("")
                    else:
                        row.append(cell_content)
                else:
                    row.append("")
            table_data.append(row)
        
        # Calculate column widths - first column for days, rest for timeslots
        page_width = 10.5 * inch  # Landscape A4 width minus margins
        first_col_width = 0.7 * inch
        timeslot_col_width = (page_width - first_col_width) / len(timeslots)
        
        # Create single continuous table
        timetable_table = Table(table_data, 
                               colWidths=[first_col_width] + [timeslot_col_width] * len(timeslots),
                               repeatRows=1)
        
        # Create table style
        table_style = TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Day column
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#ECF0F1')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (0, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('VALIGN', (0, 1), (0, -1), 'MIDDLE'),
            
            # Data cells
            ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (1, 1), (-1, -1), 8),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (1, 1), (-1, -1), 'MIDDLE'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black),
        ])
        
        # Apply special BLUE formatting for break cells
        tea_break_index = timeslots.index("10:45-11:15") + 1 if "10:45-11:15" in timeslots else -1
        lunch_break_index = timeslots.index("1:05-2:00") + 1 if "1:05-2:00" in timeslots else -1
        
        # Light blue for tea break
        if tea_break_index > 0:
            table_style.add('BACKGROUND', (tea_break_index, 0), (tea_break_index, -1), colors.HexColor('#E6F3FF'))
            table_style.add('FONTNAME', (tea_break_index, 1), (tea_break_index, -1), 'Helvetica-Bold')
            table_style.add('TEXTCOLOR', (tea_break_index, 0), (tea_break_index, 0), colors.HexColor('#1A5276'))
        
        # Medium blue for lunch break
        if lunch_break_index > 0:
            table_style.add('BACKGROUND', (lunch_break_index, 0), (lunch_break_index, -1), colors.HexColor('#D6EAF8'))
            table_style.add('FONTNAME', (lunch_break_index, 1), (lunch_break_index, -1), 'Helvetica-Bold')
            table_style.add('TEXTCOLOR', (lunch_break_index, 0), (lunch_break_index, 0), colors.HexColor('#1A5276'))
        
        # Apply the style
        timetable_table.setStyle(table_style)
        
        elements.append(timetable_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Add faculty information section
        faculty_header_style = ParagraphStyle(
            'FacultyHeaderStyle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=0,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        )
        
        elements.append(Paragraph("FACULTY & SUBJECTS:", faculty_header_style))
        
        # Add faculty information in a clean format
        faculty_info = [
            "COA (Computer Organization & Architecture) - Ms. Suman M",
            "DBMS (Database Management Systems) - Ms. Sangeetha S", 
            "SDM (Statistics & Discrete Mathematics) - Dr. Chandra Shekar",
            "FDS (Foundations of Data Science) - Mr. Pramoda R",
            "AI (Introduction to AI) - Mr. Suresh Babu P",
            "AI LAB - Mr. Suresh Babu P",
            "DBMS LAB - Ms. Sangeetha S", 
            "DS LAB - Ms. Suman M",
            "DAE LAB - Mr. Pramoda R"
        ]
        
        for info in faculty_info:
            elements.append(Paragraph(info, faculty_style))
        
        # Build the PDF
        doc.build(elements)
        
        print(f"✅ Clean PDF saved as: {pdf_path}")
        return filename
        
    except Exception as e:
        print(f"❌ Error generating clean PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_multiple_timetables_api(data, session_id=None):
    """API-friendly function to generate multiple timetables"""
    user_timeslots = data.get('timeslots', timeslots)
    user_subjects = data.get('subjects', subjects)
    user_tea_break = data.get('tea_break', "10:45-11:15")
    user_lunch_break = data.get('lunch_break', "1:05-2:00")
    num_timetables = data.get('num_timetables', 5)

    # Generate session ID if not provided
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    timetables = []
    lab_subjects = [s for s in user_subjects if "LAB" in s.upper()]
    
    for attempt in range(num_timetables + 5):
        if len(timetables) >= num_timetables:
            break
            
        result = generate_timetable_api(user_timeslots, user_subjects, user_tea_break, user_lunch_break)
        if result:
            timetables.append(result)
    
    # Generate PDFs for all timetables
    pdf_files = []
    for i, timetable in enumerate(timetables):
        pdf_filename = generate_professional_pdf(timetable, user_timeslots, session_id, f"timetable_{i+1}.pdf")
        if pdf_filename:
            pdf_files.append(pdf_filename)
    
    return {
        'timetables': timetables,
        'pdf_files': pdf_files,
        'session_id': session_id
    }

def run_interactive_mode():
    """Run the interactive timetable generator (only when file is executed directly)"""
    print("🔧 SMART TIMETABLE CONFIGURATION\n")
    num_timetables = get_user_config()
    
    # Use the interactive configuration
    lab_subjects = [s for s in subjects if "LAB" in s.upper()]
    
    print("\n✅ Configuration loaded successfully!\n")
    
    # Generate timetables using interactive config
    timetables = []
    for attempt in range(num_timetables + 5):
        if len(timetables) >= num_timetables:
            break
            
        result = generate_timetable_api(timeslots, subjects, tea_break, lunch_break)
        if result:
            timetables.append(result)
    
    # Display results and generate PDFs
    if timetables:
        for idx, t in enumerate(timetables, start=1):
            print(f"\n🧩 TIMETABLE VERSION {idx}\n")
            
            # Display in horizontal format in console too
            display_data = {}
            for day in days:
                display_data[day] = t[day]
            
            df = pd.DataFrame(display_data, index=timeslots)
            print(tabulate(df, headers='keys', tablefmt='fancy_grid', stralign='center'))
            
            # Generate PDF for each timetable
            generate_professional_pdf(t, timeslots, "interactive", f"timetable_{idx}.pdf")
        
        print(f"\n✅ Total feasible timetables generated: {len(timetables)}")
        print(f"📄 PDF files saved in 'timetables_pdf/interactive' folder")
    else:
        print("❌ No feasible timetables generated!")

# Only run the interactive part if this file is executed directly
if __name__ == "__main__":
    run_interactive_mode()



# Utility functions for reports and data export

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta
from flask import current_app
from models import Session, Product, Room, RoomCategory
from sqlalchemy import func
import io
import tempfile
import os


def generate_daily_report_data(date, admin_user_id):
    """Generate daily report data for a specific date"""
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # Session data for the day - filter by room admin_user_id since Session doesn't have this field
    from sqlalchemy.orm import join
    sessions = Session.query.join(Room).filter(
        Room.admin_user_id == admin_user_id,
        func.date(Session.start_time) == date
    ).all()
    
    # Revenue calculations
    total_session_revenue = sum([s.cost or 0 for s in sessions])
    total_product_revenue = sum([s.product_total or 0 for s in sessions])
    total_revenue = total_session_revenue + total_product_revenue
    
    # Room statistics
    room_stats = {}
    for session in sessions:
        room_name = session.room.name if session.room else 'Unknown'
        if room_name not in room_stats:
            room_stats[room_name] = {
                'sessions': 0,
                'revenue': 0,
                'duration': 0
            }
        room_stats[room_name]['sessions'] += 1
        room_stats[room_name]['revenue'] += (session.cost or 0)
        if session.end_time:
            duration = (session.end_time - session.start_time).total_seconds() / 60  # minutes
            room_stats[room_name]['duration'] += duration
    
    # Product statistics
    product_stats = {}
    from models import CartItem
    cart_items = CartItem.query.join(Session).join(Room).filter(
        Room.admin_user_id == admin_user_id,
        func.date(Session.start_time) == date
    ).all()
    
    for item in cart_items:
        product_name = item.product.name if item.product else 'Unknown'
        if product_name not in product_stats:
            product_stats[product_name] = {
                'quantity': 0,
                'revenue': 0
            }
        product_stats[product_name]['quantity'] += item.quantity
        product_stats[product_name]['revenue'] += item.product.price * item.quantity
    
    return {
        'date': date,
        'total_sessions': len(sessions),
        'total_revenue': total_revenue,
        'session_revenue': total_session_revenue,
        'product_revenue': total_product_revenue,
        'room_stats': room_stats,
        'product_stats': product_stats,
        'sessions': sessions
    }


def generate_pdf_report(report_data, report_type='daily', gaming_center_name='Gaming Center'):
    """Generate PDF report from report data"""
    
    # Create a BytesIO buffer
    buffer = io.BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.darkblue,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.darkblue
    )
    
    # Build story
    story = []
    
    # Title
    title_text = f"{gaming_center_name} - {report_type.title()} Report"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 12))
    
    # Date
    date_text = f"Report Date: {report_data['date']}"
    story.append(Paragraph(date_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Summary Statistics
    story.append(Paragraph("Summary Statistics", heading_style))
    summary_data = [
        ['Metric', 'Value'],
        ['Total Sessions', str(report_data['total_sessions'])],
        ['Total Revenue', f"{report_data['total_revenue']:,.0f} som"],
        ['Session Revenue', f"{report_data['session_revenue']:,.0f} som"],
        ['Product Revenue', f"{report_data['product_revenue']:,.0f} som"],
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Room Statistics
    if report_data['room_stats']:
        story.append(Paragraph("Room Statistics", heading_style))
        room_data = [['Room Name', 'Sessions', 'Revenue (som)', 'Total Duration (min)']]
        for room, stats in report_data['room_stats'].items():
            room_data.append([
                room,
                str(stats['sessions']),
                f"{stats['revenue']:,.0f}",
                f"{stats['duration']:.0f}"
            ])
        
        room_table = Table(room_data)
        room_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(room_table)
        story.append(Spacer(1, 20))
    
    # Product Sales Statistics
    if report_data['product_stats']:
        story.append(Paragraph("Product Sales Statistics", heading_style))
        product_data = [['Product Name', 'Quantity Sold', 'Revenue (som)']]
        for product, stats in report_data['product_stats'].items():
            product_data.append([
                product,
                str(stats['quantity']),
                f"{stats['revenue']:,.0f}"
            ])
        
        product_table = Table(product_data)
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(product_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer


def export_products_to_excel(products, gaming_center_name):
    """Export products list to Excel format"""
    buffer = io.BytesIO()
    
    # Create DataFrame
    product_data = []
    for product in products:
        product_data.append({
            'Name': product.name,
            'Category': product.product_category.name if product.product_category else 'N/A',
            'Price': product.price,
            'Stock Quantity': product.stock_quantity,
            'Unit': product.unit,
            'Min Stock Alert': product.min_stock_alert,
            'Status': 'Active' if product.is_active else 'Inactive'
        })
    
    df = pd.DataFrame(product_data)
    
    # Write to Excel
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Products', index=False)
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Products']
        
        # Add header formatting
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write headers with formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
    
    buffer.seek(0)
    return buffer


def import_products_from_excel(file_content, admin_user_id):
    """Import products from Excel file content"""
    from models import Product, ProductCategory
    from app import db
    
    try:
        # Create a BytesIO buffer from the file content
        buffer = io.BytesIO(file_content)
        
        # Read Excel file
        df = pd.read_excel(buffer)
        
        # Expected columns
        expected_columns = ['Name', 'Category', 'Price', 'Stock Quantity', 'Unit']
        
        # Check if required columns exist
        missing_columns = []
        for col in expected_columns:
            if col not in df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            return False, f"Excel faylida kerakli ustunlar yo'q: {', '.join(missing_columns)}"
        
        imported_count = 0
        updated_count = 0
        
        for index, row in df.iterrows():
            try:
                # Check if category exists, create if not
                category_name = str(row['Category']).strip()
                category = ProductCategory.query.filter_by(
                    name=category_name, 
                    admin_user_id=admin_user_id
                ).first()
                
                if not category:
                    category = ProductCategory(
                        name=category_name,
                        admin_user_id=admin_user_id,
                        is_active=True
                    )
                    db.session.add(category)
                    db.session.flush()  # To get the ID
                
                # Check if product already exists
                product_name = str(row['Name']).strip()
                existing_product = Product.query.filter_by(
                    name=product_name,
                    admin_user_id=admin_user_id
                ).first()
                
                if existing_product:
                    # Update existing product
                    existing_product.price = float(row['Price'])
                    existing_product.stock_quantity = int(row.get('Stock Quantity', 0))
                    existing_product.unit = str(row.get('Unit', 'dona'))
                    existing_product.category_id = category.id
                    updated_count += 1
                else:
                    # Create new product
                    new_product = Product(
                        name=product_name,
                        price=float(row['Price']),
                        stock_quantity=int(row.get('Stock Quantity', 0)),
                        unit=str(row.get('Unit', 'dona')),
                        min_stock_alert=int(row.get('Min Stock Alert', 5)),
                        category_id=category.id,
                        admin_user_id=admin_user_id,
                        is_active=True
                    )
                    db.session.add(new_product)
                    imported_count += 1
                    
            except Exception as e:
                # Skip invalid rows
                continue
        
        db.session.commit()
        
        if imported_count > 0 and updated_count > 0:
            message = f"{imported_count} ta yangi mahsulot qo'shildi, {updated_count} ta mahsulot yangilandi!"
        elif imported_count > 0:
            message = f"{imported_count} ta yangi mahsulot import qilindi!"
        elif updated_count > 0:
            message = f"{updated_count} ta mahsulot yangilandi!"
        else:
            message = "Hech qanday mahsulot import qilinmadi!"
        
        return True, message
        
    except Exception as e:
        return False, f"Import jarayonida xatolik: {str(e)}"


def generate_excel_report(report_data, report_type='daily', gaming_center_name='Gaming Center'):
    """Generate Excel report from report data"""
    
    # Create a BytesIO buffer
    buffer = io.BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Summary Sheet
        summary_data = {
            'Metric': ['Total Sessions', 'Total Revenue', 'Session Revenue', 'Product Revenue'],
            'Value': [
                report_data['total_sessions'],
                f"{report_data['total_revenue']:,.0f} som",
                f"{report_data['session_revenue']:,.0f} som",
                f"{report_data['product_revenue']:,.0f} som"
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        worksheet = writer.sheets['Summary']
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 20)
        
        # Room Statistics Sheet
        if report_data['room_stats']:
            room_data = []
            for room, stats in report_data['room_stats'].items():
                room_data.append({
                    'Room Name': room,
                    'Sessions': stats['sessions'],
                    'Revenue (som)': stats['revenue'],
                    'Duration (min)': f"{stats['duration']:.0f}"
                })
            
            room_df = pd.DataFrame(room_data)
            room_df.to_excel(writer, sheet_name='Room Statistics', index=False)
            
            # Format room statistics sheet
            worksheet = writer.sheets['Room Statistics']
            worksheet.set_column('A:A', 20)
            worksheet.set_column('B:B', 10)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 15)
        
        # Product Sales Sheet
        if report_data['product_stats']:
            product_data = []
            for product, stats in report_data['product_stats'].items():
                product_data.append({
                    'Product Name': product,
                    'Quantity Sold': stats['quantity'],
                    'Revenue (som)': stats['revenue']
                })
            
            product_df = pd.DataFrame(product_data)
            product_df.to_excel(writer, sheet_name='Product Sales', index=False)
            
            # Format product sales sheet
            worksheet = writer.sheets['Product Sales']
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 15)
    
    buffer.seek(0)
    return buffer


def export_products_to_excel(products, gaming_center_name='Gaming Center'):
    """Export products list to Excel format"""
    buffer = io.BytesIO()
    
    # Prepare data
    product_data = []
    for product in products:
        category_name = product.product_category.name if product.product_category else 'No Category'
        product_data.append({
            'Product Name': product.name,
            'Category': category_name,
            'Price (som)': product.price,
            'Unit': product.unit,
            'Stock Quantity': product.stock_quantity,
            'Min Stock Alert': product.min_stock_alert,
            'Stock Status': product.get_stock_status(),
            'Active': 'Yes' if product.is_active else 'No'
        })
    
    # Create DataFrame
    df = pd.DataFrame(product_data)
    
    # Create Excel writer
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Products', index=False)
        
        # Format worksheet
        worksheet = writer.sheets['Products']
        worksheet.set_column('A:A', 25)  # Product Name
        worksheet.set_column('B:B', 15)  # Category
        worksheet.set_column('C:C', 12)  # Price
        worksheet.set_column('D:D', 10)  # Unit
        worksheet.set_column('E:E', 12)  # Stock Quantity
        worksheet.set_column('F:F', 12)  # Min Stock Alert
        worksheet.set_column('G:G', 12)  # Stock Status
        worksheet.set_column('H:H', 8)   # Active
    
    buffer.seek(0)
    return buffer


def import_products_from_excel(file_content, admin_user_id):
    """Import products from Excel file"""
    try:
        # Read Excel file
        df = pd.read_excel(io.BytesIO(file_content))
        
        # Expected columns
        required_columns = ['Product Name', 'Category', 'Price (som)', 'Unit', 'Stock Quantity', 'Min Stock Alert']
        
        # Validate columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Process each row
        imported_count = 0
        errors = []
        
        from models import ProductCategory, Product
        from app import db
        
        for index, row in df.iterrows():
            try:
                # Get or create category
                category_name = str(row['Category']).strip()
                category = ProductCategory.query.filter_by(
                    name=category_name,
                    admin_user_id=admin_user_id
                ).first()
                
                if not category:
                    category = ProductCategory(
                        name=category_name,
                        admin_user_id=admin_user_id
                    )
                    db.session.add(category)
                    db.session.flush()  # Get the ID
                
                # Create product
                product = Product(
                    name=str(row['Product Name']).strip(),
                    category_id=category.id,
                    admin_user_id=admin_user_id,
                    price=float(row['Price (som)']),
                    unit=str(row['Unit']).strip(),
                    stock_quantity=int(row['Stock Quantity']),
                    min_stock_alert=int(row['Min Stock Alert'])
                )
                
                db.session.add(product)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
        
        db.session.commit()
        
        if errors:
            return True, f"Imported {imported_count} products with {len(errors)} errors: {'; '.join(errors[:3])}"
        else:
            return True, f"Successfully imported {imported_count} products"
            
    except Exception as e:
        return False, f"Error processing Excel file: {str(e)}"
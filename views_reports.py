from collections import Counter
from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
from flask import flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app import app, db, get_tashkent_time, utc_to_tashkent
from models import CartItem, Product, ProductCategory, Room, RoomCategory, Session
from route_helpers import (
    build_plan_usage,
    generate_ai_report_insights,
    get_plan_catalog,
    get_plan_config,
    utc_range_for_tashkent_date,
    utc_range_for_tashkent_dates,
    utc_range_for_tashkent_month,
)
from translations import t

try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    UNICODE_FONT = 'DejaVuSans'
    UNICODE_FONT_BOLD = 'DejaVuSans-Bold'
except Exception:
    UNICODE_FONT = 'Helvetica'
    UNICODE_FONT_BOLD = 'Helvetica-Bold'


@app.route('/analytics')
@login_required
def analytics():
    def load_sessions(start_utc, end_utc):
        return (
            Session.query.join(Room)
            .filter(
                Room.admin_user_id == current_user.id,
                Session.is_active == False,
                Session.created_at >= start_utc,
                Session.created_at < end_utc,
            )
            .options(
                selectinload(Session.room),
                selectinload(Session.cart_items).selectinload(CartItem.product),
            )
            .all()
        )

    report_type = request.args.get('type', 'monthly')
    selected_date = request.args.get('date')
    selected_week_date = request.args.get('week_date')
    selected_month = request.args.get('month')

    today = get_tashkent_time().date()
    current_date = today.strftime('%Y-%m-%d')
    current_month = today.strftime('%Y-%m')
    current_week_date = selected_week_date or current_date

    selected_period_days = 30
    period_label = "Tanlangan davr"
    report_sessions_source = []

    if report_type == 'daily':
        if selected_date:
            try:
                target_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            except ValueError:
                target_date = today
        else:
            target_date = today

        day_start_utc, day_end_utc = utc_range_for_tashkent_date(target_date)
        report_sessions_source = load_sessions(day_start_utc, day_end_utc)
        main_revenue = sum(session.total_price for session in report_sessions_source)
        main_sessions = len(report_sessions_source)
        main_title = f"Kunlik Hisobot - {target_date.strftime('%d.%m.%Y')}"
        session_revenue = sum(session.session_price for session in report_sessions_source)
        products_revenue = sum(session.products_total for session in report_sessions_source)
        selected_period_days = 1
        period_label = target_date.strftime('%d.%m.%Y')
        current_date = target_date.strftime('%Y-%m-%d')
    elif report_type == 'weekly':
        if selected_week_date:
            try:
                base_date = datetime.strptime(selected_week_date, '%Y-%m-%d').date()
            except ValueError:
                base_date = today
        else:
            base_date = today

        week_start = base_date - timedelta(days=base_date.weekday())
        week_end = week_start + timedelta(days=6)
        week_start_utc, week_end_utc = utc_range_for_tashkent_dates(week_start, week_end)
        report_sessions_source = load_sessions(week_start_utc, week_end_utc)
        main_revenue = sum(session.total_price for session in report_sessions_source)
        main_sessions = len(report_sessions_source)
        main_title = f"Haftalik Hisobot - {week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')}"
        session_revenue = sum(session.session_price for session in report_sessions_source)
        products_revenue = sum(session.products_total for session in report_sessions_source)
        selected_period_days = 7
        period_label = f"{week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')}"
        current_week_date = base_date.strftime('%Y-%m-%d')
    else:
        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
            except (ValueError, AttributeError):
                year, month = today.year, today.month
        else:
            year, month = today.year, today.month

        month_start_utc, month_end_utc = utc_range_for_tashkent_month(year, month)
        report_sessions_source = load_sessions(month_start_utc, month_end_utc)
        main_revenue = sum(session.total_price for session in report_sessions_source)
        main_sessions = len(report_sessions_source)
        month_names = ['', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr']
        main_title = f"Oylik Hisobot - {month_names[month]} {year}"
        session_revenue = sum(session.session_price for session in report_sessions_source)
        products_revenue = sum(session.products_total for session in report_sessions_source)
        selected_period_days = max((month_end_utc - month_start_utc).days, 1)
        period_label = f"{month_names[month]} {year}"
        current_month = f"{year:04d}-{month:02d}"

    today_start_utc, today_end_utc = utc_range_for_tashkent_date(today)
    today_sessions = load_sessions(today_start_utc, today_end_utc)
    today_revenue = sum(session.total_price for session in today_sessions)

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_start_utc, week_end_utc = utc_range_for_tashkent_dates(week_start, week_end)
    weekly_sessions = load_sessions(week_start_utc, week_end_utc)
    weekly_revenue = sum(session.total_price for session in weekly_sessions)

    report_sessions = sorted(report_sessions_source, key=lambda x: x.created_at, reverse=True)[:50]
    sales_source = report_sessions_source

    product_sales = Counter()
    for sess in sales_source:
        for item in sess.cart_items:
            if item.product:
                product_sales[item.product.name] += item.quantity
    top_products = product_sales.most_common(10)

    room_stats = {}
    for sess in sales_source:
        room_name = sess.room.name if sess.room else 'Noma\'lum'
        if room_name not in room_stats:
            room_stats[room_name] = {'count': 0, 'revenue': 0}
        room_stats[room_name]['count'] += 1
        room_stats[room_name]['revenue'] += sess.total_price
    top_rooms = sorted(room_stats.items(), key=lambda x: x[1]['revenue'], reverse=True)[:10]

    plan_details = get_plan_config(current_user)
    total_products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    total_categories = ProductCategory.query.filter_by(admin_user_id=current_user.id, is_active=True).count()
    inventory_products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    plan_usage = build_plan_usage(plan_details, total_products, total_categories)
    ai_insights = generate_ai_report_insights(
        plan_details=plan_details,
        report_sessions=sales_source,
        total_revenue=main_revenue,
        session_revenue=session_revenue,
        products_revenue=products_revenue,
        top_products=top_products,
        top_rooms=top_rooms,
        inventory_products=inventory_products,
        plan_usage=plan_usage,
        period_label=period_label,
    )

    session_percent = (session_revenue / main_revenue * 100) if main_revenue else 0
    products_percent = (products_revenue / main_revenue * 100) if main_revenue else 0
    avg_session_value = (main_revenue / main_sessions) if main_sessions else 0
    daily_average_revenue = main_revenue / selected_period_days if selected_period_days else 0
    sessions_per_day = main_sessions / selected_period_days if selected_period_days else 0

    return render_template(
        'analytics.html',
        report_type=report_type,
        current_date=current_date,
        current_month=current_month,
        current_week_date=current_week_date,
        main_revenue=main_revenue,
        main_sessions=main_sessions,
        main_title=main_title,
        daily_revenue=today_revenue,
        daily_sessions=len(today_sessions),
        weekly_revenue=weekly_revenue,
        weekly_sessions=len(weekly_sessions),
        session_revenue=session_revenue,
        products_revenue=products_revenue,
        session_percent=session_percent,
        products_percent=products_percent,
        avg_session_value=avg_session_value,
        daily_average_revenue=daily_average_revenue,
        sessions_per_day=sessions_per_day,
        selected_period_days=selected_period_days,
        report_sessions=report_sessions,
        top_products=top_products,
        top_rooms=top_rooms,
        plan_details=plan_details,
        plan_catalog=get_plan_catalog(),
        plan_usage=plan_usage,
        ai_insights=ai_insights,
    )


@app.route('/analytics/cleanup-deleted', methods=['POST'])
@login_required
def analytics_cleanup_deleted():
    inactive_room_ids = [r.id for r in Room.query.filter_by(admin_user_id=current_user.id, is_active=False).all()]
    if not inactive_room_ids:
        flash(t('analytics_cleanup_none'), 'info')
        return redirect(url_for('analytics'))

    sessions_to_delete = Session.query.filter(Session.room_id.in_(inactive_room_ids)).all()
    if not sessions_to_delete:
        flash(t('analytics_cleanup_none'), 'info')
        return redirect(url_for('analytics'))

    session_ids = [s.id for s in sessions_to_delete]
    CartItem.query.filter(CartItem.session_id.in_(session_ids)).delete(synchronize_session=False)
    Session.query.filter(Session.id.in_(session_ids)).delete(synchronize_session=False)
    db.session.commit()
    flash(t('analytics_cleanup_done'), 'success')
    return redirect(url_for('analytics'))


@app.route('/products/export-excel')
@login_required
def export_products_excel():
    products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    data = []
    for product in products:
        data.append({
            'Nomi': product.name,
            'Kategoriya': product.product_category.name if product.product_category else 'Kategoriyasiz',
            'Narxi (som)': product.price,
            'Zaxira miqdori': product.stock_quantity or 0,
            'Minimum zaxira': product.min_stock_alert or 0,
            'Holati': product.get_stock_status_text() if hasattr(product, 'get_stock_status_text') else 'Mavjud',
            'Yaratilgan sana': product.created_at.strftime('%Y-%m-%d') if product.created_at else ''
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Mahsulotlar', index=False)
    except Exception as e:
        flash(f'Excel yaratishda xatolik: {str(e)}', 'danger')
        return redirect(url_for('products'))

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'mahsulotlar_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


@app.route('/products/import-excel', methods=['POST'])
@login_required
def import_products_excel():
    if 'file' not in request.files:
        flash('Fayl tanlanmagan!', 'danger')
        return redirect(url_for('products'))

    file = request.files['file']
    if file.filename == '':
        flash('Fayl tanlanmagan!', 'danger')
        return redirect(url_for('products'))

    if not file.filename or not file.filename.endswith('.xlsx'):
        flash('Faqat .xlsx formatidagi fayllar qabul qilinadi!', 'danger')
        return redirect(url_for('products'))

    try:
        df = pd.read_excel(file, sheet_name=0)
        required_columns = ['Nomi', 'Kategoriya', 'Narxi (som)']
        for col in required_columns:
            if col not in df.columns:
                flash(f'Kerakli ustun topilmadi: {col}', 'danger')
                return redirect(url_for('products'))

        imported_count = 0
        for _, row in df.iterrows():
            existing_product = Product.query.filter_by(
                admin_user_id=current_user.id,
                name=row['Nomi'],
                is_active=True
            ).first()

            if existing_product:
                continue

            category_name = str(row['Kategoriya'])
            category = ProductCategory.query.filter_by(
                admin_user_id=current_user.id,
                name=category_name
            ).first()
            if not category:
                category = ProductCategory()
                category.name = category_name
                category.admin_user_id = current_user.id
                db.session.add(category)
                db.session.flush()

            product = Product()
            product.admin_user_id = current_user.id
            product.name = str(row['Nomi'])
            product.category_id = category.id
            try:
                product.price = float(row['Narxi (som)']) if pd.notna(row['Narxi (som)']) else 0.0
            except (ValueError, TypeError):
                product.price = 0.0

            try:
                stock_val = row.get('Zaxira miqdori', 0)
                product.stock_quantity = int(stock_val) if pd.notna(stock_val) and str(stock_val).strip() != '' else 0
            except (ValueError, TypeError):
                product.stock_quantity = 0

            try:
                min_stock_val = row.get('Minimum zaxira', 0)
                product.min_stock_alert = int(min_stock_val) if pd.notna(min_stock_val) and str(min_stock_val).strip() != '' else 0
            except (ValueError, TypeError):
                product.min_stock_alert = 0

            db.session.add(product)
            imported_count += 1

        db.session.commit()
        flash(f'{imported_count} ta mahsulot muvaffaqiyatli import qilindi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Import paytida xatolik: {str(e)}', 'danger')

    return redirect(url_for('products'))


@app.route('/reports/pdf/<report_type>')
@login_required
def generate_pdf_report(report_type):
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        flash(t('pdf_select_date_range'), 'danger')
        return redirect(url_for('analytics'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash(t('pdf_invalid_date'), 'danger')
        return redirect(url_for('analytics'))

    user_room_ids = [room.id for room in Room.query.filter_by(admin_user_id=current_user.id).all()]
    range_start_utc, range_end_utc = utc_range_for_tashkent_dates(start_date, end_date)
    sessions = Session.query.filter(
        Session.room_id.in_(user_room_ids),
        Session.created_at >= range_start_utc,
        Session.created_at < range_end_utc,
        Session.is_active == False
    ).all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []
    pdf_primary = colors.HexColor("#4f86e6")
    pdf_text = colors.HexColor("#1b2b45")
    pdf_light = colors.HexColor("#f2f6ff")
    pdf_lighter = colors.HexColor("#e7eefc")
    pdf_grid = colors.HexColor("#c7d3ea")

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontName=UNICODE_FONT_BOLD, fontSize=18, textColor=pdf_primary, alignment=1, spaceAfter=30)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontName=UNICODE_FONT, fontSize=10, textColor=pdf_text)
    heading2_style = ParagraphStyle('CustomHeading2', parent=styles['Heading2'], fontName=UNICODE_FONT_BOLD, fontSize=13, textColor=pdf_text, spaceBefore=8, spaceAfter=6)

    report_titles = {
        'daily': t('pdf_daily_report'),
        'weekly': t('pdf_weekly_report'),
        'monthly': t('pdf_monthly_report')
    }

    title = f"{current_user.gaming_center_name}\n{report_titles.get(report_type, t('pdf_report_title'))}"
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"{t('pdf_date_range')}: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}", normal_style))
    elements.append(Spacer(1, 20))

    currency = t('currency')
    total_revenue = sum(session.total_price for session in sessions)
    total_sessions = len(sessions)
    stats_data = [
        [t('pdf_total_sessions'), str(total_sessions)],
        [t('pdf_total_revenue'), f"{total_revenue:,.0f} {currency}"],
        [t('pdf_avg_session'), f"{total_revenue/total_sessions if total_sessions > 0 else 0:,.0f} {currency}"]
    ]

    stats_table = Table(stats_data, colWidths=[3.2 * inch, 2.8 * inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), pdf_light),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), UNICODE_FONT_BOLD),
        ('FONTNAME', (1, 0), (1, -1), UNICODE_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), pdf_text),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, pdf_grid),
        ('BOX', (0, 0), (-1, -1), 1, pdf_grid)
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 30))

    if sessions:
        elements.append(Paragraph(f"{t('pdf_sessions_list')}:", heading2_style))
        elements.append(Spacer(1, 12))
        session_data = [[t('pdf_room'), t('pdf_date'), t('pdf_time'), t('pdf_duration'), f"{t('pdf_amount')} ({currency})"]]
        for session in sessions[:50]:
            session_data.append([
                session.room.name,
                utc_to_tashkent(session.created_at).strftime('%d.%m.%Y'),
                utc_to_tashkent(session.start_time).strftime('%H:%M') if session.start_time else 'N/A',
                session.get_formatted_duration(),
                f"{session.total_price:,.0f}"
            ])

        session_table = Table(session_data, colWidths=[1.6 * inch, 0.95 * inch, 0.75 * inch, 1.25 * inch, 1.05 * inch])
        session_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), pdf_primary),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), UNICODE_FONT),
            ('FONTNAME', (0, 0), (-1, 0), UNICODE_FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [pdf_light, colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.6, pdf_grid)
        ]))
        elements.append(session_table)

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"{t('pdf_sold_products')}:", heading2_style))
    elements.append(Spacer(1, 12))

    cart_items = CartItem.query.join(Session).filter(
        Session.room_id.in_(user_room_ids),
        Session.created_at >= range_start_utc,
        Session.created_at < range_end_utc,
        Session.is_active == False
    ).all()

    unknown_product = t('pdf_no_data')
    if cart_items:
        product_sales = {}
        for item in cart_items:
            product_name = item.product.name if item.product else unknown_product
            if product_name in product_sales:
                product_sales[product_name]['quantity'] += item.quantity
                product_sales[product_name]['total'] += item.total_price
            else:
                product_sales[product_name] = {
                    'quantity': item.quantity,
                    'unit_price': item.price_at_time,
                    'total': item.total_price
                }

        product_data = [[t('pdf_product'), t('pdf_quantity'), f"{t('pdf_price')} ({currency})", f"{t('pdf_total')} ({currency})"]]
        total_product_revenue = 0
        for product_name, data in product_sales.items():
            product_data.append([
                product_name,
                f"{data['quantity']} {t('pdf_pcs')}",
                f"{data['unit_price']:,.0f}",
                f"{data['total']:,.0f}"
            ])
            total_product_revenue += data['total']

        product_data.append([t('pdf_total').upper(), '', '', f"{total_product_revenue:,.0f}"])
        product_table = Table(product_data, colWidths=[2.4 * inch, 1 * inch, 1.2 * inch, 1.2 * inch])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), pdf_primary),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -2), 'LEFT'),
            ('ALIGN', (1, 1), (3, -2), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), UNICODE_FONT),
            ('FONTNAME', (0, 0), (-1, 0), UNICODE_FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [pdf_light, colors.white]),
            ('BACKGROUND', (0, -1), (-1, -1), pdf_lighter),
            ('FONTNAME', (0, -1), (-1, -1), UNICODE_FONT_BOLD),
            ('GRID', (0, 0), (-1, -1), 0.6, pdf_grid)
        ]))
        elements.append(product_table)
    else:
        elements.append(Paragraph(t('pdf_no_products_sold'), normal_style))

    def draw_header_footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont(UNICODE_FONT, 9)
        canvas.setFillColor(pdf_text)
        header_text = f"{current_user.gaming_center_name} • {report_titles.get(report_type, t('pdf_report_title'))}"
        canvas.drawString(doc.leftMargin, A4[1] - 24, header_text)
        canvas.setStrokeColor(pdf_grid)
        canvas.line(doc.leftMargin, A4[1] - 28, A4[0] - doc.rightMargin, A4[1] - 28)
        footer_text = f"{t('pdf_date_range')}: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        canvas.drawString(doc.leftMargin, 18, footer_text)
        canvas.drawRightString(A4[0] - doc.rightMargin, 18, f"{t('pdf_page')} {doc_obj.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)

    report_filenames = {
        'daily': t('pdf_daily_report'),
        'weekly': t('pdf_weekly_report'),
        'monthly': t('pdf_monthly_report')
    }
    filename = f"{report_filenames.get(report_type, 'report')}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"

    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@app.route('/inventory-stats')
@login_required
def inventory_stats_api():
    products = Product.query.filter_by(admin_user_id=current_user.id, is_active=True).all()
    total_products = len(products)
    available_products = 0
    low_stock_products = 0
    out_of_stock_products = 0

    for product in products:
        if product.stock_quantity is None or product.stock_quantity <= 0:
            out_of_stock_products += 1
        elif product.min_stock_alert and product.stock_quantity <= product.min_stock_alert:
            low_stock_products += 1
        else:
            available_products += 1

    return jsonify({
        'total': total_products,
        'available': available_products,
        'low_stock': low_stock_products,
        'out_of_stock': out_of_stock_products
    })

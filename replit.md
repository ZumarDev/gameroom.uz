# Gaming Center Management System

## Overview

A Flask-based web application for managing a gaming center with room-based gaming sessions, product sales, and revenue analytics. The system supports two types of gaming sessions (fixed-time and VIP) with real-time timer functionality and comprehensive admin management features.

## User Preferences

Preferred communication style: Simple, everyday language.
Interface preferences: Uzbek language throughout, centered section headers, enhanced filtering and search capabilities.

## System Architecture

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM
- **Database**: SQLite (configured via environment variable, defaults to local file)
- **Authentication**: Flask-Login for admin session management
- **Forms**: WTForms for form validation and rendering
- **Password Security**: Werkzeug for password hashing

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme
- **CSS Framework**: Bootstrap 5 with enhanced custom styling (custom.css + enhanced.css)
- **JavaScript**: Vanilla JS for real-time timers, dashboard functionality, and filtering/search
- **Icons**: Bootstrap Icons for consistent UI elements
- **Enhanced Features**: Search and filter functionality, centered page headers, date selection for reports

### Authentication System
- Single admin user authentication using Flask-Login
- Password hashing with Werkzeug security utilities
- Session-based authentication with protected routes
- Admin user creation script for initial setup

## Key Components

### Models (SQLAlchemy)
1. **AdminUser**: Single admin account with login credentials
2. **Room**: Gaming rooms that can host sessions
3. **Product**: Sellable items (drinks, snacks, food) with categories and pricing
4. **Session**: Gaming sessions with timer functionality and pricing
5. **CartItem**: Products purchased during sessions (referenced but not fully implemented)

### Forms (WTForms)
- LoginForm: Admin authentication
- RoomForm: Room creation and management  
- ProductForm: Product management with categories
- SessionForm: Session creation with room and type selection
- AddProductToSessionForm: Adding products to active sessions

### Views (Flask Routes)
- Authentication routes (login/logout)
- Dashboard with statistics and active session overview
- Room management (CRUD operations) with category filtering
- Product management (CRUD operations) with category filtering and search
- Session management (start/stop/monitor) with accurate duration tracking
- Analytics and revenue reporting with daily/monthly date selection

## Data Flow

### Session Management Flow
1. Admin selects room and session type (fixed or VIP)
2. For fixed sessions: predefined duration and pricing (30min=15k, 60min=25k, etc.)
3. For VIP sessions: open-ended timing with manual stop
4. Real-time JavaScript timers track session duration
5. Products can be added during active sessions
6. Session completion calculates total cost (session + products)

### Revenue Tracking
- Daily, weekly, and monthly revenue aggregation
- Session-based revenue (room usage fees)
- Product-based revenue (food/drinks sold)
- Combined analytics dashboard with statistics cards

### Real-time Features
- JavaScript-powered session timers that update every second
- AJAX endpoints for timer data (referenced in timer.js)
- Auto-refreshing dashboard every 30 seconds
- Visual indicators for session status (active/warning/completed)

## External Dependencies

### Python Packages
- Flask: Web framework
- Flask-SQLAlchemy: Database ORM
- Flask-Login: Authentication management
- Flask-WTF: Form handling and CSRF protection
- WTForms: Form validation
- Werkzeug: Password hashing and security utilities

### Frontend Libraries
- Bootstrap 5: UI framework with dark theme
- Bootstrap Icons: Icon library
- Custom CSS for gaming-specific styling
- Vanilla JavaScript for timer functionality

### Database
- PostgreSQL for production deployment on Replit
- Connection pooling and ping configuration for production readiness
- Environment variable DATABASE_URL configured automatically

## Deployment Strategy

### Development Setup
- Flask development server on port 5000
- Debug mode enabled for development
- SQLite database with automatic table creation
- Admin creation script for initial setup

### Production Considerations
- Environment-based configuration (DATABASE_URL, SESSION_SECRET)
- ProxyFix middleware for reverse proxy deployments
- Database connection pooling configured
- Logging system configured for debugging

### File Structure
- `app.py`: Main application factory and configuration
- `models.py`: Database models and relationships with duration calculation methods
- `views.py`: Route handlers and business logic with enhanced analytics
- `forms.py`: Form definitions and validation
- `templates/`: Jinja2 HTML templates with enhanced UI and centered headers
- `static/css/`: Custom styling (custom.css, enhanced.css)
- `static/js/`: JavaScript functionality (timer.js, dashboard.js, filters.js)
- `create_admin.py`: Initial admin user creation utility

## Recent Changes (January 2025)

### UI/UX Enhancements
- **Centered Page Headers**: All section headers now display centered with attractive icons and descriptions
- **Enhanced Styling**: Added enhanced.css with modern gradients, animations, and improved visual appeal
- **Responsive Design**: Better mobile-friendly layout and button sizing

### Filtering and Search Features
- **Product Search**: Real-time search by product name with category filtering (ichimliklar, gazaklar, ovqatlar, etc.)
- **Room Category Search**: Search room categories by name and description
- **Room Filtering**: Filter rooms by category and search by name/description
- **Enhanced JavaScript**: Added filters.js for all search and filtering functionality

### Analytics Improvements
- **Date Selection**: Daily and monthly report selection with specific date/month picking
- **Dynamic Reports**: Analytics page now supports query parameters for date filtering
- **Enhanced Display**: Improved analytics layout with main report card and comparison cards
- **Uzbek Localization**: Month names and interface elements properly localized

### Session Management Fixes
- **Accurate Duration**: Fixed session duration calculation to show actual time played, not planned time
- **Error Handling**: Improved null-checking for start_time fields
- **Real-time Pricing**: Both fixed and VIP sessions now use per-minute accurate pricing calculations

The application follows a traditional Flask MVC pattern with enhanced user experience, making it both maintainable and visually appealing for gaming center management.
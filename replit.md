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

## Recent Changes (July 2025)

### Inventory Management System Implementation (July 30, 2025)
- **Stock Management**: Added comprehensive inventory tracking to Product model
  - Added stock_quantity and min_stock_alert fields to products
  - Implemented stock status methods (in_stock, low_stock, out_of_stock)
  - Stock deduction when products are sold during sessions
- **Inventory Management Interface**: Created dedicated inventory management page
  - Stock overview cards showing total, available, low stock, and out of stock products
  - Inventory update form for adding/setting stock levels
  - Real-time stock status display with color-coded indicators
- **Session Product Management**: Enhanced product addition during sessions
  - Stock validation before adding products to sessions
  - Automatic stock deduction when products are sold
  - Stock alerts when inventory is low or depleted
- **Category System**: Simplified product categories for user creation
  - Removed predefined categories, allowing custom category creation
  - Category management through modal interface
  - Improved Uzbek language consistency in category display

## Recent Changes (July 2025)

### Migration and Multi-User System
- **Replit Migration**: Successfully migrated from Replit Agent to standard Replit environment
- **PostgreSQL Integration**: Configured PostgreSQL database for production deployment
- **Multi-User Support**: Added registration system for multiple gaming centers with unique admin accounts
- **Gaming Center Names**: Each admin can have their own gaming center name displayed in navbar
- **Database Updates**: Added gaming_center_name and is_admin_active fields to AdminUser model
- **Multi-Tenant Architecture**: Complete implementation with admin_user_id fields across all models
- **Registration Security**: Secret key protection for new admin account creation

### UI/UX Improvements and Interface Unification (July 29, 2025)
- **Centered Headers**: Dashboard, Sessions, and Products pages now have centered, styled headers with icons
- **Dark Theme Consistency**: Fixed white backgrounds in CSS to maintain dark gaming theme
- **Enhanced Styling**: Improved gradient colors and removed light theme elements
- **Unified Room Management**: Combined rooms and categories into single interface at /rooms-management
- **Navigation Simplification**: Replaced dropdown menu with single link for rooms and categories

### Filter System and Duration Display Fixes
- **Product Category Translation**: Fixed category display to show Uzbek translations (drinks->Ichimliklar)
- **Category Management**: Added ability to add new product categories through modal interface
- **JavaScript Filter Improvements**: Enhanced category matching with proper null checking and mapping
- **Duration Display**: Implemented precise duration display with seconds for completed sessions
- **Form Consistency**: Updated ProductForm to include desserts category and aligned with filter options

### Migration Completion and Multi-Tenant Architecture (July 29, 2025 - Evening)
- **Migration Completion**: Successfully migrated from Replit Agent to standard Replit environment
- **Database Migration**: PostgreSQL database fully configured and connected  
- **Complete Multi-Tenant Architecture**: Full gaming center separation implemented
  - Added admin_user_id to all models (Room, RoomCategory, Product)
  - Each gaming center operates completely independently with own data
  - Dashboard, products, rooms, sessions, and analytics filtered by current user
  - All CRUD operations (create, read, update, delete) properly secured per user
  - Session management, product sales, and reporting completely isolated per admin
- **Products Interface Enhancement**: Updated products page with improved design
  - Implemented tab-based interface matching rooms management layout
  - Simplified category system using Uzbek names only (removed English confusion)
  - Card-based layout with proper category display and product counts
  - Fixed category filtering system to use consistent Uzbek naming
- **Security Fixes**: Resolved all multi-tenant security issues
  - Fixed product deletion to check admin ownership
  - Secured all session operations to only user's rooms
  - Protected analytics to show only current user's data
  - Added validation to prevent cross-tenant data access

## Previous Changes (January 2025)

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
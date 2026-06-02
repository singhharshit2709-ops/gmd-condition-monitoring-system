1. Executive Summary
1.1 Purpose

The G Tank Electrical Condition Monitoring System is a web-based monitoring application developed to record, monitor, and analyze critical electrical equipment parameters across G Tank operations. The system enables maintenance personnel and engineers to monitor equipment current, temperature, and vibration values through a centralized dashboard, facilitating proactive maintenance planning and improved equipment reliability.

1.2 Key Benefits
Centralized monitoring of electrical equipment health
Digital recording and storage of condition monitoring data
Real-time visualization of equipment operating conditions
Automatic identification of abnormal operating parameters
Improved maintenance decision-making through data-driven insights
Cloud-based accessibility for engineering and maintenance teams
Historical data storage and retrieval through Google Sheets integration
Scalable architecture for future AI-based predictive maintenance features
1.3 Target Users
Maintenance Technicians
Electrical Engineers
Utility Engineers
Maintenance Supervisors
Plant Management Team
Reliability and Condition Monitoring Personnel
2. System Overview
2.1 Application Type

Web-Based Electrical Condition Monitoring Application

2.2 Access Methods
Desktop Browser Access
Mobile Browser Access
Tablet Support
Cloud-Based Remote Accessibility
2.3 Objective

The primary objective of the system is to digitize electrical condition monitoring activities within G Tank operations by providing a centralized platform for recording, analyzing, and visualizing equipment operating parameters.

2.4 Monitored Parameters

The system monitors:

Current (A)
Temperature (°C)
Vibration (mm/s)

These parameters are used to evaluate equipment health and identify abnormal operating conditions.

3. Features and Capabilities
3.1 Dashboard Monitoring

The dashboard provides a centralized overview of equipment operating conditions across all monitored areas. It displays equipment health status, recent readings, active alarms, and condition monitoring trends, enabling engineers to quickly identify equipment requiring attention.

3.2 Reading Entry System

Users can record equipment condition monitoring readings through a structured data entry interface. The system captures current, temperature, and vibration readings along with technician information and timestamps for future reference and analysis.

3.3 Data Visualization

Historical readings are presented through interactive dashboards and tables, allowing users to observe trends, compare operating conditions, and evaluate equipment performance over time.

3.4 Alarm and Threshold Monitoring

The system automatically evaluates entered readings against configured operating limits and categorizes equipment status as:

Normal
Warning
Alarm

This enables timely identification of abnormal equipment conditions.

3.5 AI Analysis Module

The application includes an AI-assisted analysis section designed to support future implementation of anomaly detection, predictive maintenance recommendations, and equipment health assessment capabilities.

3.6 Cloud-Based Data Storage

Monitoring data is stored and synchronized through Google Sheets integration, providing centralized access and long-term record retention.

4. Equipment Configuration
4.1 Monitored Areas

The Electrical Condition Monitoring System currently monitors the following G Tank equipment areas:

G1 Lehr
G2 Lehr
G3 Lehr
Furnace Cooling Blower
Mold Cooling Blower
Combustion Blower
Injector Blower
Electrode Cooling Blower
Electrode Water Pump
4.2 Monitored Equipment Parameters

Each equipment area includes multiple motors and electrical assets monitored using:

Current (A)
Temperature (°C)
Vibration (mm/s)
4.3 Threshold Configuration

The system evaluates equipment health using predefined operating limits:

Normal Range
Warning Range
Alarm Range

Whenever a parameter exceeds its configured threshold, the dashboard automatically updates equipment status and generates appropriate alerts.

5. User Guide
For Technicians

Technicians can enter condition monitoring readings through the Add Readings interface. The readings are automatically validated, stored, and displayed on the dashboard.

For Engineers

Engineers can access equipment health information, monitor historical trends, review alarms, and analyze equipment performance through dashboard visualizations.

For Supervisors and Management

Supervisors can monitor overall equipment condition, identify critical alarms, and review maintenance-related insights generated from the monitoring data.

6. Technical Architecture
6.1 Technology Stack
Frontend
React.js
JavaScript
HTML
CSS
Backend
FastAPI
Python
Data Management
Google Sheets Integration
REST APIs
Version Control
Git
GitHub
Deployment Platform
Render Cloud Platform
6.2 System Architecture
User Interface (React.js Dashboard)
                ↓
          REST APIs
                ↓
         FastAPI Backend
                ↓
      Google Sheets Storage
                ↓
 Condition Monitoring Analytics
6.3 Data Flow

The monitoring workflow follows the sequence below:

Technician enters equipment readings.
Frontend validates user input.
Data is transferred through FastAPI APIs.
Backend processes monitoring records.
Records are stored in Google Sheets.
Dashboard retrieves and visualizes the latest information.
Equipment status is evaluated against configured limits.
Alarms and notifications are generated where necessary.
6.4 API Configuration and Backend Validation

FastAPI Swagger documentation was utilized for backend validation and endpoint testing throughout the project. API responses, request structures, equipment configurations, and monitoring records were verified using Swagger interfaces before deployment.

The validation process ensured reliable communication between frontend services, backend processing modules, and the Google Sheets data repository.

7. Data Management
7.1 Data Storage

Google Sheets serves as the centralized storage platform for all condition monitoring records.

Stored information includes:

Equipment Area
Motor Name
Current Reading
Temperature Reading
Vibration Reading
Threshold Values
Equipment Status
Timestamp
Technician Information
7.2 Data Accessibility

Monitoring records can be accessed through:

Dashboard Interface
Google Sheets Repository
API Services
7.3 Historical Data Analysis

The system supports retrieval and visualization of historical monitoring records for trend analysis and maintenance planning purposes.

8. Deployment Information

The application was deployed using Render cloud services and managed through GitHub version control.

Deployment activities included:

Repository Management
Build Configuration
Application Deployment
Functional Testing
Production Validation
Performance Verification

Following deployment, end-to-end validation was performed to verify dashboard functionality, API connectivity, data synchronization, and system reliability.

9. Results and Achievements

The project successfully achieved the following outcomes:

Transformation of an existing monitoring architecture into an Electrical Condition Monitoring Dashboard.
Successful integration of React.js frontend and FastAPI backend services.
Configuration and validation of Google Sheets-based data management.
Deployment of the monitoring dashboard in a production environment.
Standardization of G1 Lehr, G2 Lehr, and G3 Lehr monitoring areas.
Validation of dashboard functionality, API responses, and data synchronization workflows.
Enhancement of backend persistence mechanisms to improve dashboard reliability after application restarts.
Successful implementation of electrical condition monitoring functionality for G Tank operations.
10. Future Scope

Future enhancements can further improve system capabilities through:

AI-Based Condition Monitoring
Equipment Health Scoring
Predictive Maintenance Analytics
Remaining Useful Life Estimation
Failure Prediction Models
Intelligent Maintenance Recommendations
Industry 4.0 Integration
Real-Time Sensor Connectivity
IoT Device Integration
Automated Data Acquisition
Mobile Monitoring Applications
Automated Notifications and Alerts
Advanced Reporting
Automated Daily Reports
Weekly Maintenance Reports
Equipment Performance Dashboards
Reliability Analytics
Energy Monitoring and Analysis
11. Conclusion

The G Tank Electrical Condition Monitoring System successfully demonstrated the application of digital technologies in industrial maintenance and equipment monitoring. The project involved studying existing software architecture, understanding condition monitoring principles, customizing a React.js and FastAPI-based application, integrating Google Sheets for centralized data storage, and supporting deployment and validation activities. The implementation enhanced monitoring efficiency, improved accessibility of maintenance data, and established a scalable foundation for future predictive maintenance and AI-assisted analytics initiatives within Gerresheimer's G Tank operations.

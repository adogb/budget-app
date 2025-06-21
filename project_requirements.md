# 📝 Product Requirements Document

## Project Title

**Personal Budget Web App** (Working Title)

---

## 1. Purpose

Develop a web application for personal finance management. The app will securely sync with bank accounts via Nordigen, automatically categorize transactions, track budgets and spending, and provide actionable summaries or export features. The goal is to enable easy, private budget tracking, while serving as a platform for learning, automation, and possible future monetization.

---

## 2. Target Users

- **Primary:**  
  - The developer (you), looking to create tool tailored to personal budgeting needs, with a focus on learning app development and automation.

- **Secondary:**  
  - Anyone interested in a lightweight, privacy-respecting budgeting tool with features they cannot find in existing solutions.

---

## 3. Core Features (MVP)

The MVP will focus on just one user (the developer) and will include the following core features:

### 🔗 Bank Data Integration

- Securely connect to banks via Nordigen API and select accounts.
- **Multi-Account Support**: Connect and manage multiple accounts including joint accounts.
- Fetch, update, and store transactions in a secure backend.
- **Real-time Balance Tracking**: Display current account balances with refresh capability.
- Handle authentication, token refresh, and error states gracefully.

### 🗂 Transaction Management & Basic Categorization

- **Custom Categories**: Create, edit, and manage personalized spending categories that match your lifestyle.
- **Bulk Categorization**: Perform bulk categorization actions on multiple transactions.
- **Transaction Search**: Search and filter transactions based on partial search of transaction "name".
- **Transaction Views**: List transactions with basic filtering and sorting capabilities.

### 💻 Visual Analytics & User Experience

- **Visual Analytics**: View spending breakdowns through:
  - Interactive charts (pie charts, bar graphs, trend analysis)
  - Detailed tables with sorting and filtering capabilities
  - Customizable time period views (daily, weekly, monthly, quarterly, yearly)
- Minimalist, intuitive web UI featuring:
    - **Dashboard Overview**: Visual spending summary with charts and key metrics across customizable time periods
    - **Category Management**: Easy creation and editing of spending categories
    - **Transaction Views**: List, filter, and categorize transactions with bulk actions
    - **Analytics Pages**: Interactive graphs and detailed tables showing spending patterns with period customization
    - **Account Management**: Multi-account dashboard
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- No user registration (for MVP); access is controlled by you.

---

## 4. Nice-to-Haves (Post-MVP / Stretch Goals)

### 🗂 Advanced Transaction & Budgeting Features
- **Smart Categorization**: Automatic assignment of transactions to user-defined spending categories with manual override capability.
- **Flexible Budget Periods**: Set spending limits for customizable time periods (weekly, monthly, quarterly, yearly).
- **Envelope Budgeting**: Only budget with money you actually have, not future expected income.
- **Budget Monitoring**: Clear indicators showing whether you're under, at, or over your spending limits for each category.
- **Multi-Country Banking**: Connect and manage accounts from various countries through Nordigen.
- **Transaction Filtering**: Exclude internal transfers and specific transaction types from tracking.
- **Transaction Splits**: Split single transactions across multiple categories.
- **Reconciliation**: Mark transactions as cleared/reconciled to match bank statements.
- **Transaction Management**: Re-label transactions while preserving original transaction details.
- **Smart Rules Engine**: Interface for setting up automatic categorization rules.
- **Scheduled Transactions**: Create and manage recurring transactions (salary, bills, subscriptions).
- **Advanced Search & Filtering**: Advanced search across all transactions with multiple filter criteria.
- **Data Import/Export**: Import from CSV/OFX files and export reports (CSV, PDF).
- **Reconciliation Tools**: Mark transactions as cleared and reconcile against bank statements.
- **Keyboard Shortcuts**: Quick navigation and actions for power users.

### 🚀 Advanced Features
- **Investment Tracking**: Portfolio monitoring, asset allocation, and investment performance analysis.
- **Piggy Banks**: Save towards specific goals with visual progress tracking.
- **Bill Management**: Track due dates, payment history, and automate bill payments.
- **Credit Card Features**: Detailed credit card management, payment tracking, and interest calculations.
- **Currency Support**: Multi-currency accounts with automatic conversion rates.
- **Advanced Categorization Rules**: Machine learning-based transaction categorization that improves over time.
- **Smart Insights**: Predictive analytics for spending patterns and budget recommendations.
- **Goal Setting**: Savings goals and financial milestone tracking.
- **Smart Recurring Detection**: Automatic identification of subscriptions, bills, and recurring transactions.
- **Custom Rules Engine**: Advanced rule-based categorization with complex conditional logic.
- **Notifications**: Daily/weekly digest emails of spending and budget alerts.
- **Mobile App**: Native mobile application for on-the-go expense tracking.
- **Multi-User Support**: Simple authentication and shared account management.
- **Two-Factor Authentication**: Enhanced security for account access.
- **REST API**: Full API access for third-party integrations and mobile apps.
- **Webhook Support**: Real-time notifications for external systems.
- **Blog Integration**: Embed dashboard or publish spending summaries.
- **Monetization Features**: Paid plan, donations, premium downloadable reports.
- **Advanced Analytics**: AI-powered insights, spending predictions, and financial health scores.
- **Tax Integration**: Basic tax categorization and reporting features.
- **Debt Tracking**: Loan management, payment schedules, and payoff projections.
- **Net Worth Tracking**: Complete financial picture including assets and liabilities.

---

## 5. Architecture

- **Backend:** FastAPI (Python) with data visualization endpoints
- **Frontend:** Modern web UI with interactive charts (Chart.js, D3.js, or similar)
- **Database:** SQLite for local/dev, Postgres for production (TBD)
- **External Services:** Nordigen for open banking data
- **Visualization:** Client-side charting libraries for responsive graphs and analytics
- **Config:** Environment variables via `.env` files, loaded per environment
- **Deployment:** Local first, with easy cloud deployment (e.g., Fly.io, Render, Railway)
- **Security:** All sensitive data stored locally or in secure, user-controlled cloud environments.

---

## 6. Success Criteria & Creator Goals

- Rapid development with familiar stack.
- Focused learning on:
    - Financial data automation
    - Simple, repeatable deployments
    - Exploring monetization and integrations
- Minimal time spent on UI/boilerplate; prioritize backend and automation.

---

## 7. User Stories / Functional Requirements

### 🧾 Transaction & Bank Integration

- As a user, I can securely link my banks accounts and sync transactions automatically.
- As a user, I can refresh my bank connection to ensure up-to-date data.
- As a user, I can see real-time account balances.
- As a user, I can view and search transactions based on partial search of transaction label or amount.

### 💰 Basic Categorization & Insights

- As a user, I can create and customize spending categories that match my lifestyle.
- As a user, I can perform bulk categorization actions on multiple transactions.
- As a user, I can view my spending in multiple formats:
  - Interactive charts (pie charts, bar graphs, trend analysis)
  - Detailed tables with sorting and filtering capabilities
  - Customizable time period views (daily, weekly, monthly, quarterly, yearly)
  - Category breakdowns with period customization
  - Spending trends across different time periods

### 🔒 Privacy & Data Control

- As a user, my financial data is private, stored locally or in user-controlled cloud storage.
- As a user, I can permanently delete all my data at any time.

### 🛠 Admin & Developer Experience

- As the creator, I can connect to Nordigen once and reuse the access token.
- As the creator, I can test with mock data in a development environment.
- As the creator, I can deploy the app to production with minimal setup.

---

## 8. Non-Functional Requirements

- Privacy-first: No sharing or selling of user data.
- Security: All sensitive credentials and financial data are encrypted at rest.
- Performance: App should load transaction lists and summaries within 2 seconds.
- Maintainability: Codebase is simple, well-documented, and easy to extend.
- Portability: Easy to run locally or deploy to popular cloud providers.

---

## 9. Out of Scope (for MVP)

- Budgeting and spending limits (moved to Post-MVP)
- Envelope budgeting methodology (moved to Post-MVP)
- Smart/automatic transaction categorization (moved to Post-MVP)
- Transaction splits across multiple categories (moved to Post-MVP)
- Bank statement reconciliation (moved to Post-MVP)
- Scheduled/recurring transaction management (moved to Post-MVP)
- Advanced search with multiple filter criteria (moved to Post-MVP)
- Data import/export functionality (moved to Post-MVP)
- Transaction re-labeling while preserving originals (moved to Post-MVP)
- Multi-country banking support (moved to Post-MVP)
- Internal transfer filtering (moved to Post-MVP)
- Investment and asset tracking
- Tax calculation or comprehensive reporting
- In-app payment features
- Rich mobile support (beyond responsive web UI)
- Advanced machine learning categorization
- Cryptocurrency tracking
- Loan and debt management features
- Multi-currency support with automatic conversion
- Two-factor authentication
- Bill payment automation
- Credit card interest calculations
- Advanced double-entry bookkeeping features

---
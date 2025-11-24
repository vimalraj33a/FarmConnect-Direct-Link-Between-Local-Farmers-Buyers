# FarmConnect-Direct-Link-Between-Local-Farmers-Buyers
FarmConnect is a modern, full-stack web application built using Streamlit. It creates a direct connection between local farmers and buyers, removing middlemen and ensuring fair pricing.
The platform allows:

 Farmers – to upload products, manage stock, and sell directly
 Buyers – to browse items, filter by price, search, and place orders
 Admin/Export – export product data to CSV

The app uses:

  SQLite database (local storage)

  Secure password hashing (bcrypt)

| Layer          | Technology                     |
| -------------- | ------------------------------ |
| Frontend       | Streamlit + Custom CSS         |
| Backend        | Python                         |
| Database       | SQLite                         |
| Authentication | bcrypt password hashing        |
| File Storage   | Local uploads folder           |
| Editor         | VS Code                        |
| Hosting        | Streamlit Cloud / Local server |

Project Structure

    farmconnect/
    │── app.py
    │── requirements.txt
    │── farmconnect.db
    │── uploads/
    │── .streamlit/
    │     └── config.toml
    │── assets/
    │     └── (screenshots)
    └── README.md

